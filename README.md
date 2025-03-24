# Synaptics Documentation GitHub Actions

This repository contains GitHub Actions and reusable workflows that allow to create a documentation website.

The workflow performs the following tasks:

- Build the documentation for any branch and save it as an workflow run artifact. Previous artifacts
  for the same branch are automatically deleted. The documentation includes links "Edit on GitHub" to
  help authoring.

- Attach a build of the documentation each time a new release is published.

- Each time a branch modified or a release is published the GitHub pages site of the repository is updated
  with all the versions of the documentation:

    - A version navigation toolbar is injected in each page.

    - A canonical URL header is injected in all pages to point to the latest release to help search 
      engines to direct the users to the latest version.

    - Banners are added to pages to indicate where to find the latest, non-develpment version of the
      documentation.

## How to use

To use these actions in a repository:

1. Ensure the repository is buildable with the [Synaptics Sphinx Theme](https://github.com/syna-astra-dev/synaptics-sphinx-theme).

2. Copy the workflow from this repository `template.yml` to `.github/workflows/build.yml` in the target repository

3. Ensure the following setting for the target repository:

     - Settings -> Pages -> Build and Deployment -> Source = GitHub Actions

     - Settings -> Environment -> github-pages -> Deployment branches and tags = No branch

