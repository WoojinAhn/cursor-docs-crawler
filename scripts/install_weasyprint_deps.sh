#!/usr/bin/env bash
# Install the native libraries WeasyPrint needs.
#
# Ubuntu 26.04 dropped the transitional package libgdk-pixbuf2.0-0.
# The library itself is libgdk-pixbuf-2.0-0. Older images only publish
# the transitional name, so pick whichever apt can actually install.
set -euo pipefail

select_gdk_pixbuf() {
  if apt-cache show libgdk-pixbuf-2.0-0 >/dev/null 2>&1; then
    echo libgdk-pixbuf-2.0-0
  else
    echo libgdk-pixbuf2.0-0
  fi
}

if [ "${1:-}" = "--print-gdk" ]; then
  select_gdk_pixbuf
  exit 0
fi

sudo apt-get update
GDK_PIXBUF="$(select_gdk_pixbuf)"
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 "$GDK_PIXBUF" "$@"
