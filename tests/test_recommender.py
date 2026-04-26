import pytest

from src.recommender import (
    Recommender,
    Song,
    UserProfile,
    recommend_songs_with_reliability,
)


def make_songs():
    return [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Lofi Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]


def make_small_recommender() -> Recommender:
    return Recommender(make_songs())


def make_song_dicts():
    return [song.__dict__ for song in make_songs()]


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""
    assert "Confidence" in explanation


def test_confidence_scores_are_between_zero_and_one():
    user = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "likes_acoustic": False,
    }
    run = recommend_songs_with_reliability(user, make_song_dicts(), k=2, audit_log_path=None)

    assert len(run.recommendations) == 2
    for result in run.recommendations:
        assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= run.reliability.average_confidence <= 1.0


def test_invalid_energy_is_rejected():
    user = {
        "genre": "pop",
        "mood": "happy",
        "energy": 1.5,
        "likes_acoustic": False,
    }

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        recommend_songs_with_reliability(user, make_song_dicts(), k=2, audit_log_path=None)


def test_empty_catalog_returns_warning_not_crash():
    user = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "likes_acoustic": False,
    }
    run = recommend_songs_with_reliability(user, [], k=2, audit_log_path=None)

    assert run.recommendations == []
    assert run.reliability.recommendation_count == 0
    assert run.reliability.warnings


def test_invalid_k_is_rejected():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()

    with pytest.raises(ValueError, match="positive integer"):
        rec.recommend(user, k=0)
