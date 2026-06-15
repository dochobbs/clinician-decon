"""Destination prompt templates and copy/open handoff metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Destination:
  id: str
  name: str
  open_url: str | None


@dataclass(frozen=True)
class Handoff:
  destination: str
  copy_text: str
  open_url: str | None
  action_label: str


DESTINATIONS: dict[str, Destination] = {
  "chatgpt": Destination("chatgpt", "ChatGPT", "https://chatgpt.com/"),
  "gemini": Destination("gemini", "Gemini", "https://gemini.google.com/"),
  "claude": Destination("claude", "Claude", "https://claude.ai/"),
  "openevidence": Destination("openevidence", "OpenEvidence", "https://www.openevidence.com/"),
  "web_search": Destination("web_search", "Web Search", "https://www.google.com/"),
  "copy_only": Destination("copy_only", "Copy Only", None),
}


def require_destination(destination_id: str) -> Destination:
  """Return destination config or raise a clear validation error."""
  try:
    return DESTINATIONS[destination_id]
  except KeyError as exc:
    valid = ", ".join(sorted(DESTINATIONS))
    raise ValueError(f"unsupported destination '{destination_id}'. Valid destinations: {valid}") from exc


def render_prompt(destination_id: str, *, safe_context: str, safe_query: str | None = None) -> str:
  """Render destination-specific prompt text from already decontextualized content."""
  require_destination(destination_id)
  query = (safe_query or safe_context).strip()
  context = safe_context.strip()

  if destination_id in ("chatgpt", "gemini", "claude"):
    return (
      "Use the following de-identified clinical context. Do not assume missing patient "
      "identifiers. If you need patient-specific details that are absent, say what is "
      "missing rather than inventing.\n\n"
      f"{context}"
    )
  if destination_id == "openevidence":
    return (
      "Find current clinical evidence or guidelines for the following de-identified "
      f"clinical question:\n\n{query}"
    )
  if destination_id == "web_search":
    return query
  if destination_id == "copy_only":
    return context

  raise AssertionError("destination should have been validated")


def build_handoff(destination_id: str, prompt: str) -> Handoff:
  """Build copy/open metadata without embedding prompt text in URLs."""
  destination = require_destination(destination_id)
  if destination.open_url is None:
    return Handoff(
      destination=destination.id,
      copy_text=prompt,
      open_url=None,
      action_label="Copy Only",
    )
  return Handoff(
    destination=destination.id,
    copy_text=prompt,
    open_url=destination.open_url,
    action_label=f"Copy & Open {destination.name}",
  )
