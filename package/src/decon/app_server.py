"""Local HTTP app for the Decon desktop prototype."""

from __future__ import annotations

from dataclasses import asdict
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .local_rules import OPENMED_ENGINE, SUPPORTED_ENGINES, decontextualize_text
from .model_setup import get_model_status


WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


def build_setup_status_payload() -> dict[str, Any]:
  """Build JSON-safe setup status for the frontend."""
  return get_model_status().as_dict()


def build_decon_payload(request: dict[str, Any]) -> dict[str, Any]:
  """Build a decon API response without returning raw source text or removed values."""
  text = str(request.get("text", ""))
  destination = str(request.get("destination", "copy_only"))
  engine = str(request.get("engine", OPENMED_ENGINE))
  if not text.strip():
    return {
      "error": "empty_text",
      "copy_allowed": False,
      "risk_level": "high",
      "risk_reasons": ["Paste clinical text before running decon."],
    }
  if engine not in SUPPORTED_ENGINES:
    return {
      "error": "unsupported_engine",
      "message": (
        f"Unsupported decon engine '{engine}'. "
        f"Supported engines: {', '.join(sorted(SUPPORTED_ENGINES))}."
      ),
      "copy_allowed": False,
      "risk_level": "high",
      "risk_reasons": ["Unsupported decon engine."],
    }

  try:
    result = decontextualize_text(text, destination=destination, engine=engine)
  except ValueError as exc:
    return {
      "error": "unsupported_destination",
      "message": str(exc),
      "copy_allowed": False,
      "risk_level": "high",
      "risk_reasons": ["Unsupported destination."],
    }

  return {
    "original_length": result.original_length,
    "destination": result.destination,
    "safe_context": result.safe_context,
    "safe_query": result.safe_query,
    "destination_prompt": result.destination_prompt,
    "removed_categories": result.removed_categories,
    "risk_level": result.risk_level,
    "risk_reasons": result.risk_reasons,
    "copy_allowed": result.copy_allowed,
    "engine": result.engine,
    "engine_requested": result.engine_requested,
    "engine_fallback_reason": result.engine_fallback_reason,
    "handoff": {
      "copy_text": result.destination_prompt,
      "open_url": result.open_url,
      "action_label": result.action_label,
    },
  }


class DeconRequestHandler(SimpleHTTPRequestHandler):
  """Serve static UI and local JSON endpoints."""

  def __init__(self, *args: Any, **kwargs: Any):
    super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

  def end_headers(self) -> None:
    self.send_header("Cache-Control", "no-store, max-age=0")
    super().end_headers()

  def do_GET(self) -> None:
    parsed = urlparse(self.path)
    if parsed.path == "/api/setup/status":
      self._send_json(build_setup_status_payload())
      return
    if parsed.path == "/":
      self.path = "/index.html"
    super().do_GET()

  def do_POST(self) -> None:
    parsed = urlparse(self.path)
    if parsed.path != "/api/decon":
      self.send_error(HTTPStatus.NOT_FOUND)
      return
    content_length = int(self.headers.get("Content-Length", "0"))
    body = self.rfile.read(content_length) if content_length else b"{}"
    try:
      payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
      self._send_json({"error": "invalid_json", "copy_allowed": False}, status=HTTPStatus.BAD_REQUEST)
      return
    self._send_json(build_decon_payload(payload))

  def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
    body = json.dumps(payload).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8769) -> None:
  server = ThreadingHTTPServer((host, port), DeconRequestHandler)
  print(f"Decon local app running at http://{host}:{port}")
  server.serve_forever()


def main() -> None:
  run()


if __name__ == "__main__":
  main()
