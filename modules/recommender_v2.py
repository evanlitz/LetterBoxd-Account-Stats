"""
Claude AI Recommender V2 - Data-Driven Approach
Uses TMDB candidate pool and Claude AI to analyze and rank movies.
"""

import json
from typing import List, Dict, Any, Optional

from anthropic import Anthropic

from config import Config


class RecommenderError(Exception):
    """Base exception for recommender errors."""
    pass


class ClaudeAPIError(RecommenderError):
    """Raised when Claude API returns an error."""
    pass


class InvalidResponseError(RecommenderError):
    """Raised when Claude returns an invalid response."""
    pass


class MovieRecommender:
    """Data-driven recommender using TMDB candidates and Claude AI for analysis."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the recommender.

        Args:
            api_key: Anthropic API key (if None, uses from Config)
        """
        self.api_key = api_key or Config.ANTHROPIC_API_KEY

        if not self.api_key:
            raise RecommenderError(
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY in .env file."
            )

        # Initialize client with timeout settings
        self.client = Anthropic(
            api_key=self.api_key,
            timeout=60.0,  # 60 second timeout for API calls
            max_retries=2
        )
        self.model = Config.CLAUDE_MODEL
        self.max_tokens = Config.CLAUDE_MAX_TOKENS * 2  # More tokens for analysis
        self.temperature = Config.CLAUDE_TEMPERATURE

    def _format_movie_compact(self, movie: Dict[str, Any], index: Optional[int] = None) -> str:
        """
        Format a movie compactly for the prompt.

        Args:
            movie: Enriched movie dictionary
            index: Optional index number

        Returns:
            Compact formatted string
        """
        title = movie.get('title', 'Unknown')
        year = movie.get('year', '?')

        # Handle both string and dict formats for genres, directors, cast, keywords
        genres_list = movie.get('genres', [])[:3]
        genres = ', '.join([g if isinstance(g, str) else g.get('name', '') for g in genres_list])

        directors_list = movie.get('directors', [])
        directors = ', '.join([d if isinstance(d, str) else d.get('name', '') for d in directors_list])

        cast_list = movie.get('cast', [])[:3]
        cast = ', '.join([c if isinstance(c, str) else c.get('name', '') for c in cast_list])

        rating = movie.get('rating', 'N/A')
        overview = movie.get('overview', '')[:150]

        keywords_list = movie.get('keywords', [])[:4]
        keywords = ', '.join([k if isinstance(k, str) else k.get('name', '') for k in keywords_list])

        prefix = f"[{index}] " if index is not None else ""

        return f"""{prefix}{title} ({year})
  Genres: {genres} | Director: {directors}
  Cast: {cast} | Rating: {rating}/10
  Plot: {overview}
  Keywords: {keywords}""".strip()

    def _build_data_driven_prompt(
        self,
        watched_movies: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        user_preferences: Optional[str] = None,
        min_rating: Optional[float] = None
    ) -> str:
        """
        Build prompt for data-driven candidate analysis.

        Args:
            watched_movies: User's watched movies with full TMDB data
            candidates: Candidate movies to analyze
            user_preferences: Optional user-provided context/preferences

        Returns:
            Complete prompt string
        """
        # Format watched movies
        watched_formatted = "\n\n".join(
            self._format_movie_compact(movie, i)
            for i, movie in enumerate(watched_movies, 1)
        )

        # Format candidates
        candidates_formatted = "\n\n".join(
            self._format_movie_compact(movie, i)
            for i, movie in enumerate(candidates, 1)
        )

        # Build user preferences section if provided
        user_pref_section = ""
        if user_preferences and user_preferences.strip():
            user_pref_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER'S SPECIFIC PREFERENCES & CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The user has provided the following preferences/context for their recommendations:

"{user_preferences.strip()}"

IMPORTANT: These preferences should be your PRIMARY consideration when selecting recommendations.
Prioritize candidates that match these specific preferences while still respecting their overall taste profile.
"""

        # Build quality boost section if rating filter is active
        quality_boost_section = ""
        if min_rating and min_rating >= 6.0:
            quality_boost_section = f"""

QUALITY BOOST ACTIVE:
The user has set a minimum rating filter of {min_rating}+. All candidates have already been filtered
to meet this threshold. When scoring candidates, apply a 5% quality boost to highly-rated films
(rating ≥ {min_rating}) to favor critically acclaimed movies in your final selections.
"""

        prompt = f"""You are a data analyst specializing in movie recommendations. Your task is to analyze the user's watched movies and select the 10 best recommendations from a curated candidate pool.

