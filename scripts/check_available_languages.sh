#!/usr/bin/env bash
# Compare the "Available languages" line in two llms.txt files.
#
# Stdout is either:
#   unchanged
# or:
#   changed
#   old=<line, or empty when the line is missing>
#   new=<line, or empty when the line is missing>
#
# A missing file is treated as "no line", so the first snapshot is not a
# locale change by itself. Callers decide whether to open an issue.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: check_available_languages.sh OLD_FILE NEW_FILE" >&2
  exit 2
fi

language_line() {
  local file="$1"
  if [ ! -f "$file" ]; then
    printf ''
    return 0
  fi
  # `|| true` covers both "no match" (grep exits 1) and SIGPIPE from `head`.
  grep -E '^Available languages:' "$file" | head -n 1 || true
}

old="$(language_line "$1")"
new="$(language_line "$2")"

if [ "$old" = "$new" ]; then
  printf 'unchanged\n'
  exit 0
fi

printf 'changed\n'
printf 'old=%s\n' "$old"
printf 'new=%s\n' "$new"
