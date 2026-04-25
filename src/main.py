"""Command-line runner for the explainable music recommendation reliability system."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from .recommender import evaluate_reliability, load_songs, recommend_songs_with_reliability


USER_PROFILES: Dict[str, Dict[str, Any]] = {
    "Happy Pop Enthusiast": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.80,
        "likes_acoustic": False,
    },
    "Chill Lofi Listener": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.40,
        "likes_acoustic": True,
    },
    "Intense Rock Fan": {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.90,
        "likes_acoustic": False,
    },
    "Workout Enthusiast": {
        "genre": "pop",
        "mood": "intense",
        "energy": 0.92,
        "likes_acoustic": False,
    },
    "Acoustic Soul Seeker": {
        "genre": "acoustic",
        "mood": "relaxed",
        "energy": 0.32,
        "likes_acoustic": True,
    },
    "Energetic EDM Dancer": {
        "genre": "electronic",
        "mood": "happy",
        "energy": 0.88,
        "likes_acoustic": False,
    },
    "Jazz & Blues Lover": {
        "genre": "jazz",
        "mood": "relaxed",
        "energy": 0.37,
        "likes_acoustic": True,
    },
    "Sad Contemplative Soul": {
        "genre": "pop",
        "mood": "sad",
        "energy": 0.38,
        "likes_acoustic": True,
    },
}


def format_recommendations_table(recommendations: list, profile_name: str) -> str:
    """Format structured recommendation results as a readable terminal table."""
    rank_width = 3
    title_width = 25
    artist_width = 20
    score_width = 9
    conf_width = 10
    mood_width = 12
    energy_width = 8

    table = []
    table.append(
        f"  {'Rank':<{rank_width}} | {'Title':<{title_width}} | {'Artist':<{artist_width}} | "
        f"{'Score':<{score_width}} | {'Confidence':<{conf_width}} | {'Mood':<{mood_width}} | {'Energy':<{energy_width}}"
    )
    table.append(
        "  "
        + "-"
        * (
            rank_width
            + title_width
            + artist_width
            + score_width
            + conf_width
            + mood_width
            + energy_width
            + 21
        )
    )

    for i, result in enumerate(recommendations, 1):
        song = result.song
        row = (
            f"  {str(i) + '.':<{rank_width}} | {song.title[:title_width]:<{title_width}} | "
            f"{song.artist[:artist_width]:<{artist_width}} | {result.score:.2f}/7.0  | "
            f"{result.confidence:.2f}      | {song.mood[:mood_width]:<{mood_width}} | "
            f"{song.energy:.2f}    "
        )
        table.append(row)

    return "\n".join(table)


def _profile_lines(user_prefs: Dict[str, Any]) -> List[str]:
    return [
        f"  • Favorite Genre: {user_prefs['genre'].title()}",
        f"  • Favorite Mood: {user_prefs['mood'].title()}",
        f"  • Target Energy: {user_prefs['energy']:.1f}/1.0",
        f"  • Prefers Acoustic: {'Yes' if user_prefs['likes_acoustic'] else 'No (Electronic)'}",
    ]


def main() -> None:
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "songs.csv")
    songs = load_songs(csv_path)

    if not songs:
        print("No songs loaded. Exiting.")
        return

    print("\n" + "=" * 78)
    print("MUSIC RECOMMENDER RELIABILITY SYSTEM")
    print("=" * 78)

    for profile_name, user_prefs in USER_PROFILES.items():
        print("\n" + "=" * 78)
        print(f"PROFILE: {profile_name}")
        print("=" * 78)
        print("\n".join(_profile_lines(user_prefs)))

        run = recommend_songs_with_reliability(user_prefs, songs, k=5)

        print("\nTOP 5 RECOMMENDATIONS:")
        print("-" * 78)
        print(format_recommendations_table(run.recommendations, profile_name))

        print("\nDETAILED EXPLANATIONS:")
        print("-" * 78)
        for i, result in enumerate(run.recommendations, 1):
            print(
                f"\n{i}. {result.song.title} "
                f"(Score: {result.score:.2f}/7.0, Confidence: {result.confidence:.2f})"
            )
            for line in result.explanation.split("\n"):
                print(f"   • {line.strip()}")

        print("\nRELIABILITY SUMMARY:")
        print(f"  • Guardrails: {run.reliability.guardrail_status}")
        print(f"  • Average confidence: {run.reliability.average_confidence:.2f}")
        print(f"  • Lowest confidence: {run.reliability.lowest_confidence:.2f}")
        if run.reliability.warnings:
            for warning in run.reliability.warnings:
                print(f"  • {warning}")
        else:
            print("  • No reliability warnings")

    evaluation = evaluate_reliability(USER_PROFILES, songs, k=5)
    print("\n" + "=" * 78)
    print("OVERALL RELIABILITY REPORT")
    print("=" * 78)
    print(f"Profiles evaluated: {evaluation['profiles_evaluated']}")
    print(f"Valid profiles passed guardrails: {evaluation['valid_profiles']}")
    print(f"Average confidence across profiles: {evaluation['average_confidence']:.2f}")
    if evaluation["low_confidence_cases"]:
        print("Low-confidence cases: " + ", ".join(evaluation["low_confidence_cases"]))
    else:
        print("Low-confidence cases: none")
    print("Audit log: logs/recommendation_audit.jsonl")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
