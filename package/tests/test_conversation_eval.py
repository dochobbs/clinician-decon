from decon.conversation_eval import generate_cross_turn_cases


def test_cross_turn_suite_is_deterministic_and_balanced():
  cases = generate_cross_turn_cases()

  assert len(cases) == 260
  assert len({case.id for case in cases}) == 260
  assert sum(bool(case.phi) for case in cases) == 180
  assert sum(not case.phi for case in cases) == 80
  assert cases == generate_cross_turn_cases()
