from decon.structured_boundary_eval import generate_structured_boundary_cases


def test_generate_structured_boundary_cases_is_deterministic_and_balanced():
  first = generate_structured_boundary_cases()
  second = generate_structured_boundary_cases()

  assert first == second
  assert len(first) == 144
  assert len({case.id for case in first}) == 144
  assert sum(bool(case.phi) for case in first) == 96
  assert sum(not case.phi for case in first) == 48
  assert all(case.critical_facts for case in first)
