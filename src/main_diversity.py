"""
Diversity-Enhanced Music Recommender

Implements a diversity penalty to prevent the same artist or genre 
from dominating the top recommendations. This addresses a real-world
fairness concern: systems that always recommend popular songs can
miss deserving artists and create "rich get richer" dynamics.
"""

from typing import List, Dict, Tuple
from .recommender import load_songs, recommend_songs as baseline_recommend
import os


def recommend_songs_with_diversity(
    user_prefs: Dict, 
    songs: List[Dict], 
    k: int = 5,
    diversity_mode: str = "balanced"
) -> List[Tuple]:
    """
    Recommend songs with diversity penalty to avoid artist/genre monotony.
    
    Args:
        user_prefs: User preference dictionary
        songs: List of song dictionaries
        k: Number of recommendations to return
        diversity_mode: 
            - "baseline": No diversity penalty (original algorithm)
            - "artist_diversity": Penalize repetition of artists
            - "genre_diversity": Penalize repetition of genres
            - "balanced": Penalize both artist and genre repetition
    
    Returns:
        List of (song, score, explanation) tuples with diversity penalties applied
    """
    
    # First, get scored songs from baseline algorithm
    from .recommender import score_song
    scored_songs = []
    for song in songs:
        score, explanation = score_song(user_prefs, song)
        scored_songs.append((song, score, explanation))
    
    if diversity_mode == "baseline":
        # No penalty, just sort and return
        scored_songs.sort(key=lambda x: x[1], reverse=True)
        return scored_songs[:k]
    
    # Apply diversity penalties
    final_recommendations = []
    selected_artists = set()
    selected_genres = set()
    
    # Sort by original score
    scored_songs.sort(key=lambda x: x[1], reverse=True)
    
    for song, original_score, explanation_list in scored_songs:
        # Convert explanation list to string if needed
        if isinstance(explanation_list, list):
            explanation = "\n".join(explanation_list)
        else:
            explanation = explanation_list
            
        penalty = 0.0
        penalty_reasons = []
        
        # Artist diversity penalty
        if diversity_mode in ["artist_diversity", "balanced"]:
            if song['artist'] in selected_artists:
                penalty += 0.8  # Reduce by 0.8 points if artist already selected
                penalty_reasons.append(f"Artist '{song['artist']}' already in top picks (-0.8)")
        
        # Genre diversity penalty
        if diversity_mode in ["genre_diversity", "balanced"]:
            if song['genre'] in selected_genres:
                penalty += 0.5  # Reduce by 0.5 points if genre already selected
                penalty_reasons.append(f"Genre '{song['genre']}' already represented (-0.5)")
        
        # Apply penalty
        adjusted_score = max(0.0, original_score - penalty)
        
        # Update explanation with diversity info
        if penalty > 0.0:
            diversity_note = "\n" + "\n".join([f"Diversity: {reason}" for reason in penalty_reasons])
            diversity_note += f"\nAdjusted Score: {adjusted_score:.2f} (was {original_score:.2f})"
        else:
            diversity_note = ""
        
        adjusted_explanation = explanation + diversity_note
        
        final_recommendations.append((song, adjusted_score, adjusted_explanation))
        
        # Track selections
        selected_artists.add(song['artist'])
        selected_genres.add(song['genre'])
        
        if len(final_recommendations) >= k:
            break
    
    # If we haven't found k recommendations yet, add remaining songs
    # (this shouldn't happen with a diverse dataset, but handle it safely)
    if len(final_recommendations) < k:
        for song, original_score, explanation in scored_songs:
            if not any(s[0]['id'] == song['id'] for s in final_recommendations):
                final_recommendations.append((song, original_score, explanation))
                if len(final_recommendations) >= k:
                    break
    
    return final_recommendations[:k]


def main() -> None:
    """
    Demonstrate diversity modes by comparing recommendations.
    """
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "songs.csv")
    songs = load_songs(csv_path)
    
    if not songs:
        print("No songs loaded. Exiting.")
        return
    
    # Test with a profile that might get repetitive recommendations
    user_prefs = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.80,
        "likes_acoustic": False
    }
    
    print("\n" + "="*80)
    print("🎵 DIVERSITY & FAIRNESS LOGIC DEMONSTRATION")
    print("="*80)
    print("\nProfile: Happy Pop Enthusiast")
    print(f"  Genre: {user_prefs['genre']}, Mood: {user_prefs['mood']}, Energy: {user_prefs['energy']}")
    
    # Compare three modes
    modes = [
        ("baseline", "No Diversity Penalty (Original Algorithm)"),
        ("artist_diversity", "Artist Diversity Focus (Penalize Repeated Artists)"),
        ("balanced", "Balanced Diversity (Penalize Artists & Genres)")
    ]
    
    for mode_name, mode_desc in modes:
        print("\n" + "="*80)
        print(f"📊 MODE: {mode_desc}")
        print("="*80)
        
        recs = recommend_songs_with_diversity(user_prefs, songs, k=5, diversity_mode=mode_name)
        
        print("\nTop 5 Recommendations:")
        print("-"*80)
        
        for i, (song, score, explanation) in enumerate(recs, 1):
            print(f"\n{i}. {song['title']}")
            print(f"   Artist: {song['artist']}")
            print(f"   Genre: {song['genre']}")
            print(f"   Score: {score:.2f}/7.0")
            print(f"   Details:")
            
            # Handle both string and list explanations
            if isinstance(explanation, list):
                for line in explanation:
                    if line.strip():
                        print(f"     {line}")
            else:
                for line in explanation.split("\n"):
                    if line.strip():
                        print(f"     {line}")
        
        # Show artist/genre diversity
        artists = [rec[0]['artist'] for rec in recs]
        genres = [rec[0]['genre'] for rec in recs]
        unique_artists = len(set(artists))
        unique_genres = len(set(genres))
        
        print("\n" + "-"*80)
        print(f"Diversity Stats:")
        print(f"  • Unique Artists: {unique_artists}/5")
        print(f"  • Unique Genres: {unique_genres}/5")
        print(f"  • Most Common Artist: {max(set(artists), key=artists.count)} ({artists.count(max(set(artists), key=artists.count))} times)")


if __name__ == "__main__":
    main()
