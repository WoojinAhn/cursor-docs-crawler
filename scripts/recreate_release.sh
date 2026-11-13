#!/usr/bin/env bash
# Publish TAG, replacing a release created earlier the same day.
#
# The changelog step fetches the previous release tag. On a same-day rerun
# that tag is TAG, so it exists in the local clone. The workflow then deletes
# the remote tag, and `gh release create` aborts with:
#   tag <name> exists locally but has not been pushed ... specify `--target`
# Remove the local tag and pin --target to the commit this run checked out.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: recreate_release.sh TAG TITLE NOTES_FILE [assets...]" >&2
  exit 2
fi

TAG="$1"
TITLE="$2"
NOTES_FILE="$3"
shift 3

if [ -z "${GITHUB_SHA:-}" ]; then
  echo "GITHUB_SHA is required" >&2
  exit 2
fi

gh release delete "$TAG" --yes --cleanup-tag 2>/dev/null || true
GIT_TERMINAL_PROMPT=0 git push --delete origin "$TAG" 2>/dev/null || true
git tag -d "$TAG" 2>/dev/null || true

gh release create "$TAG" \
  --target "$GITHUB_SHA" \
  --title "$TITLE" \
  --notes-file "$NOTES_FILE" \
  "$@"