CRITICAL: You must ONLY recommend movies from the candidate pool below. Do NOT suggest movies outside this list.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER'S WATCHED MOVIES ({len(watched_movies)} total)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{watched_formatted}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANDIDATE POOL ({len(candidates)} movies to choose from)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{candidates_formatted}
{user_pref_section}{quality_boost_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYSIS TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Identify Patterns in User's Taste
- What genres appear most frequently?
- Which directors, actors, or filmmakers do they favor?
- What themes, tones, or storytelling styles are common?
- What do the plot overviews reveal about their preferences?
- What keywords appear repeatedly?
- What rating patterns exist? (Do they prefer highly-rated films?)
{"- PRIORITY: If user preferences were provided above, how do they align with or diverge from the watched movies?" if user_preferences and user_preferences.strip() else ""}

Step 2: Score Each Candidate
For each candidate movie, analyze:
- Genre overlap with watched movies
- Shared directors or actors
- Similar keywords and themes
- Plot/story similarity (compare overviews)
- Rating quality (avoid low-rated films)
- Diversity value (era, style, sub-genre variety)

Step 3: Select Top 10 Recommendations
Apply this strategy:
- 3-4 similar movies (strong genre/theme/director match)
- 2-3 hidden gems (high quality but lesser-known, matching taste)
- 2-3 gap-fillers (expand horizons: adjacent genres, same director different style)

Ensure variety:
- Mix of decades/eras
- Different sub-genres within their taste
- Balance between safe bets and discoveries

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT JSON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON in this exact format:

{{
  "recommendations": [
    {{
      "candidate_index": 5,
      "title": "Movie Title",
      "year": 2015,
      "reason": "Brief reason (genre match, director similarity, theme connection, etc.)"
    }},
    ... (repeat for 10 movies)
  ]
}}

CRITICAL RULES:
- Select EXACTLY 10 movies
- Use ONLY movies from the candidate pool above
- Include the candidate_index number (the [N] number from the candidate list)
- Provide a brief data-driven reason for each pick
- Output ONLY the JSON, no additional text

Begin analysis:"""

        return prompt

    def _parse_data_driven_response(
        self,
        response_text: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse Claude's response and extract selected candidates with explanations.

        Args:
            response_text: Raw response from Claude
            candidates: Original candidate pool

        Returns:
            List of selected movie dictionaries with 'recommendation_reason' added

        Raises:
            InvalidResponseError: If response cannot be parsed
        """
        try:
            # Try to parse JSON
            data = json.loads(response_text)

            if 'recommendations' not in data:
                raise InvalidResponseError("Response missing 'recommendations' key")

            recommendations_data = data['recommendations']

            if not isinstance(recommendations_data, list):
                raise InvalidResponseError("'recommendations' must be a list")

            # Extract selected movies
            selected_movies = []

            for rec in recommendations_data:
                if not isinstance(rec, dict):
                    continue

                # Get candidate index and reason
                candidate_idx = rec.get('candidate_index')
                reason = rec.get('reason', 'Selected based on your taste profile')

                if candidate_idx is None:
                    # Fallback: try to match by title
                    title = rec.get('title')
                    year = rec.get('year')

                    if title:
                        # Find in candidates
                        for candidate in candidates:
                            if candidate['title'] == title and candidate.get('year') == year:
                                # Add reason to the movie dict
                                movie_with_reason = candidate.copy()
                                movie_with_reason['recommendation_reason'] = reason
                                selected_movies.append(movie_with_reason)
                                break
                else:
                    # Use index (1-based to 0-based)
                    idx = int(candidate_idx) - 1

                    if 0 <= idx < len(candidates):
                        # Add reason to the movie dict
                        movie_with_reason = candidates[idx].copy()
                        movie_with_reason['recommendation_reason'] = reason
                        selected_movies.append(movie_with_reason)

            if not selected_movies:
                raise InvalidResponseError("No valid recommendations found in response")

            return selected_movies

        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                try:
                    return self._parse_data_driven_response(json_match.group(), candidates)
                except json.JSONDecodeError:
                    pass

            raise InvalidResponseError(f"Failed to parse JSON response: {e}")

    def generate_recommendations(
        self,
        watched_movies: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        user_preferences: Optional[str] = None,
        min_rating: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate movie recommendations by analyzing candidates.

        Args:
            watched_movies: List of enriched watched movies with TMDB data
            candidates: List of enriched candidate movies from TMDB
            user_preferences: Optional user-provided preferences/context
            min_rating: Optional minimum rating filter (for prompt context)

        Returns:
            List of selected recommended movies (subset of candidates)

        Raises:
            RecommenderError: If recommendation generation fails
        """
        if not watched_movies:
            raise RecommenderError("No watched movies provided")

        if len(watched_movies) < Config.MIN_MOVIES_REQUIRED:
            raise RecommenderError(
                f"Need at least {Config.MIN_MOVIES_REQUIRED} movies, got {len(watched_movies)}"
            )

        if not candidates:
            raise RecommenderError("No candidate movies provided")

        if len(candidates) < Config.RECOMMENDATIONS_COUNT:
            print(f"Warning: Only {len(candidates)} candidates available, may not get 10 recommendations")

        print(f"\n{'='*70}")
        print(f"DATA-DRIVEN RECOMMENDATION ANALYSIS")
        print(f"{'='*70}")
        print(f"Watched movies: {len(watched_movies)}")
        print(f"Candidate pool: {len(candidates)}")
        print(f"Analyzing with Claude AI...")

        # Build the prompt
        prompt = self._build_data_driven_prompt(watched_movies, candidates, user_preferences, min_rating)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response text
            response_text = response.content[0].text

            # Parse recommendations
            recommendations = self._parse_data_driven_response(response_text, candidates)

            print(f"✓ Selected {len(recommendations)} recommendations from candidate pool")

            return recommendations

        except Exception as e:
            if hasattr(e, 'status_code'):
                if e.status_code == 401:
                    raise ClaudeAPIError("Invalid Anthropic API key. Please check your .env file.")
                elif e.status_code == 429:
                    raise ClaudeAPIError("Rate limit exceeded. Please wait and try again.")
                else:
                    raise ClaudeAPIError(f"Claude API error (HTTP {e.status_code}): {str(e)}")
            else:
                raise ClaudeAPIError(f"Error calling Claude API: {str(e)}")


def generate_recommendations(
    watched_movies: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to generate movie recommendations.

    Args:
        watched_movies: List of enriched watched movies
        candidates: List of enriched candidate movies
        api_key: Optional Anthropic API key

    Returns:
        List of recommended movies
    """
    recommender = MovieRecommender(api_key)
    return recommender.generate_recommendations(watched_movies, candidates)
