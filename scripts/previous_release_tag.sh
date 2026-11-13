#!/usr/bin/env bash
# Print the newest published release tag other than today's.
#
# `gh release list` is newest-first. On a same-day rerun the newest tag is
# the release this job is about to delete. Diffing that tag against the
# current snapshot compares the release with itself and replaces the
# morning's notes with "no structural change".
set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  echo "usage: previous_release_tag.sh TODAY_TAG" >&2
  exit 2
fi

TODAY_TAG="$1"
# `|| true` covers both "no matching tag" (grep exits 1) and SIGPIPE from
# `head` under `pipefail`.
gh release list --exclude-drafts --limit 10 --json tagName --jq '.[].tagName' \
  | grep -vx "$TODAY_TAG" \
  | head -n 1 \
  || true
