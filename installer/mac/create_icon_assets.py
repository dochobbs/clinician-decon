#!/usr/bin/env python3
"""Generate app and web icon assets from the Decon mark."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import zlib


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "installer" / "mac" / "assets"
ICONSET_DIR = ASSET_DIR / "ClinicianDecon.iconset"
WEB_ICON_DIR = ROOT / "package" / "web" / "icons"
SOURCE_SVG_PATH = ROOT / "decon-mark.svg"
WEB_SVG_PATH = WEB_ICON_DIR / "decon-mark.svg"
ASSET_SVG_PATH = ASSET_DIR / "decon-mark.svg"
ICNS_PATH = ASSET_DIR / "ClinicianDecon.icns"
FAVICON_PATH = ROOT / "package" / "web" / "favicon.ico"


def _blend(dst: tuple[int, int, int, int], src: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
  sr, sg, sb, sa = src
  dr, dg, db, da = dst
  alpha = sa / 255
  inv = 1 - alpha
  return (
    round(sr * alpha + dr * inv),
    round(sg * alpha + dg * inv),
    round(sb * alpha + db * inv),
    round(255 * (alpha + da / 255 * inv)),
  )


def _distance_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
  dx = bx - ax
  dy = by - ay
  if dx == 0 and dy == 0:
    return math.hypot(px - ax, py - ay)
  t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
  closest_x = ax + t * dx
  closest_y = ay + t * dy
  return math.hypot(px - closest_x, py - closest_y)


def _draw_icon(size: int) -> bytes:
  scale = 4
  canvas_size = size * scale
  pixels = [(0, 0, 0, 0)] * (canvas_size * canvas_size)

  teal = (28, 107, 88, 255)
  white = (255, 255, 255, 255)
  seam_white = (255, 255, 255, 217)

  radius = canvas_size * 0.24
  inset = 0
  for y in range(canvas_size):
    for x in range(canvas_size):
      cx = min(max(x, inset + radius), canvas_size - inset - radius)
      cy = min(max(y, inset + radius), canvas_size - inset - radius)
      if math.hypot(x - cx, y - cy) <= radius:
        pixels[y * canvas_size + x] = teal

  seam_stroke = canvas_size * 0.03 / 2
  dot_radius = canvas_size * 0.08
  for y in range(canvas_size):
    for x in range(canvas_size):
      if _distance_to_segment(
        x + 0.5,
        y + 0.5,
        canvas_size * 0.50,
        canvas_size * 0.22,
        canvas_size * 0.50,
        canvas_size * 0.78,
      ) <= seam_stroke:
        pixels[y * canvas_size + x] = _blend(pixels[y * canvas_size + x], seam_white)
      if math.hypot((x + 0.5) - canvas_size * 0.30, (y + 0.5) - canvas_size * 0.50) <= dot_radius:
        pixels[y * canvas_size + x] = _blend(pixels[y * canvas_size + x], white)

  downsampled: list[tuple[int, int, int, int]] = []
  for y in range(size):
    for x in range(size):
      block = [
        pixels[(y * scale + yy) * canvas_size + (x * scale + xx)]
        for yy in range(scale)
        for xx in range(scale)
      ]
      downsampled.append(tuple(round(sum(channel) / len(block)) for channel in zip(*block)))

  return _png_bytes(size, size, downsampled)


def _png_bytes(width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> bytes:
  def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

  raw_rows = []
  for y in range(height):
    row = bytearray([0])
    for pixel in pixels[y * width:(y + 1) * width]:
      row.extend(pixel)
    raw_rows.append(bytes(row))
  data = zlib.compress(b"".join(raw_rows), level=9)
  header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
  return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", data) + chunk(b"IEND", b"")


def _write_png(path: Path, size: int) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(_draw_icon(size))


def _write_ico(path: Path, png_path: Path) -> None:
  data = png_path.read_bytes()
  header = struct.pack("<HHH", 0, 1, 1)
  entry = struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(data), 6 + 16)
  path.write_bytes(header + entry + data)


def _write_icns(path: Path, iconset_dir: Path) -> None:
  icon_elements = (
    ("ic04", "icon_16x16.png"),
    ("ic11", "icon_16x16@2x.png"),
    ("ic05", "icon_32x32.png"),
    ("ic12", "icon_32x32@2x.png"),
    ("ic07", "icon_128x128.png"),
    ("ic13", "icon_128x128@2x.png"),
    ("ic08", "icon_256x256.png"),
    ("ic14", "icon_256x256@2x.png"),
    ("ic09", "icon_512x512.png"),
    ("ic10", "icon_512x512@2x.png"),
  )
  chunks = []
  for icon_type, filename in icon_elements:
    data = (iconset_dir / filename).read_bytes()
    chunks.append(icon_type.encode("ascii") + struct.pack(">I", len(data) + 8) + data)
  body = b"".join(chunks)
  path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> int:
  if not SOURCE_SVG_PATH.is_file():
    raise FileNotFoundError(f"missing source icon: {SOURCE_SVG_PATH}")

  icon_specs = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
  }
  ICONSET_DIR.mkdir(parents=True, exist_ok=True)
  for filename, size in icon_specs.items():
    _write_png(ICONSET_DIR / filename, size)

  WEB_ICON_DIR.mkdir(parents=True, exist_ok=True)
  WEB_SVG_PATH.write_text(SOURCE_SVG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
  ASSET_DIR.mkdir(parents=True, exist_ok=True)
  ASSET_SVG_PATH.write_text(SOURCE_SVG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
  _write_png(WEB_ICON_DIR / "icon-192.png", 192)
  _write_png(WEB_ICON_DIR / "icon-512.png", 512)
  favicon_png = WEB_ICON_DIR / "favicon-32.png"
  _write_png(favicon_png, 32)
  _write_ico(FAVICON_PATH, favicon_png)

  _write_icns(ICNS_PATH, ICONSET_DIR)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
