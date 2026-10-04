#!/usr/bin/env bash
# The heavyweight consumer is deliberately installed only on a disposable CI VM.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_OS:-}" == Linux ]] || {
  echo 'Refusing local OBS installation. Use GitHub Actions ubuntu-24.04.' >&2; exit 2;
}
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo 'Ubuntu 24.04 required' >&2; exit 2; }
VERSION=32.2.2
ASSET="OBS-Studio-${VERSION}-Ubuntu-24.04-x86_64.deb"
SHA256=b6557ca2059287210332accc94c267094050489cffffc5c832e746e3a418dab0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl --fail --location --retry 3 "https://github.com/obsproject/obs-studio/releases/download/${VERSION}/${ASSET}" -o "$TMP/$ASSET"
echo "$SHA256  $TMP/$ASSET" | sha256sum --check --strict
sudo apt-get update
sudo apt-get install --no-install-recommends -y "$TMP/$ASSET" xvfb xauth openbox dbus-x11 xdotool imagemagick tesseract-ocr python3-websocket fonts-dejavu-core
printf 'Installed official OBS %s asset; verified SHA256 %s\n' "$VERSION" "$SHA256"
