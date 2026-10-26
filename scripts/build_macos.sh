#!/bin/sh
# Install packaging tools first: python3 -m pip install '.[build]'
set -eu
cd -- "$(dirname -- "$0")/.."
if [ "$(uname -s)" != Darwin ]; then
  echo 'Build the macOS application on macOS.' >&2
  exit 1
fi
python3 -m PyInstaller \
  --noconfirm --windowed --onedir \
  --name 'MCS51 Studio' \
  --osx-bundle-identifier org.mcs51studio.desktop \
  --paths src \
  --add-data 'src/mcs51_studio/data:mcs51_studio/data' \
  --specpath build \
  launch.py
