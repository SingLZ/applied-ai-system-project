"""Core recommendation and reliability logic for the music recommender."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union


WEIGHTS: Dict[str, float] = {
    "genre": 3.0,
    "mood": 2.0,
    "energy": 1.5,
    "acoustic": 0.5,
}
MAX_SCORE = sum(WEIGHTS.values())
DEFAULT_AUDIT_LOG_PATH = os.path.join("logs", "recommendation_audit.jsonl")


@dataclass(frozen=True)
class Song:
    """Represents a song and its attributes."""

    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass(frozen=True)
class UserProfile:
    """Represents a user's taste preferences."""

    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


@dataclass(frozen=True)
class RecommendationResult:
    """Structured recommendation output used by the reliability layer."""

    song: Song
    score: float
    confidence: float
    explanation: str


@dataclass(frozen=True)
class ReliabilitySummary:
    """Run-level reliability information returned with recommendations."""

    average_confidence: float
    lowest_confidence: float
    guardrail_status: str
    warnings: List[str]
    recommendation_count: int


@dataclass(frozen=True)
class RecommendationRun:
    """Full recommendation response: recommendations plus reliability metadata."""

    recommendations: List[RecommendationResult]
    reliability: ReliabilitySummary


ProfileInput = Union[UserProfile, Mapping[str, Any]]
SongInput = Union[Song, Mapping[str, Any]]


class Recommender:
    """OOP implementation of the recommendation logic."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs sorted by recommendation score."""
        run = self.recommend_with_reliability(user, k=k, audit_log_path=None)
        return [result.song for result in run.recommendations]

    def recommend_with_reliability(
        self,
        user: UserProfile,
        k: int = 5,
        audit_log_path: Optional[str] = DEFAULT_AUDIT_LOG_PATH,
    ) -> RecommendationRun:
        """Return recommendations with confidence, guardrails, warnings, and logging."""
        normalized_user = validate_user_profile(user, k)
        results = _rank_song_objects(normalized_user, self.songs, k)
        summary = build_reliability_summary(results)

        if audit_log_path is not None:
            log_recommendation_run(
                profile=normalized_user,
                recommendations=results,
                summary=summary,
                audit_log_path=audit_log_path,
            )

        return RecommendationRun(recommendations=results, reliability=summary)

    def _score_song_oop(self, user: UserProfile, song: Song) -> float:
        """Score a single song against a user profile."""
        return _score_song_object(user, song)[0]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a readable explanation for why a song was recommended."""
        _, reasons = _score_song_object(validate_user_profile(user, 1), song)
        confidence = confidence_from_score(self._score_song_oop(user, song))
        return " | ".join(reasons + [f"Confidence: {confidence:.2f}"])


def load_songs(csv_path: str) -> List[Dict[str, Any]]:
    """Load songs from CSV and convert numerical values to Python numeric types."""
    songs: List[Dict[str, Any]] = []
    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                songs.append(
                    {
                        "id": int(row["id"]),
                        "title": row["title"],
                        "artist": row["artist"],
                        "genre": row["genre"],
                        "mood": row["mood"],
                        "energy": float(row["energy"]),
                        "tempo_bpm": int(row["tempo_bpm"]),
                        "valence": float(row["valence"]),
                        "danceability": float(row["danceability"]),
                        "acousticness": float(row["acousticness"]),
                    }
                )
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}")
        return []
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid song CSV schema or value in {csv_path}: {exc}") from exc

    print(f"✓ Loaded {len(songs)} songs from {csv_path}")
    return songs


def score_song(user_prefs: Dict[str, Any], song: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Score a single song against user preferences using the weighted formula.

    Returns: (total_score, list_of_reasons)
    """
    user = validate_user_profile(user_prefs, k=1)
    score, reasons = _score_song_object(user, _song_dict_to_dataclass(song))
    return score, reasons


def recommend_songs(
    user_prefs: Dict[str, Any], songs: List[Dict[str, Any]], k: int = 5
) -> List[Tuple[Dict[str, Any], float, str]]:
    """
    Backward-compatible API: return top-k `(song_dict, score, explanation)` tuples.

    The explanation now includes confidence and reliability notes so the reliability
    layer is part of the main recommendation output, not only a standalone script.
    """
    run = recommend_songs_with_reliability(user_prefs, songs, k=k, audit_log_path=None)
    song_by_id = {song["id"]: song for song in songs}

    return [
        (
            song_by_id[result.song.id],
            result.score,
            f"{result.explanation}\n  Confidence: {result.confidence:.2f}",
        )
        for result in run.recommendations
    ]


