#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="Clinician Decon"
VERSION="0.1.0"
ARCH="$(uname -m)"
PYTHON_VERSION="${DECON_BUNDLE_PYTHON_VERSION:-3.13}"
MODEL_DIR_NAME="OpenMed--OpenMed-PII-SuperClinical-Large-434M-v1"
MODEL_SOURCE="${DECON_MODEL_SOURCE:-$ROOT_DIR/package/local-models/$MODEL_DIR_NAME}"
BUILD_DIR="$ROOT_DIR/build/mac-self-contained"
DIST_DIR="$ROOT_DIR/dist/mac"
APP_DIR="$BUILD_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
PYTHON_DIR="$RESOURCES_DIR/python"
PYTHON_PACKAGES_DIR="$RESOURCES_DIR/python-packages"
STAGE_DIR="$BUILD_DIR/dmg-root"
DMG_PATH="$DIST_DIR/Clinician-Decon-$VERSION-self-contained-$ARCH.dmg"
UV_CACHE_DIR="${UV_CACHE_DIR:-$BUILD_DIR/uv-cache}"
ICON_ASSET="$ROOT_DIR/installer/mac/assets/ClinicianDecon.icns"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to build the self-contained Mac DMG." >&2
  exit 1
fi

if [[ ! -d "$MODEL_SOURCE" ]]; then
  echo "Missing OpenMed model source: $MODEL_SOURCE" >&2
  echo "Run decon-setup-openmed --repo-local first, or set DECON_MODEL_SOURCE." >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR/package/local-models" "$STAGE_DIR" "$DIST_DIR" "$UV_CACHE_DIR"

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
  --exclude "*.pyc" \
  "$ROOT_DIR/package/" "$RESOURCES_DIR/package/"
rsync -a --exclude ".DS_Store" "$MODEL_SOURCE/" "$RESOURCES_DIR/package/local-models/$MODEL_DIR_NAME/"

UV_CACHE_DIR="$UV_CACHE_DIR" uv python install \
  --managed-python \
  "$PYTHON_VERSION"

MANAGED_PYTHON="$(
  UV_CACHE_DIR="$UV_CACHE_DIR" uv python find \
    --managed-python \
    --resolve-links \
    "$PYTHON_VERSION"
)"
MANAGED_PYTHON_ROOT="$(cd "$(dirname "$MANAGED_PYTHON")/.." && pwd)"
rsync -a --exclude ".DS_Store" "$MANAGED_PYTHON_ROOT/" "$PYTHON_DIR/"
mkdir -p "$PYTHON_PACKAGES_DIR"

UV_CACHE_DIR="$UV_CACHE_DIR" uv pip install \
  --python "$PYTHON_DIR/bin/python" \
  --target "$PYTHON_PACKAGES_DIR" \
  --link-mode copy \
  "$RESOURCES_DIR/package[openmed]"

rm -rf "$RESOURCES_DIR/package/build" "$RESOURCES_DIR/package/src/decon.egg-info"

DECON_HOME="$BUILD_DIR/decon-home" \
DECON_MODEL_DIR="$RESOURCES_DIR/package/local-models/$MODEL_DIR_NAME" \
PYTHONPATH="$RESOURCES_DIR/package/src:$PYTHON_PACKAGES_DIR" \
  "$PYTHON_DIR/bin/python" - <<'PY'
from decon.model_setup import get_model_status

status = get_model_status()
if not status.ner_model_ready:
  raise SystemExit(status.last_error)
print("Bundled OpenMed runtime ready")
PY

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
