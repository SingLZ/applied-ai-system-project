"""Bonus reliability test harness for the music recommender system.

Runs the integrated recommender on predefined valid and invalid inputs and prints
pass/fail results, confidence ratings, and guardrail outcomes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import USER_PROFILES  # noqa: E402
from src.recommender import (  # noqa: E402
    evaluate_reliability,
    load_songs,
    recommend_songs_with_reliability,
)


GuardrailCase = Tuple[str, Dict[str, Any], int, str]


def _load_catalog() -> List[Dict[str, Any]]:
    csv_path = PROJECT_ROOT / "data" / "songs.csv"
    return load_songs(str(csv_path))


def run_valid_profile_tests(songs: List[Dict[str, Any]]) -> Tuple[int, int, List[float]]:
    print("\nValid profile tests:")
    passed = 0
    confidences: List[float] = []

    for profile_name, profile in USER_PROFILES.items():
        try:
            run = recommend_songs_with_reliability(profile, songs, k=5, audit_log_path=None)
            is_pass = bool(run.recommendations) and run.reliability.guardrail_status == "passed"
            passed += int(is_pass)
            confidences.append(run.reliability.average_confidence)
            status = "PASS" if is_pass else "FAIL"
            print(f"- {profile_name}: {status} | avg confidence {run.reliability.average_confidence:.2f}")
        except Exception as exc:  # pragma: no cover - defensive CLI reporting
            print(f"- {profile_name}: FAIL | unexpected error: {exc}")

    return passed, len(USER_PROFILES), confidences


def run_guardrail_tests(songs: List[Dict[str, Any]]) -> Tuple[int, int]:
    cases: List[GuardrailCase] = [
        (
            "Invalid energy 1.5",
            {"genre": "pop", "mood": "happy", "energy": 1.5, "likes_acoustic": False},
            5,
            "between 0.0 and 1.0",
        ),
        (
            "Empty genre",
            {"genre": "", "mood": "happy", "energy": 0.8, "likes_acoustic": False},
            5,
            "non-empty string",
        ),
        (
            "Invalid k=0",
            {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False},
            0,
            "positive integer",
        ),
    ]

    print("\nGuardrail tests:")
    passed = 0
    for name, profile, k, expected_message in cases:
        try:
            recommend_songs_with_reliability(profile, songs, k=k, audit_log_path=None)
            print(f"- {name}: FAIL | input was accepted unexpectedly")
        except ValueError as exc:
            is_pass = expected_message in str(exc)
            passed += int(is_pass)
            status = "PASS" if is_pass else "FAIL"
            print(f"- {name}: {status} | rejected with: {exc}")

    return passed, len(cases)


def run_empty_catalog_test() -> bool:
    profile = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    run = recommend_songs_with_reliability(profile, [], k=5, audit_log_path=None)
    passed = not run.recommendations and bool(run.reliability.warnings)
    print("\nEmpty catalog test:")
    print(
        f"- Empty catalog behavior: {'PASS' if passed else 'FAIL'} | "
        f"recommendations={len(run.recommendations)}, warnings={len(run.reliability.warnings)}"
    )
    return passed


def main() -> int:
    print("=== Reliability Evaluation Harness ===")
    songs = _load_catalog()
    if not songs:
        print("FAIL: no songs loaded; cannot run evaluation harness")
        return 1

    valid_passed, valid_total, confidences = run_valid_profile_tests(songs)
    guardrail_passed, guardrail_total = run_guardrail_tests(songs)
    empty_catalog_passed = run_empty_catalog_test()
    evaluation = evaluate_reliability(USER_PROFILES, songs, k=5)

    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    all_passed = (
        valid_passed == valid_total
        and guardrail_passed == guardrail_total
        and empty_catalog_passed
    )

    print("\nSummary:")
    print(f"Profiles tested: {valid_total}")
    print(f"Valid profile passes: {valid_passed}/{valid_total}")
    print(f"Guardrail tests passed: {guardrail_passed}/{guardrail_total}")
    print(f"Empty catalog test passed: {1 if empty_catalog_passed else 0}/1")
    print(f"Average confidence: {average_confidence:.2f}")
    print(f"Low-confidence cases: {len(evaluation['low_confidence_cases'])}")
    print(f"Overall status: {'PASS' if all_passed else 'FAIL'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
