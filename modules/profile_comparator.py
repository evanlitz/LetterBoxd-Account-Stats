"""
Profile Comparator for Letterboxd users.
Compares multiple users' profiles to find compatibility, shared favorites, and recommendations.
"""

from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import statistics


class ProfileComparator:
    """Compare multiple Letterboxd user profiles."""

    def __init__(self, profiles: List[Dict[str, Any]]):
        """
        Initialize comparator with enriched profile data.

        Args:
            profiles: List of profile dictionaries, each containing:
                - username: str
                - movies: List of enriched movies
                - analysis: Profile analysis results
        """
        self.profiles = profiles
        self.usernames = [p['username'] for p in profiles]

    @staticmethod
    def _round_to_half_star(rating: float) -> float:
        """
        Round a rating to the nearest 0.5 (Letterboxd's rating system).

        Args:
            rating: Rating value (on 0-5 scale)

        Returns:
            Rating rounded to nearest 0.5
        """
        return round(rating * 2) / 2

    def compare_two_users(self, user1_idx: int = 0, user2_idx: int = 1) -> Dict[str, Any]:
        """
        Deep comparison of two users.

        Args:
            user1_idx: Index of first user
            user2_idx: Index of second user

        Returns:
            Dictionary with comparison results
        """
        if len(self.profiles) < 2:
            raise ValueError("Need at least 2 profiles to compare")

        user1 = self.profiles[user1_idx]
        user2 = self.profiles[user2_idx]

        # Get movie sets
        movies1 = {m['title']: m for m in user1['movies']}
        movies2 = {m['title']: m for m in user2['movies']}

        # Find shared and unique films
        shared_titles = set(movies1.keys()) & set(movies2.keys())
        unique_to_user1 = set(movies1.keys()) - set(movies2.keys())
        unique_to_user2 = set(movies2.keys()) - set(movies1.keys())

        # Calculate compatibility score
        compatibility = self._calculate_compatibility(movies1, movies2, shared_titles)

        # Find shared favorites (both rated highly)
        shared_favorites = self._find_shared_favorites(movies1, movies2, shared_titles)

        # Find disagreements (rated very differently)
        disagreements = self._find_disagreements(movies1, movies2, shared_titles)

        # Find shared dislikes (both rated poorly)
        shared_dislikes = self._find_shared_dislikes(movies1, movies2, shared_titles)

        # Compare preferences
        genre_similarity = self._compare_genres(user1, user2)
        director_similarity = self._compare_directors(user1, user2)

        # Recommendations
        recommendations = self._generate_recommendations(movies1, movies2, unique_to_user1, unique_to_user2)

        return {
            'user1': user1['username'],
            'user2': user2['username'],
            'compatibility_score': compatibility['score'],
            'compatibility_details': compatibility,
            'shared_films_count': len(shared_titles),
            'user1_unique_count': len(unique_to_user1),
            'user2_unique_count': len(unique_to_user2),
            'shared_favorites': shared_favorites,
            'shared_dislikes': shared_dislikes,
            'disagreements': disagreements,
            'genre_similarity': genre_similarity,
            'director_similarity': director_similarity,
            'recommendations_for_user1': recommendations['for_user1'],
            'recommendations_for_user2': recommendations['for_user2'],
            'fresh_recommendations': []  # Will be populated by app.py after comparison
        }

    def find_group_consensus(self) -> Dict[str, Any]:
        """
        Find consensus recommendations for a group of 3-5 users.

        Returns:
            Dictionary with group consensus data
        """
        if len(self.profiles) < 2:
            raise ValueError("Need at least 2 profiles for group analysis")

        # Find films watched by everyone
        all_movie_sets = [set(m['title'] for m in p['movies']) for p in self.profiles]
        watched_by_all = set.intersection(*all_movie_sets)

        # Find films watched by at least 50% of the group
        movie_watchers = defaultdict(list)
        for i, profile in enumerate(self.profiles):
            for movie in profile['movies']:
                movie_watchers[movie['title']].append({
                    'user_idx': i,
                    'username': profile['username'],
                    'rating': movie.get('rating'),
                    'movie_data': movie
                })

        majority_watched = {
            title: watchers
            for title, watchers in movie_watchers.items()
            if len(watchers) >= len(self.profiles) / 2
        }

        # Find safe bets (everyone who watched it liked it)
        safe_bets = self._find_safe_bets(majority_watched)

        # Find potential compromises (films not everyone has seen but highly rated)
        unwatched_recommendations = self._find_unwatched_gems(movie_watchers)

        # Group compatibility
        avg_compatibility = self._calculate_group_compatibility()

        # Pairwise compatibility matrix
        pairwise_matrix = self._calculate_pairwise_matrix()

        # Individual taste profiles
        individual_profiles = self._generate_individual_profiles(all_movie_sets, movie_watchers)

        return {
            'usernames': self.usernames,
            'user_count': len(self.profiles),
            'watched_by_all_count': len(watched_by_all),
            'majority_watched_count': len(majority_watched),
            'safe_bets': safe_bets,
            'unwatched_recommendations': unwatched_recommendations,
            'average_compatibility': avg_compatibility,
            'pairwise_compatibility': pairwise_matrix,
            'individual_profiles': individual_profiles
        }

    def _calculate_compatibility(
        self,
        movies1: Dict[str, Dict],
        movies2: Dict[str, Dict],
        shared_titles: Set[str]
    ) -> Dict[str, Any]:
        """Calculate compatibility score between two users."""
        if not shared_titles:
            return {
                'score': 0,
                'rated_together': 0,
                'correlation': 0,
                'average_difference': 0
            }

        # Get shared rated films
        shared_rated = []
        ratings1 = []
        ratings2 = []

        for title in shared_titles:
            r1 = movies1[title].get('rating')
            r2 = movies2[title].get('rating')
            if r1 is not None and r2 is not None:
                shared_rated.append(title)
                ratings1.append(r1)
                ratings2.append(r2)

        if not shared_rated:
            return {
                'score': 30,  # Base score for having shared films
                'rated_together': 0,
                'correlation': 0,
                'average_difference': 0
            }

        # Calculate correlation
        avg_diff = sum(abs(r1 - r2) for r1, r2 in zip(ratings1, ratings2)) / len(shared_rated)

        # Normalize to 0-100 scale
        # Perfect match (diff=0) = 100, max diff (diff=10) = 0
        rating_score = max(0, (10 - avg_diff) * 10)

        # Bonus for shared films
        shared_bonus = min(20, len(shared_titles) / 10)

        # Overall score
        compatibility_score = min(100, rating_score + shared_bonus)

        return {
            'score': round(compatibility_score, 1),
            'rated_together': len(shared_rated),
            'shared_films': len(shared_titles),
            'average_difference': round(avg_diff, 2)
        }

    def _find_shared_favorites(
        self,
        movies1: Dict[str, Dict],
        movies2: Dict[str, Dict],
        shared_titles: Set[str]
    ) -> List[Dict[str, Any]]:
        """Find films both users rated highly."""
        favorites = []

        for title in shared_titles:
            r1 = movies1[title].get('rating')
            r2 = movies2[title].get('rating')

            # Both rated >= 8/10 (4 stars)
            if r1 and r2 and r1 >= 8 and r2 >= 8:
                user1_stars = r1 / 2
                user2_stars = r2 / 2
                avg_stars = (user1_stars + user2_stars) / 2

                favorites.append({
                    'title': title,
                    'year': movies1[title].get('release_date', '')[:4] if movies1[title].get('release_date') else '',
                    'user1_rating': self._round_to_half_star(user1_stars),
                    'user2_rating': self._round_to_half_star(user2_stars),
                    'average_rating': self._round_to_half_star(avg_stars),
                    'poster_path': movies1[title].get('poster_path')
                })

        # Sort by average rating
        favorites.sort(key=lambda x: x['average_rating'], reverse=True)
        return favorites[:10]

    def _find_shared_dislikes(
        self,
        movies1: Dict[str, Dict],
        movies2: Dict[str, Dict],
        shared_titles: Set[str]
    ) -> List[Dict[str, Any]]:
        """Find films both users rated poorly."""
        dislikes = []

        for title in shared_titles:
            r1 = movies1[title].get('rating')
            r2 = movies2[title].get('rating')

            # Both rated <= 4/10 (2 stars or less)
            if r1 is not None and r2 is not None and r1 <= 4 and r2 <= 4:
                user1_stars = r1 / 2
                user2_stars = r2 / 2
                avg_stars = (user1_stars + user2_stars) / 2

                dislikes.append({
                    'title': title,
                    'year': movies1[title].get('release_date', '')[:4] if movies1[title].get('release_date') else '',
                    'user1_rating': self._round_to_half_star(user1_stars),
                    'user2_rating': self._round_to_half_star(user2_stars),
                    'average_rating': self._round_to_half_star(avg_stars),
                    'poster_path': movies1[title].get('poster_path')
                })

        # Sort by average rating (lowest first)
        dislikes.sort(key=lambda x: x['average_rating'])
        return dislikes[:10]

    def _find_disagreements(
        self,
        movies1: Dict[str, Dict],
        movies2: Dict[str, Dict],
        shared_titles: Set[str]
    ) -> List[Dict[str, Any]]:
        """Find films with biggest rating disagreements."""
        disagreements = []

        for title in shared_titles:
            r1 = movies1[title].get('rating')
            r2 = movies2[title].get('rating')

            if r1 and r2:
                user1_stars = r1 / 2
                user2_stars = r2 / 2
                diff = abs(user1_stars - user2_stars)

                # Significant disagreement: 2+ star difference
                if diff >= 2:
                    disagreements.append({
                        'title': title,
                        'year': movies1[title].get('release_date', '')[:4] if movies1[title].get('release_date') else '',
                        'user1_rating': self._round_to_half_star(user1_stars),
                        'user2_rating': self._round_to_half_star(user2_stars),
                        'difference': self._round_to_half_star(diff),
                        'poster_path': movies1[title].get('poster_path')
                    })

        # Sort by difference
        disagreements.sort(key=lambda x: x['difference'], reverse=True)
        return disagreements[:10]

    def _compare_genres(self, user1: Dict, user2: Dict) -> Dict[str, Any]:
        """Compare genre preferences."""
        genres1 = {g['name']: g['count'] for g in user1['analysis'].get('genres', [])[:10]}
        genres2 = {g['name']: g['count'] for g in user2['analysis'].get('genres', [])[:10]}

        shared_genres = set(genres1.keys()) & set(genres2.keys())

        return {
            'shared_count': len(shared_genres),
            'shared_genres': sorted(list(shared_genres))[:5]
        }

    def _compare_directors(self, user1: Dict, user2: Dict) -> Dict[str, Any]:
        """Compare director preferences."""
        dirs1 = {d['name']: d['count'] for d in user1['analysis'].get('directors', [])[:10]}
        dirs2 = {d['name']: d['count'] for d in user2['analysis'].get('directors', [])[:10]}

        shared_directors = set(dirs1.keys()) & set(dirs2.keys())

        return {
            'shared_count': len(shared_directors),
            'shared_directors': sorted(list(shared_directors))[:5]
        }

    def _generate_recommendations(
        self,
        movies1: Dict[str, Dict],
        movies2: Dict[str, Dict],
        unique_to_user1: Set[str],
        unique_to_user2: Set[str]
    ) -> Dict[str, List[Dict]]:
        """Generate cross-recommendations."""
        # Recommend user1's favorites to user2
        recs_for_user2 = []
        for title in unique_to_user1:
            movie = movies1[title]
            rating = movie.get('rating')
            if rating and rating >= 8:  # 4+ stars
                stars = rating / 2
                recs_for_user2.append({
                    'title': title,
                    'year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                    'rating': self._round_to_half_star(stars),
                    'poster_path': movie.get('poster_path')
                })

        # Recommend user2's favorites to user1
        recs_for_user1 = []
        for title in unique_to_user2:
            movie = movies2[title]
            rating = movie.get('rating')
            if rating and rating >= 8:
                stars = rating / 2
                recs_for_user1.append({
                    'title': title,
                    'year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                    'rating': self._round_to_half_star(stars),
                    'poster_path': movie.get('poster_path')
                })

        # Sort by rating
        recs_for_user1.sort(key=lambda x: x['rating'], reverse=True)
        recs_for_user2.sort(key=lambda x: x['rating'], reverse=True)

        return {
            'for_user1': recs_for_user1[:10],
            'for_user2': recs_for_user2[:10]
        }

    def get_seed_movies_for_recommendations(
        self,
        movies1: Dict[str, Dict],
        movies2: Dict[str, Dict],
        shared_titles: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Get highly-rated shared movies to use as seeds for recommendations.

        Returns:
            List of movies both users rated highly (with TMDB IDs)
        """
        seed_movies = []

        for title in shared_titles:
            r1 = movies1[title].get('rating')
            r2 = movies2[title].get('rating')
            tmdb_id = movies1[title].get('tmdb_id')

            # Both rated >= 8/10 (4 stars) and has TMDB ID
            if r1 and r2 and r1 >= 8 and r2 >= 8 and tmdb_id:
                seed_movies.append({
                    'title': title,
                    'tmdb_id': tmdb_id,
                    'average_rating': (r1 + r2) / 4
                })

        # Sort by average rating and return top 10
        seed_movies.sort(key=lambda x: x['average_rating'], reverse=True)
        return seed_movies[:10]

    def _find_safe_bets(self, majority_watched: Dict) -> List[Dict[str, Any]]:
        """Find films that everyone who watched them liked."""
        safe_bets = []

        for title, watchers in majority_watched.items():
            ratings = [w['rating'] for w in watchers if w['rating']]

            if not ratings or len(ratings) < 2:
                continue

            avg_rating = sum(ratings) / len(ratings)
            min_rating = min(ratings)

            # Safe bet: average rating >= 8 and no one rated below 6
            if avg_rating >= 8 and min_rating >= 6:
                avg_stars = avg_rating / 2
                min_stars = min_rating / 2

                safe_bets.append({
                    'title': title,
                    'year': watchers[0]['movie_data'].get('release_date', '')[:4] if watchers[0]['movie_data'].get('release_date') else '',
                    'watched_by': len(watchers),
                    'average_rating': self._round_to_half_star(avg_stars),
                    'lowest_rating': self._round_to_half_star(min_stars),
                    'poster_path': watchers[0]['movie_data'].get('poster_path')
                })

        safe_bets.sort(key=lambda x: x['average_rating'], reverse=True)
        return safe_bets[:10]

    def _find_unwatched_gems(self, movie_watchers: Dict) -> List[Dict[str, Any]]:
        """Find highly-rated films not everyone has seen."""
        unwatched_gems = []

        for title, watchers in movie_watchers.items():
            # Skip if everyone has seen it
            if len(watchers) == len(self.profiles):
                continue

            ratings = [w['rating'] for w in watchers if w['rating']]

            if not ratings:
                continue

            avg_rating = sum(ratings) / len(ratings)

            # High rating but not everyone has seen it
            if avg_rating >= 8 and len(watchers) >= 1:
                avg_stars = avg_rating / 2

                unwatched_gems.append({
                    'title': title,
                    'year': watchers[0]['movie_data'].get('release_date', '')[:4] if watchers[0]['movie_data'].get('release_date') else '',
                    'watched_by': len(watchers),
                    'watched_by_names': [w['username'] for w in watchers],
                    'average_rating': self._round_to_half_star(avg_stars),
                    'poster_path': watchers[0]['movie_data'].get('poster_path')
                })

        unwatched_gems.sort(key=lambda x: x['average_rating'], reverse=True)
        return unwatched_gems[:15]

    def _calculate_group_compatibility(self) -> float:
        """Calculate average compatibility across all pairs."""
        if len(self.profiles) < 2:
            return 0

        total_score = 0
        pair_count = 0

        for i in range(len(self.profiles)):
            for j in range(i + 1, len(self.profiles)):
                movies_i = {m['title']: m for m in self.profiles[i]['movies']}
                movies_j = {m['title']: m for m in self.profiles[j]['movies']}
                shared = set(movies_i.keys()) & set(movies_j.keys())

                compat = self._calculate_compatibility(movies_i, movies_j, shared)
                total_score += compat['score']
                pair_count += 1

        return round(total_score / pair_count, 1) if pair_count > 0 else 0

    def _calculate_pairwise_matrix(self) -> List[List[Dict[str, Any]]]:
        """
        Calculate compatibility matrix for all pairs of users.

        Returns:
            2D list where matrix[i][j] contains compatibility info between user i and j
        """
        n = len(self.profiles)
        matrix = []

        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    # Same user - no compatibility score
                    row.append({
                        'username': self.usernames[i],
                        'score': None,
                        'is_self': True
                    })
                else:
                    # Calculate compatibility between user i and user j
                    movies_i = {m['title']: m for m in self.profiles[i]['movies']}
                    movies_j = {m['title']: m for m in self.profiles[j]['movies']}
                    shared = set(movies_i.keys()) & set(movies_j.keys())

                    compat = self._calculate_compatibility(movies_i, movies_j, shared)
                    row.append({
                        'username': self.usernames[j],
                        'score': compat['score'],
                        'shared_count': len(shared),
                        'is_self': False
                    })
            matrix.append(row)

        return matrix

    def _generate_individual_profiles(
        self,
        all_movie_sets: List[Set[str]],
        movie_watchers: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """
        Generate individual taste profile for each user compared to the group.

        Args:
            all_movie_sets: List of movie title sets for each user
            movie_watchers: Dictionary mapping movie titles to watchers

        Returns:
            List of profile dictionaries for each user
        """
        profiles = []

        # Calculate group average rating
        all_ratings = []
        for profile in self.profiles:
            for movie in profile['movies']:
                if movie.get('rating'):
                    all_ratings.append(movie['rating'])

        group_avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 5.0

        # Calculate group genre preferences
        group_genre_counts = {}
        for profile in self.profiles:
            for genre_data in profile['analysis'].get('genres', []):
                genre = genre_data['name']
                count = genre_data['count']
                group_genre_counts[genre] = group_genre_counts.get(genre, 0) + count

        for i, profile in enumerate(self.profiles):
            user_ratings = [m.get('rating') for m in profile['movies'] if m.get('rating')]
            user_avg_rating = sum(user_ratings) / len(user_ratings) if user_ratings else 5.0

            # Rating tendency (harsh vs generous)
            rating_diff = user_avg_rating - group_avg_rating
            if rating_diff > 1:
                critic_type = "generous"
                critic_description = f"Rates {abs(rating_diff):.1f} points higher than group average"
            elif rating_diff < -1:
                critic_type = "harsh"
                critic_description = f"Rates {abs(rating_diff):.1f} points lower than group average"
            else:
                critic_type = "balanced"
                critic_description = "Rates similarly to the group"

            # Find unique movies (only this user has seen)
            user_movies = all_movie_sets[i]
            other_movies = set()
            for j, other_set in enumerate(all_movie_sets):
                if i != j:
                    other_movies.update(other_set)

            unique_movies = user_movies - other_movies
            unique_favorites = []

            for movie in profile['movies']:
                if movie['title'] in unique_movies and movie.get('rating', 0) >= 8:
                    unique_favorites.append({
                        'title': movie['title'],
                        'year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                        'rating': self._round_to_half_star(movie['rating'] / 2),
                        'poster_path': movie.get('poster_path')
                    })

            # Sort by rating and take top 5
            unique_favorites.sort(key=lambda x: x['rating'], reverse=True)
            unique_favorites = unique_favorites[:5]

            # Find distinctive genre preferences
            user_genres = {g['name']: g['count'] for g in profile['analysis'].get('genres', [])[:10]}
            distinctive_genres = []

            for genre, user_count in user_genres.items():
                # Calculate if this user prefers this genre more than the group
                group_total_for_genre = group_genre_counts.get(genre, 0)
                user_percentage = user_count / len(profile['movies']) if profile['movies'] else 0
                group_percentage = group_total_for_genre / sum(len(p['movies']) for p in self.profiles)

                if user_percentage > group_percentage * 1.3:  # 30% more than group
                    distinctive_genres.append({
                        'name': genre,
                        'preference': 'high'
                    })

            distinctive_genres = distinctive_genres[:3]

            # Compatibility with others
            compatibilities = []
            for j, other_profile in enumerate(self.profiles):
                if i != j:
                    movies_i = {m['title']: m for m in profile['movies']}
                    movies_j = {m['title']: m for m in other_profile['movies']}
                    shared = set(movies_i.keys()) & set(movies_j.keys())
                    compat = self._calculate_compatibility(movies_i, movies_j, shared)
                    compatibilities.append({
                        'username': other_profile['username'],
                        'score': compat['score']
                    })

            # Find most and least compatible
            if compatibilities:
                most_compatible = max(compatibilities, key=lambda x: x['score'])
                least_compatible = min(compatibilities, key=lambda x: x['score'])
            else:
                most_compatible = None
                least_compatible = None

            profiles.append({
                'username': profile['username'],
                'total_movies': len(profile['movies']),
                'average_rating': self._round_to_half_star(user_avg_rating / 2),
                'critic_type': critic_type,
                'critic_description': critic_description,
                'unique_favorites': unique_favorites,
                'distinctive_genres': distinctive_genres,
                'most_compatible': most_compatible,
                'least_compatible': least_compatible
            })

        return profiles
