from decon.destinations import build_handoff, render_prompt


def test_chatgpt_gemini_and_claude_templates_include_safe_context():
  safe = "adolescent immunization schedule, no patient identifiers"

  for destination in ("chatgpt", "gemini", "claude"):
    prompt = render_prompt(destination, safe_context=safe)

    assert safe in prompt
    assert "Do not assume missing patient identifiers" in prompt


def test_open_evidence_and_web_search_use_safe_query():
  prompt = render_prompt(
    "openevidence",
    safe_context="longer safe context",
    safe_query="pediatric asthma step therapy current guidelines",
  )
  search_prompt = render_prompt(
    "web_search",
    safe_context="longer safe context",
    safe_query="pediatric asthma step therapy current guidelines",
  )

  assert prompt.startswith("Find current clinical evidence")
  assert "pediatric asthma step therapy current guidelines" in prompt
  assert search_prompt == "pediatric asthma step therapy current guidelines"


def test_handoff_never_embeds_prompt_in_destination_url():
  sensitive_safe_prompt = "de-identified but still clinical prompt with A1c 8.2"

  for destination in ("chatgpt", "gemini", "claude", "openevidence", "web_search"):
    handoff = build_handoff(destination, sensitive_safe_prompt)

    assert handoff.copy_text == sensitive_safe_prompt
    assert sensitive_safe_prompt not in handoff.open_url
    assert handoff.open_url.startswith("https://")
    assert "Copy & Open" in handoff.action_label


def test_copy_only_has_no_open_url():
  prompt = "safe context"

  handoff = build_handoff("copy_only", prompt)

  assert handoff.copy_text == prompt
  assert handoff.open_url is None
  assert handoff.action_label == "Copy Only"
