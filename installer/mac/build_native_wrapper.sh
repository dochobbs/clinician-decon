#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_PATH="${1:?Usage: build_native_wrapper.sh /path/to/ClinicianDeconNative}"
SOURCE_PATH="$ROOT_DIR/installer/mac/native/ClinicianDeconApp.swift"
MODULE_CACHE_DIR="${CLANG_MODULE_CACHE_PATH:-$ROOT_DIR/build/swift-module-cache}"

if ! command -v xcrun >/dev/null 2>&1; then
  echo "xcrun is required to build the native macOS wrapper." >&2
  exit 1
fi

mkdir -p "$MODULE_CACHE_DIR"

xcrun swiftc \
  -O \
  -parse-as-library \
  -module-cache-path "$MODULE_CACHE_DIR" \
  -framework Cocoa \
  -framework WebKit \
  "$SOURCE_PATH" \
  -o "$OUTPUT_PATH"

chmod 755 "$OUTPUT_PATH"
