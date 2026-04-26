# Model Card: Explainable Music Recommendation Reliability System

## 1. Model Name

**VibeFinder Reliability 2.0**

## 2. Intended Use

This system recommends songs from a small CSV catalog using a transparent content-based scoring algorithm. It is intended for classroom and portfolio demonstration of applied AI design, explainability, guardrails, and reliability testing.

It is not intended for production music streaming, psychological profiling, or high-stakes decision-making.

## 3. Original Project

The original Module 3 Music Recommender Simulation loaded a catalog of songs, scored them against a user taste profile, and returned ranked recommendations with short explanations. The extension adds guardrails, confidence scoring, audit logging, diversity warnings, and a reliability evaluation layer integrated into the main application flow.

## 4. How It Works

The model compares a user profile against song attributes.

User profile fields:

- preferred genre
- preferred mood
- target energy from `0.0` to `1.0`
- acoustic preference as a boolean

Song fields:

- genre
- mood
- energy
- tempo
- valence
- danceability
- acousticness

Scoring formula:

```text
Final Score = (3.0 × genre_match)
            + (2.0 × mood_match)
            + (1.5 × energy_similarity)
            + (0.5 × acoustic_preference)
```

The maximum score is `7.0`. Confidence is normalized as:

```text
confidence = score / 7.0
```

## 5. Reliability Layer

The advanced AI feature is an integrated reliability system.

It includes:

- input validation guardrails
- confidence scores per recommendation
- run-level average and minimum confidence
- diversity warnings for repeated artists or genres
- low-confidence warnings
- JSONL audit logging
- observable agent workflow trace
- multi-profile reliability evaluation
- bonus evaluation harness with pass/fail reporting

This is part of the main recommender behavior, not a standalone script.

## 6. Data

The dataset is `data/songs.csv`, a curated catalog of 20 songs. The catalog contains multiple genres and moods, including pop, lofi, rock, ambient, jazz, electronic, acoustic, metal, country, blues, reggae, classical, and folk.

The dataset is intentionally small and explainable. This helps with transparency but limits recommendation quality for underrepresented genres.

## 7. Strengths

- Transparent scoring logic.
- Human-readable explanations for every recommendation.
- Confidence scoring exposes uncertainty.
- Guardrails prevent invalid input from producing misleading results.
- Audit logs make system behavior inspectable after the fact.
- Reliability testing shows where the recommender is strong or weak.

## 8. Limitations and Biases

1. **Small catalog limitation:** Some genres have only one matching song, which reduces confidence for niche profiles.
2. **Genre bias:** Genre receives the largest weight, so the system may reinforce existing preferences.
3. **Exact mood matching:** Similar moods such as `chill` and `relaxed` do not receive partial credit.
4. **No user behavior learning:** The system does not learn from likes, skips, repeat plays, or listening history.
5. **No semantic understanding:** It does not analyze lyrics, language, artist context, or cultural meaning.
6. **Binary acoustic preference:** Acoustic preference is simplified into true/false, even though real taste is more continuous.

## 9. Evaluation

The project includes automated tests and a multi-profile CLI evaluation.

Automated tests cover:

- sorted recommendation output
- non-empty explanations
- confidence score range checks
- invalid energy rejection
- invalid `k` rejection
- empty catalog behavior
- observable agent trace steps
- empty-catalog trace warnings

The main CLI evaluates 8 user profiles and prints an overall reliability report. The bonus `scripts/run_evaluation.py` harness runs valid profiles, invalid guardrail inputs, and empty-catalog behavior, then prints a pass/fail summary.

Latest observed reliability result:

```text
Profiles evaluated: 8
Valid profiles passed guardrails: 8
Average confidence across profiles: ~0.72
Main weakness: low confidence for profiles where the 20-song catalog lacks strong matches
```

## 10. Misuse Risk and Prevention

Potential misuse:

- Presenting recommendations as if they objectively know a user's taste.
- Creating filter bubbles by repeatedly recommending the same genre or artist.
- Hiding uncertainty from users.

Prevention methods in this project:

- confidence scores
- explanations
- diversity warnings
- audit logs
- explicit limitations in documentation
- no claims that the system understands a user's full identity or personality

## 11. Future Work

- Add mood families so related moods receive partial credit.
- Add a larger and more balanced catalog.
- Add user feedback from likes/skips.
- Add semantic tags for lyrics or themes.
- Replace exact genre matching with embeddings or similarity scores.
- Add a configurable diversity penalty directly into the main ranking function.
- Add optional RAG-style retrieval from listening notes or genre documentation.

## 12. Reflection

The project showed that simple AI systems can appear reliable when they are only tested on easy examples. Adding confidence scoring and guardrails made weaknesses more visible. The system performs well for clear profiles such as `lofi + chill`, but struggles when the catalog has sparse coverage.

AI collaboration was useful for identifying reliability features such as confidence scoring, guardrails, and audit logging. A flawed AI suggestion was to add RAG or fine-tuning, which would have made the project more complicated without matching the actual need. The better final design was to make the existing recommender more measurable and trustworthy.
