"""
Claude AI Recommender
Uses Claude AI to analyze user's movie taste and generate personalized recommendations.
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
    """Recommender using Claude AI to generate personalized movie recommendations."""

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

        self.client = Anthropic(api_key=self.api_key)
        self.model = Config.CLAUDE_MODEL
        self.max_tokens = Config.CLAUDE_MAX_TOKENS
        self.temperature = Config.CLAUDE_TEMPERATURE

    def _format_movie_for_prompt(self, movie: Dict[str, Any]) -> str:
        """
        Format a single movie's data for inclusion in the Claude prompt.

        Args:
            movie: Enriched movie dictionary with TMDB data

        Returns:
            Formatted string representation of the movie
        """
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'Unknown')
        genres = ', '.join(movie.get('genres', []))
        directors = ', '.join(movie.get('directors', []))
        cast = ', '.join(movie.get('cast', [])[:3])  # Top 3 actors
        rating = movie.get('rating', 'N/A')
        overview = movie.get('overview', 'No overview available')[:200]  # Truncate long overviews
        keywords = ', '.join(movie.get('keywords', [])[:5])  # Top 5 keywords

        return f"""
Title: {title} ({year})
Genres: {genres}
Director: {directors}
Cast: {cast}
Rating: {rating}/10
Overview: {overview}
Keywords: {keywords}
""".strip()

    def _build_prompt(self, movies: List[Dict[str, Any]]) -> str:
        """
        Build the complete Claude prompt with user's watched movies.

        Args:
            movies: List of enriched movie dictionaries

        Returns:
            Complete prompt string
        """
        # Format all movies
        formatted_movies = "\n\n".join(
            f"{i}. {self._format_movie_for_prompt(movie)}"
            for i, movie in enumerate(movies, 1)
        )

        # Build the prompt
        prompt = f"""You are an expert film curator and analyst with deep knowledge of cinema across all genres, eras, and cultures. Analyze this user's watched movies and recommend 10 films they haven't seen yet.

USER'S WATCHED MOVIES ({len(movies)} total):

{formatted_movies}

ANALYSIS TASK:

1. Identify patterns in their taste:
   - What genres do they gravitate toward?
   - Favorite directors, actors, or filmmakers?
   - Preferred themes, storytelling styles, or tones?
   - Time periods and film movements they enjoy?
   - What do their ratings suggest about their preferences?

2. Generate 10 diverse recommendations following this strategy:
   - 3-4 similar movies they'll likely love (safe bets based on clear preferences)
   - 2-3 hidden gems (critically acclaimed but lesser-known films matching their taste)
   - 2-3 gap-fillers (expand horizons: same director but different genre, adjacent movements, thematic connections)

3. Ensure variety in your recommendations:
   - Mix of decades and eras
   - Different genres (while staying within their taste profile)
   - Balance between classics and modern films
   - Include international cinema if it matches their interests
   - Avoid recommending movies that are already in their watched list

CRITICAL REQUIREMENTS:
- Return EXACTLY 10 movie recommendations
- Each movie must have a release year
- Do NOT recommend any movies from the user's watched list above
- Focus on movies that genuinely match their demonstrated preferences

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "recommendations": [
    {{"title": "Movie Title", "year": 1999}},
    {{"title": "Another Movie", "year": 2015}},
    {{"title": "Third Movie", "year": 1987}},
    {{"title": "Fourth Movie", "year": 2020}},
    {{"title": "Fifth Movie", "year": 1954}},
    {{"title": "Sixth Movie", "year": 2008}},
    {{"title": "Seventh Movie", "year": 1973}},
    {{"title": "Eighth Movie", "year": 2018}},
    {{"title": "Ninth Movie", "year": 1995}},
    {{"title": "Tenth Movie", "year": 2012}}
  ]
}}

IMPORTANT: Provide ONLY the JSON output above, no additional commentary, explanation, or text. The response must be valid JSON that can be parsed directly."""

        return prompt

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Claude's response and extract movie recommendations.

        Args:
            response_text: Raw response from Claude

        Returns:
            List of movie dictionaries with 'title' and 'year'

        Raises:
            InvalidResponseError: If response cannot be parsed
        """
        try:
            # Try to parse as JSON directly
            data = json.loads(response_text)

            if 'recommendations' not in data:
                raise InvalidResponseError("Response missing 'recommendations' key")

            recommendations = data['recommendations']

            if not isinstance(recommendations, list):
                raise InvalidResponseError("'recommendations' must be a list")

            if len(recommendations) != Config.RECOMMENDATIONS_COUNT:
                print(f"Warning: Expected {Config.RECOMMENDATIONS_COUNT} recommendations, got {len(recommendations)}")

            # Validate each recommendation
            valid_recommendations = []
            for rec in recommendations:
                if not isinstance(rec, dict):
                    continue

                if 'title' not in rec or 'year' not in rec:
                    continue

                # Ensure year is an integer
                try:
                    year = int(rec['year'])
                except (ValueError, TypeError):
                    continue

                valid_recommendations.append({
                    'title': str(rec['title']),
                    'year': year
                })

            if not valid_recommendations:
                raise InvalidResponseError("No valid recommendations found in response")

            return valid_recommendations

        except json.JSONDecodeError as e:
            # Try to extract JSON from response if it contains other text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return self._parse_response(json_match.group())
                except json.JSONDecodeError:
                    pass

            raise InvalidResponseError(f"Failed to parse JSON response: {e}")

    def generate_recommendations(
        self,
        watched_movies: List[Dict[str, Any]],
        num_recommendations: int = None
    ) -> List[Dict[str, Any]]:
        """
        Generate movie recommendations based on watched movies.

        Args:
            watched_movies: List of enriched movie dictionaries with TMDB data
            num_recommendations: Number of recommendations (uses Config default if None)

        Returns:
            List of recommended movie dictionaries with 'title' and 'year'

        Raises:
            RecommenderError: If recommendation generation fails
        """
        if not watched_movies:
            raise RecommenderError("No watched movies provided")

        if len(watched_movies) < Config.MIN_MOVIES_REQUIRED:
            raise RecommenderError(
                f"Need at least {Config.MIN_MOVIES_REQUIRED} movies to generate recommendations, "
                f"got {len(watched_movies)}"
            )

        # Build the prompt
        prompt = self._build_prompt(watched_movies)

        print(f"\nGenerating recommendations using Claude AI...")
        print(f"Analyzing {len(watched_movies)} watched movies...")

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
            recommendations = self._parse_response(response_text)

            print(f"✓ Generated {len(recommendations)} recommendations")

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

    def generate_recommendations_with_details(
        self,
        watched_movies: List[Dict[str, Any]],
        tmdb_client
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations and enrich them with TMDB data.

        Args:
            watched_movies: List of enriched movie dictionaries
            tmdb_client: TMDBClient instance to fetch details

        Returns:
            List of enriched recommended movies
        """
        # Generate recommendations
        recommendations = self.generate_recommendations(watched_movies)

        # Enrich with TMDB data
        print("\nEnriching recommendations with TMDB data...")
        enriched = tmdb_client.enrich_movies(recommendations, show_progress=True)

        return enriched


def generate_recommendations(
    watched_movies: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to generate movie recommendations.

    Args:
        watched_movies: List of enriched movie dictionaries
        api_key: Optional Anthropic API key

    Returns:
        List of recommended movie dictionaries
    """
    recommender = MovieRecommender(api_key)
    return recommender.generate_recommendations(watched_movies)
