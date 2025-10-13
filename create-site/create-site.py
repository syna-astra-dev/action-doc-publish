#!/usr/bin/env python3

import os
import shutil
import zipfile
import requests
import re
import argparse
import pwd
import grp


BANNER_ANCHOR = '<div role="main" class="document" itemscope="itemscope" itemtype="http://schema.org/Article">'
VERSION_ANCHOR = '<script>'
CANONICAL_ANCHOR = '<title>'

DOWNLOAD_FOLDER = "v"
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snippets")

CACHE_DIR = os.path.join('_build', 'site', 'cache')
SITE_DIR = os.path.join('_build', 'site', 'html')
VERSIONS_DIR = os.path.join('_build', 'site', 'html', 'v')

# Function to inject content into an HTML file after matching a specific line
def inject_content_into_html(file_path, anchor, content_to_inject):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    new_lines = []
    injected = False

    # Process each line
    for line in lines:
        # If pattern is found, insert the content
        if anchor in line and not injected:
            new_lines.append(content_to_inject + '\n')
            injected = True

        new_lines.append(line)

    # Write the modified content back to the file
    with open(file_path, 'w') as file:
        file.writelines(new_lines)


def get_gh_headers(accept = 'application/vnd.github+json'):
    
    headers = {
        'Accept': accept,
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'synaptics-create-site',
        'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']
    }
    
    return headers


def download_file(asset_url, asset_path, media_type = 'application/octet-stream'):
    asset_headers = get_gh_headers(media_type)

    with requests.get(asset_url, headers=asset_headers, allow_redirects=True) as asset_response:

        if asset_response.status_code != 200:
            raise Exception(f"Failed to fetch asset: {asset_response.status_code}, {asset_response.reason}")

        with open(asset_path, 'wb') as out_file:
            out_file.write(asset_response.content)


def download_release(repo, release):
    
    version_name = str(release['tag_name']).replace('/', '_')

    release_dir = os.path.join(CACHE_DIR, version_name)
        
    if not release['assets']:
        print("No assets found, skipping.")
        return
    
    for asset in release['assets']:
        if asset['name'] == 'documentation.zip':
            break
    else:
        print("No documentation.zip found in assets, skipping.")
        return
    
    try:
        os.makedirs(release_dir)
    except FileExistsError:
        print("Release already downloaded, skipping.")
        return version_name
    
    try:

        asset_url = f"https://api.github.com/repos/{repo}/releases/assets/{asset['id']}"
        asset_path = os.path.join(release_dir, 'documentation.zip')

        print(f"Downloading: {asset_url}")
        download_file(asset_url, asset_path)

    except Exception as e:
        shutil.rmtree(release_dir)
        raise e
    
    return version_name


def download_workflow_artifact(repo, workflow_artifact):

    version_name = str(workflow_artifact['workflow_run']['head_branch']).replace('/', '_')

    branch_dir = os.path.join(CACHE_DIR, version_name)
    
    try:
        os.makedirs(branch_dir)
    except FileExistsError:
        print("Artifact for branch already downloaded, skipping.")
        return version_name
    
    try:

        asset_url = f"https://api.github.com/repos/{repo}/actions/artifacts/{workflow_artifact['id']}/zip"
        asset_path = os.path.join(branch_dir, 'documentation.zip')

        print(f"Downloading: {asset_url}")
        download_file(asset_url, asset_path, 'application/vnd.github+json')

    except Exception as e:
        shutil.rmtree(branch_dir)
        raise e
    
    return version_name


def get_sorted_versions():

    # find all non-wip versions we downloaded    
    versions = [x for x in os.listdir(CACHE_DIR) if not x.startswith('wip_')]

    def split_version(version_name):
        parts = re.split(r'(?<=\d)(?=[A-Za-z])|(?<=[A-Za-z])(?=\d)|[._-]', version_name)
        return [(int(part), "") if part.isnumeric() else (float('inf'), part) for part in parts]

    return sorted(versions, key=split_version)


