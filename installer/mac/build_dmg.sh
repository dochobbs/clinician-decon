#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="Clinician Decon"
VERSION="0.1.0"
# The staging output is Clinician Decon.app inside the final DMG.
BUILD_DIR="$ROOT_DIR/build/mac"
DIST_DIR="$ROOT_DIR/dist/mac"
APP_DIR="$BUILD_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
STAGE_DIR="$BUILD_DIR/dmg-root"
DMG_PATH="$DIST_DIR/Clinician-Decon-$VERSION.dmg"
ICON_ASSET="$ROOT_DIR/installer/mac/assets/ClinicianDecon.icns"

rm -rf "$BUILD_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR/package" "$STAGE_DIR" "$DIST_DIR"

if [[ ! -f "$ICON_ASSET" ]]; then
  "$ROOT_DIR/installer/mac/create_icon_assets.py"
fi

cp "$ROOT_DIR/installer/mac/app/Info.native.plist" "$CONTENTS_DIR/Info.plist"
cp "$ROOT_DIR/installer/mac/app/clinician-decon-launcher" "$MACOS_DIR/clinician-decon-launcher"
chmod 755 "$MACOS_DIR/clinician-decon-launcher"
"$ROOT_DIR/installer/mac/build_native_wrapper.sh" "$MACOS_DIR/ClinicianDeconNative"
cp "$ICON_ASSET" "$RESOURCES_DIR/ClinicianDecon.icns"

rsync -a \
  --exclude ".DS_Store" \
  --exclude "__pycache__/" \
  --exclude ".pytest_cache/" \
  --exclude ".decon-home/" \
  --exclude "local-models/" \
  --exclude "package/local-models/" \
  --exclude "*.pyc" \
  "$ROOT_DIR/package/" "$RESOURCES_DIR/package/"

cp "$ROOT_DIR/LICENSE" "$RESOURCES_DIR/LICENSE"
cp "$ROOT_DIR/docs/install/mac-demo-readme.md" "$RESOURCES_DIR/README_FIRST.md"

plutil -lint "$CONTENTS_DIR/Info.plist" >/dev/null

cp -R "$APP_DIR" "$STAGE_DIR/$APP_NAME.app"
ln -s /Applications "$STAGE_DIR/Applications"
cp "$ROOT_DIR/docs/install/mac-demo-readme.md" "$STAGE_DIR/Read Me First.md"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "$DMG_PATH"
