#!/bin/bash

LATEST_BRANCH=${LATEST_BRANCH:="refs/heads/main"}

set -e

mkdir -p _build

echo Building sphinx...

sphinx-build . _build/html

if [[ "${GITHUB_REF}" == "${LATEST_BRANCH}" ]]; then
  /tools/create-site.py "$1" "$2" "$3"
else
  cp -r _build/html _build/site
fi

echo Updating permission of files...

chown -R $(stat -c '%u:%g' . ) _build

echo Done