def fetch_paginate(url):
    headers = get_gh_headers()

    results = []

    full_url = f'https://api.github.com{url}'

    while True:
        response = requests.get(full_url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch page: {response.status_code}, {response.reason}")
        
        if isinstance(response.json(), dict):
            results.append(response.json())
        else:
            results += response.json()

        if 'Link' not in response.headers:
            break

        links = response.headers['Link'].split(',')

        for link in links:
            if 'rel="next"' in link:
                full_url = link.split(';')[0].strip()[1:-1]
                break
        else:
            break

    return results


def get_releases(repo):    
    return fetch_paginate(f'/repos/{repo}/releases')


def get_workflow_artifacts(repo):
    pages = fetch_paginate(f'/repos/{repo}/actions/artifacts')
    for page in pages:
        for workflow_artifact in page['artifacts']:            
            if workflow_artifact['expired']:
                continue
            if workflow_artifact['name'] == 'documentation':
                yield workflow_artifact


def reset_permissions(uid_path, target_path):

    if not os.path.exists(target_path):
        return

    def chown_recursive(path, uid, gid):
        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                os.chown(os.path.join(root, dir_name), uid, gid)
            for file_name in files:
                os.chown(os.path.join(root, file_name), uid, gid)
        os.chown(path, uid, gid)

    # Get the UID and GID of the current directory
    stat_info = os.stat(uid_path)
    uid = stat_info.st_uid
    gid = stat_info.st_gid

    # Apply ownership recursively to the _build directory
    chown_recursive(target_path, uid, gid)


def get_one_artifact_per_branch(workflow_artifacts):
    branches_artifacts = {}

    for workflow_artifact in workflow_artifacts:
        branch_name = workflow_artifact['workflow_run']['head_branch']

        if branch_name not in branches_artifacts:
            branches_artifacts[branch_name] = workflow_artifact

    return branches_artifacts.values()


def get_website_address(repo):

    websites = fetch_paginate(f'/repos/{repo}/pages')    

    if len(websites) == 0:
        print(f"No GitHub pages websites configured in {repo}")
        exit(1)

    return websites[0]['html_url']


def find_title(version_name):
    with open(os.path.join(VERSIONS_DIR, version_name, 'index.html'), 'r') as fp:
        data = fp.read()

    title = data.split('<title>')[1].split('</title>')[0]
    return title.split('&mdash;')[0]


def prepare_version(version_name, latest_version, is_dev, website_address):
    version_dir = os.path.join(VERSIONS_DIR, version_name)

    with zipfile.ZipFile(os.path.join(CACHE_DIR, version_name, 'documentation.zip'), 'r') as zip_ref:
        zip_ref.extractall(version_dir)

    # check if the zip contains a directory, in that case move out all the contents and remove the directory
    files_list = os.listdir(version_dir)
    if len(files_list) == 1 and os.path.isdir(os.path.join(version_dir, files_list[0])):

        inner_dir = os.path.join(version_dir, files_list[0])
        for item in os.listdir(inner_dir):
            shutil.move(os.path.join(inner_dir, item), version_dir)
        os.rmdir(inner_dir)

    title = find_title(version_name)

    version_bar = get_version_bar(version_name, latest_version, title, website_address)
        
    if latest_version == version_name:
        banner = None
    elif is_dev:
        banner = load_template("dev-header.html")        
    else:
        banner = load_template("old-release-header.html")

    canonical_header = load_template("canonical.html", website_address=website_address)
    
    # update all the files with the required version bar
    for root, dirs, files in os.walk(version_dir, topdown=True, followlinks=False):

        for file_name in files:

            if not file_name.endswith('.html'):
                continue

            file_path = os.path.join(root, file_name)

            if banner is not None:                
                inject_content_into_html(file_path, BANNER_ANCHOR, banner)

            # inject the version bar in the doc we downloaded from the release
            inject_content_into_html(file_path, VERSION_ANCHOR, version_bar)

            # inject the canonical header
            path_parts = os.path.relpath(file_path, VERSIONS_DIR).split('/')

            if path_parts[-1] == 'index.html':
                canonical_path = "/".join(path_parts[1:-1]) + ('/' if len(path_parts) > 2 else '')
            else:
                canonical_path = "/".join(path_parts[1:])            

            page_canonical_header = canonical_header.replace('%PAGE_PATH%', canonical_path)
            inject_content_into_html(file_path, CANONICAL_ANCHOR, page_canonical_header)


def find_latest_release(repo):

    try:
        latest_release = fetch_paginate(f'/repos/{repo}/releases/latest')

        return latest_release[0].get('tag_name')

    except Exception as e:
        print(f"Cannot find latest release")
        return None


def create_site():
    
    try:
        repository = os.environ['GITHUB_REPOSITORY']

    except KeyError:
        print("GITHUB_REPOSITORY environment variable not set")
        exit(1)

    versions = []

    print("Downloading documentation for releases...")
    releases = get_releases(repository)
    latest_version = find_latest_release(repository)

    for release in releases:
        print("Release: ", release['tag_name'])
        version_name = download_release(repository, release)

        if version_name is not None:
            versions.append([version_name, False])

    print("Downloading documentation for branches...")
    workflow_artifacts = get_workflow_artifacts(repository)
    workflow_artifacts = get_one_artifact_per_branch(workflow_artifacts)
    for workflow_artifact in workflow_artifacts:
        print("Branch: ", workflow_artifact['workflow_run']['head_branch'])                
        version_name = download_workflow_artifact(repository, workflow_artifact)

        if version_name is not None:
            versions.append([version_name, True])

    if os.path.exists(SITE_DIR):
        shutil.rmtree(SITE_DIR)

    os.makedirs(SITE_DIR)

    if len(versions) == 0:
        print("No versions found, exiting.")
        return

    # there are no releases, we take one of the branches as the latest version
    if latest_version is None:
        
        if 'main' in os.listdir(CACHE_DIR):
            latest_version = 'main'
        else:
            latest_version = versions[0][0]
    
    print("Latest version: ", latest_version)

    website_address = get_website_address(repository)
    print("Target website address: ", website_address)

    print("Creating main index.html file...")
    with open(os.path.join(SITE_DIR, 'index.html'), 'w') as fp:
        fp.write(load_template('index.html', website_address=website_address))

    print("Preparing versions of the documentation...")
    for version in versions:
        print("Version: ", version[0])
        prepare_version(version[0], latest_version, version[1], website_address)

    # setup a link to the latest released version
    os.symlink(latest_version, os.path.join(VERSIONS_DIR, 'latest'))


def load_template(template_name, **kwargs):
    with open(os.path.join(TEMPLATE_DIR, template_name), 'r') as fp:
        data = fp.read()

    for key, value in kwargs.items():
        data = data.replace(f'%%{key.upper()}%%', value)

    return data


def get_version_bar(current_version_name, latest_version, title, website_address):
    versions = []    

    for version_name in get_sorted_versions():

        version_label = version_name        

        if version_name == latest_version:
            version_label += " (latest)"

        versions.append(f'<dd><a href="{website_address}/v/{version_name}">{ version_label }</a>')

    current_version_label = current_version_name

    if current_version_name == latest_version:
        current_version_label += ' (latest)'

    return load_template('versions.html', versions="\n".join(versions), title=title, current_version=current_version_label)


if __name__ == "__main__":
    try:
        create_site()
    finally:
        reset_permissions('.', '_build')