def recommend_songs_with_reliability(
    user_prefs: Dict[str, Any],
    songs: List[Dict[str, Any]],
    k: int = 5,
    audit_log_path: Optional[str] = DEFAULT_AUDIT_LOG_PATH,
) -> RecommendationRun:
    """Functional API that returns recommendations plus integrated reliability data."""
    user = validate_user_profile(user_prefs, k)
    song_objects = [_song_dict_to_dataclass(song) for song in songs]
    results = _rank_song_objects(user, song_objects, k)
    summary = build_reliability_summary(results)

    if audit_log_path is not None:
        log_recommendation_run(
            profile=user,
            recommendations=results,
            summary=summary,
            audit_log_path=audit_log_path,
        )

    return RecommendationRun(recommendations=results, reliability=summary)


def evaluate_reliability(
    profiles: Mapping[str, Dict[str, Any]],
    songs: List[Dict[str, Any]],
    k: int = 5,
) -> Dict[str, Any]:
    """Run the recommender across multiple profiles and summarize reliability."""
    profile_reports: List[Dict[str, Any]] = []
    valid_profile_count = 0

    for profile_name, profile in profiles.items():
        try:
            run = recommend_songs_with_reliability(profile, songs, k=k, audit_log_path=None)
            valid_profile_count += 1
            profile_reports.append(
                {
                    "profile_name": profile_name,
                    "average_confidence": run.reliability.average_confidence,
                    "lowest_confidence": run.reliability.lowest_confidence,
                    "warnings": run.reliability.warnings,
                    "recommendation_count": run.reliability.recommendation_count,
                }
            )
        except ValueError as exc:
            profile_reports.append(
                {
                    "profile_name": profile_name,
                    "error": str(exc),
                    "average_confidence": 0.0,
                    "lowest_confidence": 0.0,
                    "warnings": ["profile failed guardrails"],
                    "recommendation_count": 0,
                }
            )

    confidences = [report["average_confidence"] for report in profile_reports if "error" not in report]
    low_confidence_cases = [
        report["profile_name"]
        for report in profile_reports
        if report.get("average_confidence", 0.0) < 0.75
    ]

    return {
        "profiles_evaluated": len(profiles),
        "valid_profiles": valid_profile_count,
        "average_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
        "low_confidence_cases": low_confidence_cases,
        "profile_reports": profile_reports,
    }


def validate_user_profile(user: ProfileInput, k: int) -> UserProfile:
    """Validate and normalize user profile input before scoring."""
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")

    if isinstance(user, UserProfile):
        profile = user
    elif isinstance(user, Mapping):
        profile = UserProfile(
            favorite_genre=str(user.get("favorite_genre", user.get("genre", ""))).strip(),
            favorite_mood=str(user.get("favorite_mood", user.get("mood", ""))).strip(),
            target_energy=_require_number(user.get("target_energy", user.get("energy")), "target_energy/energy"),
            likes_acoustic=user.get("likes_acoustic"),
        )
    else:
        raise ValueError("user profile must be a UserProfile or dictionary")

    if not isinstance(profile.favorite_genre, str) or not profile.favorite_genre.strip():
        raise ValueError("favorite_genre/genre must be a non-empty string")
    if not isinstance(profile.favorite_mood, str) or not profile.favorite_mood.strip():
        raise ValueError("favorite_mood/mood must be a non-empty string")
    if not 0.0 <= profile.target_energy <= 1.0:
        raise ValueError("target_energy/energy must be between 0.0 and 1.0")
    if not isinstance(profile.likes_acoustic, bool):
        raise ValueError("likes_acoustic must be a boolean")

    return UserProfile(
        favorite_genre=profile.favorite_genre.strip(),
        favorite_mood=profile.favorite_mood.strip(),
        target_energy=float(profile.target_energy),
        likes_acoustic=profile.likes_acoustic,
    )


def confidence_from_score(score: float) -> float:
    """Normalize a raw score into a 0.0-1.0 confidence value."""
    return max(0.0, min(1.0, score / MAX_SCORE))


def build_reliability_summary(results: List[RecommendationResult]) -> ReliabilitySummary:
    """Build run-level confidence and diversity warnings."""
    if not results:
        return ReliabilitySummary(
            average_confidence=0.0,
            lowest_confidence=0.0,
            guardrail_status="passed",
            warnings=["No songs available for recommendation."],
            recommendation_count=0,
        )

    confidences = [result.confidence for result in results]
    warnings = _build_diversity_warnings(results)

    return ReliabilitySummary(
        average_confidence=round(sum(confidences) / len(confidences), 3),
        lowest_confidence=round(min(confidences), 3),
        guardrail_status="passed",
        warnings=warnings,
        recommendation_count=len(results),
    )


