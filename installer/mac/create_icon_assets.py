#!/usr/bin/env python3
"""Generate app and web icon assets without external imaging dependencies."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import subprocess
import zlib


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "installer" / "mac" / "assets"
ICONSET_DIR = ASSET_DIR / "ClinicianDecon.iconset"
WEB_ICON_DIR = ROOT / "package" / "web" / "icons"
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


def _point_in_polygon(x: float, y: float, points: tuple[tuple[float, float], ...]) -> bool:
  inside = False
  j = len(points) - 1
  for i, point in enumerate(points):
    xi, yi = point
    xj, yj = points[j]
    if (yi > y) != (yj > y):
      cross_x = (xj - xi) * (y - yi) / (yj - yi) + xi
      if x < cross_x:
        inside = not inside
    j = i
  return inside


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

  teal = (15, 118, 110, 255)
  teal_dark = (12, 82, 78, 255)
  white = (255, 255, 255, 242)

  radius = canvas_size * 0.22
  inset = canvas_size * 0.035
  for y in range(canvas_size):
    for x in range(canvas_size):
      cx = min(max(x, inset + radius), canvas_size - inset - radius)
      cy = min(max(y, inset + radius), canvas_size - inset - radius)
      if math.hypot(x - cx, y - cy) <= radius:
        shade = teal_dark if y > canvas_size * 0.78 else teal
        pixels[y * canvas_size + x] = shade

  shield = (
    (canvas_size * 0.50, canvas_size * 0.21),
    (canvas_size * 0.70, canvas_size * 0.30),
    (canvas_size * 0.66, canvas_size * 0.58),
    (canvas_size * 0.50, canvas_size * 0.77),
    (canvas_size * 0.34, canvas_size * 0.58),
    (canvas_size * 0.30, canvas_size * 0.30),
  )
  for y in range(canvas_size):
    for x in range(canvas_size):
      if _point_in_polygon(x + 0.5, y + 0.5, shield):
        pixels[y * canvas_size + x] = _blend(pixels[y * canvas_size + x], white)

  # Clinical document lines.
  for y_frac in (0.39, 0.48, 0.57):
    for y in range(round(canvas_size * y_frac - canvas_size * 0.008), round(canvas_size * y_frac + canvas_size * 0.008)):
      for x in range(round(canvas_size * 0.40), round(canvas_size * 0.61)):
        pixels[y * canvas_size + x] = _blend(pixels[y * canvas_size + x], (*teal_dark[:3], 210))

  # Check mark.
  check_segments = (
    (0.39, 0.67, 0.47, 0.74),
    (0.47, 0.74, 0.63, 0.57),
  )
  stroke = canvas_size * 0.025
  for y in range(canvas_size):
    for x in range(canvas_size):
      if any(
        _distance_to_segment(
          x + 0.5,
          y + 0.5,
          canvas_size * ax,
          canvas_size * ay,
          canvas_size * bx,
          canvas_size * by,
        ) <= stroke
        for ax, ay, bx, by in check_segments
      ):
        pixels[y * canvas_size + x] = _blend(pixels[y * canvas_size + x], (*teal_dark[:3], 235))

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


def main() -> int:
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
  _write_png(WEB_ICON_DIR / "icon-192.png", 192)
  _write_png(WEB_ICON_DIR / "icon-512.png", 512)
  favicon_png = WEB_ICON_DIR / "favicon-32.png"
  _write_png(favicon_png, 32)
  _write_ico(FAVICON_PATH, favicon_png)

  subprocess.run(["iconutil", "-c", "icns", "-o", str(ICNS_PATH), str(ICONSET_DIR)], check=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
