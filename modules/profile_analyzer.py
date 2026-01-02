"""
Profile taste analyzer for Letterboxd data.
Analyzes user's entire watch history to identify patterns and preferences.
"""

from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
import statistics
import json

from anthropic import Anthropic
from config import Config


class ProfileAnalyzer:
    """Analyzes a user's Letterboxd profile to extract taste preferences."""

    def __init__(self, enriched_movies: List[Dict[str, Any]], rated_only: bool = True):
        """
        Initialize the analyzer with enriched movie data.

        Args:
            enriched_movies: List of movies enriched with TMDB data
            rated_only: If True, only analyze rated films
        """
        self.enriched_movies = enriched_movies
        self.rated_only = rated_only

        # Initialize Claude AI client for profile generation
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        # Filter to rated only if requested
        if rated_only:
            self.movies = [m for m in enriched_movies if m.get('rating') is not None]
        else:
            self.movies = enriched_movies

    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete taste analysis.

        Returns:
            Dictionary containing all analysis results
        """
        # Generate basic analysis
        stats = self._calculate_stats()
        genres = self._analyze_genres()
        directors = self._analyze_directors()
        actors = self._analyze_actors()
        decades = self._analyze_decades()
        keywords = self._analyze_keywords()
        rating_patterns = self._analyze_rating_patterns()
        public_disagreement = self._analyze_public_disagreement()
        hidden_gems = self._find_hidden_gems()
        certifications = self._analyze_certifications()
        watch_time = self._calculate_watch_time()

        # Generate AI-powered cinematic profile
        ai_profile = self._generate_ai_profile(stats, genres, directors, actors, decades, rating_patterns)

        return {
            'stats': stats,
            'genres': genres,
            'directors': directors,
            'actors': actors,
            'decades': decades,
            'keywords': keywords,
            'rating_patterns': rating_patterns,
            'public_disagreement': public_disagreement,
            'hidden_gems': hidden_gems,
            'certifications': certifications,
            'watch_time': watch_time,
            'ai_profile': ai_profile,
            'taste_summary': self._generate_taste_summary()
        }

    def _calculate_stats(self) -> Dict[str, Any]:
        """Calculate basic statistics."""
        total_films = len(self.movies)
        rated_films = [m for m in self.movies if m.get('rating') is not None]

        if not rated_films:
            avg_rating = 0
            median_rating = 0
        else:
            ratings = [m['rating'] for m in rated_films]
            avg_rating = statistics.mean(ratings)
            median_rating = statistics.median(ratings)

        return {
            'total_films': total_films,
            'rated_films': len(rated_films),
            'average_rating': round(avg_rating, 2),
            'median_rating': round(median_rating, 2),
            'average_rating_stars': round(avg_rating / 2, 2) if avg_rating else 0,
        }

    def _analyze_genres(self) -> List[Dict[str, Any]]:
        """Analyze genre preferences."""
        genre_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0, 'rated_count': 0})

        for movie in self.movies:
            genres = movie.get('genres', [])
            rating = movie.get('rating')

            for genre in genres:
                # Handle both string genres and dict genres
                if isinstance(genre, str):
                    genre_name = genre
                elif isinstance(genre, dict):
                    genre_name = genre.get('name')
                else:
                    continue

                if genre_name:
                    genre_stats[genre_name]['count'] += 1
                    if rating is not None:
                        genre_stats[genre_name]['total_rating'] += rating
                        genre_stats[genre_name]['rated_count'] += 1

        # Calculate averages and sort
        genres = []
        for name, stats in genre_stats.items():
            avg_rating = (stats['total_rating'] / stats['rated_count']) if stats['rated_count'] > 0 else 0
            genres.append({
                'name': name,
                'count': stats['count'],
                'average_rating': round(avg_rating, 2),
                'average_rating_stars': round(avg_rating / 2, 2) if avg_rating else 0
            })

        # Sort by count descending
        return sorted(genres, key=lambda x: x['count'], reverse=True)

    def _analyze_directors(self) -> List[Dict[str, Any]]:
        """Analyze favorite directors."""
        director_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0, 'rated_count': 0, 'titles': []})

        for movie in self.movies:
            directors = movie.get('directors', [])
            rating = movie.get('rating')
            title = movie.get('title', 'Unknown')

            for director in directors:
                # Handle both string and dict
                if isinstance(director, str):
                    director_name = director
                elif isinstance(director, dict):
                    director_name = director.get('name')
                else:
                    continue

                if director_name:
                    director_stats[director_name]['count'] += 1
                    director_stats[director_name]['titles'].append(title)
                    if rating is not None:
                        director_stats[director_name]['total_rating'] += rating
                        director_stats[director_name]['rated_count'] += 1

        # Calculate averages and sort
        directors = []
        for name, stats in director_stats.items():
            avg_rating = (stats['total_rating'] / stats['rated_count']) if stats['rated_count'] > 0 else 0
            directors.append({
                'name': name,
                'count': stats['count'],
                'average_rating': round(avg_rating, 2),
                'average_rating_stars': round(avg_rating / 2, 2) if avg_rating else 0,
                'sample_titles': stats['titles'][:3]  # First 3 titles
            })

        # Sort by count descending, minimum 2 films
        directors = [d for d in directors if d['count'] >= 2]
        return sorted(directors, key=lambda x: x['count'], reverse=True)[:15]

    def _analyze_actors(self) -> List[Dict[str, Any]]:
        """Analyze favorite actors."""
        actor_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0, 'rated_count': 0, 'profile_url': None})

        for movie in self.movies:
            cast = movie.get('cast', [])[:5]  # Top 5 billed actors
            rating = movie.get('rating')

            for actor in cast:
                # Handle both string and dict
                if isinstance(actor, str):
                    actor_name = actor
                    profile_url = None
                elif isinstance(actor, dict):
                    actor_name = actor.get('name')
                    profile_url = actor.get('profile_url')
                else:
                    continue

                if actor_name:
                    actor_stats[actor_name]['count'] += 1
                    # Store profile URL if we have one and haven't stored it yet
                    if profile_url and not actor_stats[actor_name]['profile_url']:
                        actor_stats[actor_name]['profile_url'] = profile_url
                    if rating is not None:
                        actor_stats[actor_name]['total_rating'] += rating
                        actor_stats[actor_name]['rated_count'] += 1

        # Calculate averages and sort
        actors = []
        for name, stats in actor_stats.items():
            avg_rating = (stats['total_rating'] / stats['rated_count']) if stats['rated_count'] > 0 else 0
            actors.append({
                'name': name,
                'count': stats['count'],
                'average_rating': round(avg_rating, 2),
                'average_rating_stars': round(avg_rating / 2, 2) if avg_rating else 0,
                'profile_url': stats['profile_url']
            })

        # Sort by count descending, minimum 3 films
        actors = [a for a in actors if a['count'] >= 3]
        return sorted(actors, key=lambda x: x['count'], reverse=True)[:15]

    def _analyze_decades(self) -> List[Dict[str, Any]]:
        """Analyze decade preferences."""
        decade_stats = defaultdict(lambda: {'count': 0, 'total_rating': 0, 'rated_count': 0})

        for movie in self.movies:
            release_date = movie.get('release_date', '')
            rating = movie.get('rating')

            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                    decade = (year // 10) * 10
                    decade_label = f"{decade}s"

                    decade_stats[decade_label]['count'] += 1
                    decade_stats[decade_label]['decade_value'] = decade
                    if rating is not None:
                        decade_stats[decade_label]['total_rating'] += rating
                        decade_stats[decade_label]['rated_count'] += 1
                except ValueError:
                    pass

        # Calculate averages and sort
        decades = []
        for label, stats in decade_stats.items():
            avg_rating = (stats['total_rating'] / stats['rated_count']) if stats['rated_count'] > 0 else 0
            decades.append({
                'decade': label,
                'count': stats['count'],
                'average_rating': round(avg_rating, 2),
                'average_rating_stars': round(avg_rating / 2, 2) if avg_rating else 0
            })

        # Sort by decade chronologically
        return sorted(decades, key=lambda x: x['decade'])

    def _analyze_keywords(self) -> List[Dict[str, Any]]:
        """Analyze common keywords/themes."""
        keyword_counter = Counter()

        for movie in self.movies:
            keywords = movie.get('keywords', [])
            for keyword in keywords:
                # Handle both string and dict
                if isinstance(keyword, str):
                    keyword_name = keyword
                elif isinstance(keyword, dict):
                    keyword_name = keyword.get('name')
                else:
                    continue

                if keyword_name:
                    keyword_counter[keyword_name] += 1

        # Return top 20 keywords
        keywords = []
        for name, count in keyword_counter.most_common(20):
            keywords.append({
                'name': name,
                'count': count
            })

        return keywords

    def _analyze_rating_patterns(self) -> Dict[str, Any]:
        """Analyze rating distribution patterns."""
        rated_films = [m for m in self.movies if m.get('rating') is not None]

        if not rated_films:
            return {
                'distribution': {},
                'highest_rated': [],
                'lowest_rated': []
            }

        # Rating distribution (0.5 to 5.0 stars)
        distribution = defaultdict(int)
        for movie in rated_films:
            rating_stars = round(movie['rating'] / 2, 1)
            distribution[rating_stars] += 1

        # Convert to list format
        dist_list = [{'stars': stars, 'count': count} for stars, count in sorted(distribution.items())]

        # Highest rated films
        sorted_by_rating = sorted(rated_films, key=lambda x: x['rating'], reverse=True)
        highest_rated = [
            {
                'title': m['title'],
                'year': m.get('release_date', '')[:4] if m.get('release_date') else '',
                'rating': m['rating'],
                'rating_stars': round(m['rating'] / 2, 1)
            }
            for m in sorted_by_rating[:10]
        ]

        # Lowest rated films (only if rated 5.0 or below on 10-point scale)
        low_rated = [m for m in rated_films if m['rating'] <= 5.0]
        sorted_low = sorted(low_rated, key=lambda x: x['rating'])
        lowest_rated = [
            {
                'title': m['title'],
                'year': m.get('release_date', '')[:4] if m.get('release_date') else '',
                'rating': m['rating'],
                'rating_stars': round(m['rating'] / 2, 1)
            }
            for m in sorted_low[:10]
        ]

        return {
            'distribution': dist_list,
            'highest_rated': highest_rated,
            'lowest_rated': lowest_rated
        }

    def _analyze_public_disagreement(self) -> Dict[str, Any]:
        """Analyze movies where user rating differs most from TMDB rating."""
        # Filter out movies without ratings or with TMDB rating of 0 (likely wrong match)
        rated_films = [
            m for m in self.movies
            if m.get('rating') is not None
            and m.get('vote_average') is not None
            and m.get('vote_average') > 0
        ]

        if not rated_films:
            return {
                'overrated': [],
                'underrated': []
            }

        # Calculate disagreement (user rating - TMDB rating, both on 10-point scale)
        disagreements = []
        for movie in rated_films:
            user_rating = movie['rating']  # Already on 10-point scale
            tmdb_rating = movie['vote_average']  # Already on 10-point scale
            difference = user_rating - tmdb_rating

            disagreements.append({
                'title': movie['title'],
                'year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                'user_rating': round(user_rating / 2, 1),  # Convert to 5-star for display
                'tmdb_rating': round(tmdb_rating, 1),
                'user_rating_stars': round(user_rating / 2, 1),
                'difference': round(difference, 1),
                'poster_path': movie.get('poster_path'),
                'poster_url': movie.get('poster_url')
            })

        # Sort by difference
        disagreements.sort(key=lambda x: x['difference'])

        # Get top 5 underrated (user rated much lower than public)
        underrated = disagreements[:5]

        # Get top 5 overrated (user rated much higher than public)
        overrated = disagreements[-5:]
        overrated.reverse()  # Highest difference first

        return {
            'overrated': overrated,  # User rated higher than public
            'underrated': underrated  # User rated lower than public
        }

    def _find_hidden_gems(self) -> List[Dict[str, Any]]:
        """
        Find hidden gems - highly rated obscure films.

        Returns:
            List of hidden gem movies with metadata
        """
        # Filter for highly-rated movies with low popularity
        hidden_gems = []

        for movie in self.movies:
            user_rating = movie.get('rating')  # 10-point scale
            popularity = movie.get('popularity')
            vote_count = movie.get('vote_count', 0)

            # Skip if missing required data
            if user_rating is None or popularity is None:
                continue

            # Criteria for hidden gem:
            # - User rating >= 8/10 (4 stars)
            # - TMDB popularity < 25 (relatively obscure)
            # - Vote count < 1000 (not widely known)
            if user_rating >= 8 and popularity < 25 and vote_count < 1000:
                hidden_gems.append({
                    'title': movie['title'],
                    'year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                    'user_rating': round(user_rating / 2, 1),  # Convert to 5-star
                    'user_rating_stars': round(user_rating / 2, 1),
                    'popularity': round(popularity, 1),
                    'vote_count': vote_count,
                    'poster_path': movie.get('poster_path'),
                    'poster_url': movie.get('poster_url'),
                    'overview': movie.get('overview', '')[:150]
                })

        # Sort by user rating (highest first), then by popularity (lowest first)
        hidden_gems.sort(key=lambda x: (-x['user_rating'], x['popularity']))

        # Return top 10
        return hidden_gems[:10]

    def _analyze_certifications(self) -> Dict[str, Any]:
        """
        Analyze certification (content rating) distribution.

        Returns:
            Dictionary with certification breakdown and statistics
        """
        # Count certifications
        cert_counts = defaultdict(int)
        total_with_cert = 0

        for movie in self.movies:
            cert = movie.get('certification')
            if cert:
                cert_counts[cert] += 1
                total_with_cert += 1

        if total_with_cert == 0:
            return {
                'distribution': [],
                'total_certified': 0,
                'most_common': None
            }

        # Calculate percentages and sort by count
        distribution = []
        for cert, count in cert_counts.items():
            percentage = (count / total_with_cert) * 100
            distribution.append({
                'certification': cert,
                'count': count,
                'percentage': round(percentage, 1)
            })

        # Sort by count (descending)
        distribution.sort(key=lambda x: x['count'], reverse=True)

        return {
            'distribution': distribution,
            'total_certified': total_with_cert,
            'total_films': len(self.movies),
            'most_common': distribution[0]['certification'] if distribution else None
        }

    def _calculate_watch_time(self) -> Dict[str, Any]:
        """
        Calculate total viewing time and fun statistics.

        Returns:
            Dictionary with watch time statistics and comparisons
        """
        # Sum up all runtimes
        total_minutes = 0
        films_with_runtime = 0

        for movie in self.movies:
            runtime = movie.get('runtime')
            if runtime and runtime > 0:
                total_minutes += runtime
                films_with_runtime += 1

        if total_minutes == 0:
            return {
                'total_minutes': 0,
                'total_hours': 0,
                'total_days': 0,
                'films_counted': 0,
                'average_runtime': 0,
                'comparisons': []
            }

        total_hours = total_minutes / 60
        total_days = total_hours / 24

        # Calculate average runtime
        avg_runtime = total_minutes / films_with_runtime if films_with_runtime > 0 else 0

        # Fun comparisons
        comparisons = []

        # Flight comparisons
        if total_hours >= 1:
            nyc_to_la = total_hours / 5.5  # ~5.5 hour flight
            if nyc_to_la >= 1:
                comparisons.append({
                    'type': 'flight',
                    'description': f'Enough time to fly from NYC to LA {int(nyc_to_la)} times'
                })

        # Work week comparison
        work_weeks = total_hours / 40  # 40-hour work week
        if work_weeks >= 1:
            comparisons.append({
                'type': 'work',
                'description': f'Equivalent to {round(work_weeks, 1)} full-time work weeks'
            })

        # Marathon comparison
        if films_with_runtime >= 10:
            comparisons.append({
                'type': 'marathon',
                'description': f'That\'s {films_with_runtime} films back-to-back!'
            })

        # Days comparison
        if total_days >= 7:
            comparisons.append({
                'type': 'time',
                'description': f'Over {int(total_days)} days of pure movie watching'
            })
        elif total_days >= 1:
            comparisons.append({
                'type': 'time',
                'description': f'{round(total_days, 1)} days of continuous viewing'
            })

        return {
            'total_minutes': int(total_minutes),
            'total_hours': round(total_hours, 1),
            'total_days': round(total_days, 2),
            'films_counted': films_with_runtime,
            'average_runtime': round(avg_runtime, 0),
            'comparisons': comparisons
        }

    def _generate_taste_summary(self) -> str:
        """Generate natural language taste summary."""
        if not self.movies:
            return "No films found to analyze."

        stats = self._calculate_stats()
        genres = self._analyze_genres()
        directors = self._analyze_directors()
        decades = self._analyze_decades()

        summary_parts = []

        # Stats overview
        summary_parts.append(
            f"You've watched {stats['total_films']} films"
            + (f", rating {stats['rated_films']} of them" if self.rated_only and stats['rated_films'] != stats['total_films'] else "")
            + f" with an average rating of {stats['average_rating_stars']}★."
        )

        # Genre preferences
        if genres:
            top_genres = genres[:3]
            genre_names = [g['name'] for g in top_genres]
            if len(genre_names) == 1:
                genre_text = genre_names[0]
            elif len(genre_names) == 2:
                genre_text = f"{genre_names[0]} and {genre_names[1]}"
            else:
                genre_text = f"{', '.join(genre_names[:-1])}, and {genre_names[-1]}"

            summary_parts.append(
                f"Your taste gravitates strongly toward {genre_text}, "
                f"with {top_genres[0]['count']} {top_genres[0]['name']} films in your history."
            )

        # Director preferences
        if directors:
            top_director = directors[0]
            summary_parts.append(
                f"You're a fan of {top_director['name']}'s work ({top_director['count']} films watched"
                + (f", avg rating {top_director['average_rating_stars']}★" if top_director.get('average_rating_stars', 0) > 0 else "")
                + ")."
            )

        # Decade preferences
        if decades:
            top_decade = max(decades, key=lambda x: x['count'])
            summary_parts.append(
                f"The {top_decade['decade']} is your most-watched era with {top_decade['count']} films."
            )

        return " ".join(summary_parts)

    def _generate_ai_profile(
        self,
        stats: Dict[str, Any],
        genres: List[Dict[str, Any]],
        directors: List[Dict[str, Any]],
        actors: List[Dict[str, Any]],
        decades: List[Dict[str, Any]],
        rating_patterns: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Use Claude AI to generate a personalized cinematic profile with a catchy title.

        Args:
            stats: Basic statistics
            genres: Genre analysis
            directors: Director preferences
            actors: Actor preferences
            decades: Decade preferences
            rating_patterns: Rating distribution and patterns

        Returns:
            Dictionary with 'title' and 'description' keys
        """
        # Build data summary for Claude
        profile_data = {
            'total_films': stats.get('total_films', 0),
            'avg_rating': stats.get('avg_rating', 0),
            'top_genres': [g['name'] for g in genres[:5]] if genres else [],
            'top_directors': [d['name'] for d in directors[:3]] if directors else [],
            'top_actors': [a['name'] for a in actors[:3]] if actors else [],
            'favorite_decade': decades[0]['decade'] if decades else None,
            'rating_distribution': rating_patterns.get('distribution', []),
            'highest_rated': [f"{m['title']} ({m.get('year', 'N/A')})" for m in rating_patterns.get('highest_rated', [])[:3]]
        }

        prompt = f"""Based on this user's Letterboxd viewing history, create a personalized cinematic profile:

VIEWING DATA:
- Total films watched: {profile_data['total_films']}
- Average rating: {profile_data['avg_rating']}/10
- Top genres: {', '.join(profile_data['top_genres'])}
- Favorite directors: {', '.join(profile_data['top_directors'])}
- Favorite actors: {', '.join(profile_data['top_actors'])}
- Most-watched decade: {profile_data['favorite_decade']}
- Highest rated films: {', '.join(profile_data['highest_rated'])}

Generate a JSON response with:
1. "title": A catchy, creative 3-5 word title that captures their moviegoer personality (e.g., "Cerebral Indie Explorer", "Blockbuster Action Devotee", "Art House Cinephile", "Nostalgic Genre Hopper")
2. "description": A 2-3 paragraph engaging narrative (150-200 words) that:
   - Describes their unique taste profile in an engaging, personalized way
   - Highlights what makes their viewing habits distinctive
   - References specific preferences and patterns
   - Sounds like it was written by a film critic who knows them personally
   - Uses vivid, cinematic language

Output ONLY valid JSON with no additional text:
{{"title": "...", "description": "..."}}"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse the response
            response_text = response.content[0].text.strip()
            profile = json.loads(response_text)

            return {
                'title': profile.get('title', 'Film Enthusiast'),
                'description': profile.get('description', 'A passionate moviegoer with diverse tastes.')
            }

        except Exception as e:
            # Fallback if AI generation fails
            print(f"AI profile generation failed: {e}")
            return {
                'title': 'Film Enthusiast',
                'description': f"A dedicated moviegoer who has watched {profile_data['total_films']} films, with a particular affinity for {', '.join(profile_data['top_genres'][:3])}."
            }
