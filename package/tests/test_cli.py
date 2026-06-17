import json

from decon.cli import main


def test_cli_prints_local_safe_prompt(capsys):
  exit_code = main([
    "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 needs vaccine guidance",
    "--destination",
    "web_search",
  ])

  captured = capsys.readouterr()

  assert exit_code == 0
  assert "Marcus" not in captured.out
  assert "Johnson" not in captured.out
  assert "3/15/2013" not in captured.out
  assert "LP-2024-08432" not in captured.out
  assert "vaccine" in captured.out.lower()


def test_cli_json_outputs_local_metadata(capsys):
  exit_code = main([
    "Mom Jennifer asks about guanfacine for Marvin before camp July 12",
    "--json",
  ])

  captured = capsys.readouterr()
  payload = json.loads(captured.out)

  assert exit_code == 0
  assert payload["engine"] in {"local-rules", "rules+openmed"}
  assert payload["destination"] == "copy"
  assert "name" in payload["removed_categories"]
  assert "Jennifer" not in payload["destination_prompt"]
  assert "Marvin" not in payload["destination_prompt"]
