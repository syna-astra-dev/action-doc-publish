#!/bin/bash

if [[ $# -lt 2 ]] ; then
    echo "Usage: $0 <GITHUB_REPOSITORY> <OUT_DIR>"
    exit 1
fi

BASE_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))

IMAGE_NAME="ghcr.io/syna-astra-dev/action-doc-publish/create-site:latest"

OUT_DIR=$(readlink -f $2)

docker build -t ${IMAGE_NAME} ${BASE_DIR}/create-site

# create the output directory to ensure permissions are correct
mkdir -p ${OUT_DIR}

docker run -it --rm \
           -e "GITHUB_TOKEN=$(gh auth token)" \
           -e "GITHUB_REPOSITORY=$1" \
           -v ${OUT_DIR}:${OUT_DIR} -w ${OUT_DIR} \
           ${IMAGE_NAME}