#!/bin/bash 

set -e

function usage() {
    echo "Usage: $0 <GITHUB_REPOSITORY> <GITHUB_REF> <GITHUB_SHA>"
    echo "  GITHUB_REPOSITORY: The repository name (e.g., owner/repo)"
    echo "  GITHUB_REF: The reference of the commit (e.g., refs/heads/main)"
    echo "  GITHUB_SHA: The SHA of the build for which we want to keep the commit (optional)"
}

if [[ $# -lt 2 ]]; then
    usage
    exit 1
fi

GITHUB_REPOSITORY=$1
GITHUB_REF=$2
GITHUB_SHA=$3

if [[ -z "${GITHUB_SHA}"  ]]; then
    # This query finds all the artifacts named "documentation" that are associated with the given branch
    QUERY='.artifacts[] | select(.name == "documentation") | select(.workflow_run.head_branch == "'${GITHUB_REF}'") | .id'
else
    # This query finds all the artifacts named "documentation" that are associated with the given branch and filters out the ones that are associated with the current commit SHA
    QUERY='.artifacts[] | select(.name == "documentation") | select(.workflow_run.head_branch == "'${GITHUB_REF}'") | select(.workflow_run.head_sha != "'${GITHUB_SHA}'") | .id'
fi

echo "Look for existing artifacts for ${GITHUB_REPOSITORY} on branch ${GITHUB_REF}..."

ARTIFACTS=$(gh api -X GET /repos/${GITHUB_REPOSITORY}/actions/artifacts --paginate | jq -r "${QUERY}")

for ARTIFACT in ${ARTIFACTS}
do
    echo "Deleting artifact ${ARTIFACT}..."
    gh api -X DELETE /repos/${GITHUB_REPOSITORY}/actions/artifacts/${ARTIFACT}
done

echo "Done deleting artifacts."