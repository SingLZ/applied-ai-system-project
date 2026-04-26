"""
Experiment: Testing weight sensitivity

BASELINE WEIGHTS:
- w_genre = 3.0
- w_mood = 2.0
- w_energy = 1.5
- w_acoustic = 0.5

EXPERIMENTAL WEIGHTS (Mood-Focused):
- w_genre = 1.5  (HALVED - less genre dominance)
- w_mood = 3.5   (INCREASED - mood prioritized)
- w_energy = 1.5 (UNCHANGED)
- w_acoustic = 0.5 (UNCHANGED)

HYPOTHESIS: With reduced genre weight, different mood users within the same genre
might get more diverse recommendations. This tests whether genre is overweighting
the system.
"""

from .recommender import load_songs
import os
from typing import Dict, List, Tuple

def score_song_experimental(user_prefs: Dict, song: Dict) -> Tuple[float, str]:
    """
    Score a single song with EXPERIMENTAL weights (mood-focused).
    
    Experimental weights reduce genre importance and boost mood.
    """
    score = 0.0
    explanations = []
    
    # EXPERIMENTAL WEIGHTS
    w_genre = 1.5      # REDUCED from 3.0
    w_mood = 3.5       # INCREASED from 2.0
    w_energy = 1.5     # unchanged
    w_acoustic = 0.5   # unchanged
    
    # Genre match (reduced weight)
    if song['genre'].lower() == user_prefs['genre'].lower():
        genre_score = 1.0
        explanations.append(f"Genre match: {song['genre']} (+{w_genre})")
    else:
        genre_score = 0.5
        explanations.append(f"Genre mismatch: {song['genre']} (expected {user_prefs['genre']}) (+{w_genre * 0.5})")
    score += w_genre * genre_score
    
    # Mood match (increased weight)
    if song['mood'].lower() == user_prefs['mood'].lower():
        mood_score = 1.0
        explanations.append(f"Mood match: {song['mood']} (+{w_mood})")
    else:
        mood_score = 0.0
        explanations.append(f"Mood mismatch: {song['mood']} (expected {user_prefs['mood']}) (+0.0)")
    score += w_mood * mood_score
    
    # Energy similarity
    energy_similarity = 1.0 - abs(user_prefs['energy'] - song['energy'])
    energy_score = w_energy * energy_similarity
    explanations.append(f"Energy match: {song['energy']:.2f} (target {user_prefs['energy']:.2f}) (+{energy_score:.2f})")
    score += energy_score
    
    # Acoustic preference
    if user_prefs['likes_acoustic']:
        acoustic_score = w_acoustic * song['acousticness']
    else:
        acoustic_score = w_acoustic * (1.0 - song['acousticness'])
    
    pref_text = "acoustic" if user_prefs['likes_acoustic'] else "electronic"
    explanations.append(f"{pref_text.capitalize()} preference: {acoustic_score:.2f}")
    score += acoustic_score
    
    explanation = "\n".join(explanations)
    return score, explanation

def recommend_songs_experimental(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple]:
    """
    Recommend top k songs using EXPERIMENTAL weights.
    """
    scored_songs = []
    for song in songs:
        score, explanation = score_song_experimental(user_prefs, song)
        scored_songs.append((song, score, explanation))
    
    # Sort by score (highest first)
    scored_songs.sort(key=lambda x: x[1], reverse=True)
    
    return scored_songs[:k]

def main() -> None:
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "songs.csv")
    songs = load_songs(csv_path)
    
    if not songs:
        print("No songs loaded. Exiting.")
        return
    
    # Test with key profiles to see how weights change results
    test_profiles = {
        "Happy Pop Enthusiast": {
            "genre": "pop", 
            "mood": "happy", 
            "energy": 0.80,
            "likes_acoustic": False
        },
        "Chill Lofi Listener": {
            "genre": "lofi", 
            "mood": "chill", 
            "energy": 0.40,
            "likes_acoustic": True
        },
        "Workout Enthusiast": {
            "genre": "pop", 
            "mood": "intense", 
            "energy": 0.92,
            "likes_acoustic": False
        }
    }
    
    print("\n" + "="*70)
    print("🔬 WEIGHT SENSITIVITY EXPERIMENT")
    print("Testing: Mood-Focused Weights vs Baseline Genre-Focused")
    print("="*70)
    
    for profile_name, user_prefs in test_profiles.items():
        print("\n" + "="*70)
        print(f"📊 {profile_name}")
        print("="*70)
        
        # Get experimental recommendations
        recs_exp = recommend_songs_experimental(user_prefs, songs, k=5)
        
        print("\n🔬 EXPERIMENTAL WEIGHTS (Mood-Focused):")
        print("  w_genre=1.5, w_mood=3.5, w_energy=1.5, w_acoustic=0.5")
        print("-"*70)
        
        for i, (song, score, explanation) in enumerate(recs_exp, 1):
            print(f"\n{i}. {song['title']} - Score: {score:.2f}/7.0")
            for line in explanation.split("\n"):
                print(f"   • {line}")

if __name__ == "__main__":
    main()