def log_recommendation_run(
    profile: UserProfile,
    recommendations: List[RecommendationResult],
    summary: ReliabilitySummary,
    audit_log_path: str = DEFAULT_AUDIT_LOG_PATH,
) -> None:
    """Append a JSONL audit record. Logging failures do not crash recommendation."""
    try:
        directory = os.path.dirname(audit_log_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        top_song = recommendations[0].song.title if recommendations else None
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "profile": asdict(profile),
            "top_recommendation": top_song,
            "average_confidence": summary.average_confidence,
            "lowest_confidence": summary.lowest_confidence,
            "guardrail_status": summary.guardrail_status,
            "warnings": summary.warnings,
            "recommendation_count": summary.recommendation_count,
        }

        with open(audit_log_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"Warning: recommendation audit log was not written: {exc}")


def _rank_song_objects(user: UserProfile, songs: List[Song], k: int) -> List[RecommendationResult]:
    if not songs:
        return []

    scored_results = []
    for song in songs:
        score, reasons = _score_song_object(user, song)
        scored_results.append(
            RecommendationResult(
                song=song,
                score=score,
                confidence=confidence_from_score(score),
                explanation="\n  ".join(reasons),
            )
        )

    scored_results.sort(key=lambda result: result.score, reverse=True)
    return scored_results[:k]


def _score_song_object(user: UserProfile, song: Song) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []

    if song.genre.lower() == user.favorite_genre.lower():
        genre_score = 1.0
        reasons.append(f"Genre match: {song.genre} (+{WEIGHTS['genre']:.1f})")
    else:
        genre_score = 0.5
        reasons.append(
            f"Genre mismatch: {song.genre} (expected {user.favorite_genre}) "
            f"(+{WEIGHTS['genre'] * genre_score:.1f})"
        )
    score += WEIGHTS["genre"] * genre_score

    if song.mood.lower() == user.favorite_mood.lower():
        mood_score = 1.0
        reasons.append(f"Mood match: {song.mood} (+{WEIGHTS['mood']:.1f})")
    else:
        mood_score = 0.0
        reasons.append(f"Mood mismatch: {song.mood} (expected {user.favorite_mood}) (+0.0)")
    score += WEIGHTS["mood"] * mood_score

    energy_similarity = max(0.0, 1.0 - abs(user.target_energy - song.energy))
    energy_contribution = WEIGHTS["energy"] * energy_similarity
    score += energy_contribution
    reasons.append(
        f"Energy match: {song.energy:.2f} (target {user.target_energy:.2f}) "
        f"(+{energy_contribution:.2f})"
    )

    if user.likes_acoustic:
        acoustic_score = song.acousticness
        reasons.append(
            f"Acoustic preference: {song.acousticness:.2f} "
            f"(+{WEIGHTS['acoustic'] * acoustic_score:.2f})"
        )
    else:
        acoustic_score = 1.0 - song.acousticness
        reasons.append(
            f"Electronic preference: {song.acousticness:.2f} "
            f"(+{WEIGHTS['acoustic'] * acoustic_score:.2f})"
        )
    score += WEIGHTS["acoustic"] * acoustic_score

    return round(score, 3), reasons


def _build_diversity_warnings(results: List[RecommendationResult]) -> List[str]:
    warnings: List[str] = []
    if len(results) < 2:
        return warnings

    artists = [result.song.artist for result in results]
    genres = [result.song.genre for result in results]
    artist_counts = Counter(artists)
    genre_counts = Counter(genres)

    most_common_artist, artist_count = artist_counts.most_common(1)[0]
    most_common_genre, genre_count = genre_counts.most_common(1)[0]

    if artist_count / len(results) >= 0.4 and artist_count > 1:
        warnings.append(
            f"Diversity warning: artist '{most_common_artist}' appears {artist_count}/{len(results)} times."
        )
    if genre_count / len(results) >= 0.6 and genre_count > 1:
        warnings.append(
            f"Diversity warning: genre '{most_common_genre}' appears {genre_count}/{len(results)} times."
        )
    if min(result.confidence for result in results) < 0.6:
        warnings.append("Low-confidence warning: at least one recommendation scored below 0.60 confidence.")

    return warnings


def _song_dict_to_dataclass(song: Mapping[str, Any]) -> Song:
    try:
        return Song(
            id=int(song["id"]),
            title=str(song["title"]),
            artist=str(song["artist"]),
            genre=str(song["genre"]),
            mood=str(song["mood"]),
            energy=float(song["energy"]),
            tempo_bpm=float(song["tempo_bpm"]),
            valence=float(song["valence"]),
            danceability=float(song["danceability"]),
            acousticness=float(song["acousticness"]),
        )
    except KeyError as exc:
        raise ValueError(f"song is missing required field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"song contains invalid numeric value: {exc}") from exc


def _require_number(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number, not a boolean")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
