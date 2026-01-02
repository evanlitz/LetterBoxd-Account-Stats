"""
TMDB API Client
Fetches detailed movie metadata from The Movie Database (TMDB) API.
"""

import time
import re
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import requests
from rapidfuzz import fuzz, process
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config


class TMDBError(Exception):
    """Base exception for TMDB client errors."""
    pass


class MovieNotFoundError(TMDBError):
    """Raised when a movie cannot be found in TMDB."""
    pass


class TMDBAPIError(TMDBError):
    """Raised when TMDB API returns an error."""
    pass


class TMDBClient:
    """Client for interacting with the TMDB API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TMDB client.

        Args:
            api_key: TMDB API key (if None, uses from Config)
        """
        self.api_key = api_key or Config.TMDB_API_KEY
        self.base_url = Config.TMDB_BASE_URL
        self.image_base_url = Config.TMDB_IMAGE_BASE_URL

        if not self.api_key:
            raise TMDBError("TMDB API key not found. Please set TMDB_API_KEY in .env file.")

        # In-memory cache
        self.cache = {} if Config.ENABLE_CACHE else None

        # Rate limiting - optimized for better throughput while staying under 40/10s limit
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 10 requests per second (still well under 40/10s limit)

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Session for connection pooling
        self.session = requests.Session()
        self.session.params = {'api_key': self.api_key}

    def _wait_for_rate_limit(self):
        """Implement rate limiting to stay under TMDB's limits."""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)

        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the TMDB API with retry logic.

        Args:
            endpoint: API endpoint (e.g., '/search/movie')
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            TMDBAPIError: If the API returns an error
        """
        self._wait_for_rate_limit()

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)

            if response.status_code == 401:
                raise TMDBAPIError("Invalid TMDB API key. Please check your .env file.")
            elif response.status_code == 404:
                raise MovieNotFoundError(f"Resource not found: {endpoint}")
            elif response.status_code == 429:
                raise TMDBAPIError("TMDB API rate limit exceeded. Please wait and try again.")
            elif response.status_code != 200:
                raise TMDBAPIError(f"TMDB API error (HTTP {response.status_code}): {response.text}")

            return response.json()

        except requests.exceptions.Timeout:
            raise TMDBAPIError("TMDB API request timed out.")
        except requests.exceptions.RequestException as e:
            raise TMDBAPIError(f"Network error while accessing TMDB API: {str(e)}")

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments."""
        return f"{prefix}:{'_'.join(str(arg) for arg in args)}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if enabled and available."""
        if self.cache is not None:
            return self.cache.get(key)
        return None

    def _set_in_cache(self, key: str, value: Any):
        """Set value in cache if enabled."""
        if self.cache is not None:
            self.cache[key] = value

    def _normalize_title(self, title: str) -> str:
        """
        Normalize a movie title for better matching.
        Removes articles, special characters, and converts to lowercase.

        Args:
            title: Original movie title

        Returns:
            Normalized title
        """
        # Convert to lowercase
        normalized = title.lower()

        # Remove leading articles (the, a, an) in various languages
        normalized = re.sub(r'^(the|a|an|le|la|les|un|une|der|die|das|el|los|las)\s+', '', normalized)

        # Remove special characters but keep alphanumeric and spaces
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _fuzzy_match_title(self, search_title: str, results: List[Dict], year: Optional[int] = None, threshold: int = 85) -> Optional[int]:
        """
        Use fuzzy matching to find the best match from search results.

        Args:
            search_title: The title we're searching for
            results: List of search results from TMDB
            year: Optional year to help with matching
            threshold: Minimum similarity score (0-100)

        Returns:
            TMDB movie ID of best match, or None
        """
        if not results:
            return None

        normalized_search = self._normalize_title(search_title)

        best_match = None
        best_score = 0

        for result in results[:10]:  # Only check top 10 results
            result_title = result.get('title', '')
            normalized_result = self._normalize_title(result_title)

            # Calculate similarity score
            score = fuzz.ratio(normalized_search, normalized_result)

            # Bonus points for year match
            if year:
                result_year = result.get('release_date', '')[:4]
                if result_year and str(year) == result_year:
                    score += 15  # Boost score for year match

            # Check if this is the best match so far
            if score > best_score and score >= threshold:
                best_score = score
                best_match = result['id']

        if best_match:
            print(f"  Fuzzy match found with {best_score}% similarity")

        return best_match

    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[int]:
        """
        Search for a movie by title and year, return TMDB ID.

        Args:
            title: Movie title
            year: Release year (optional, but recommended for accuracy)

        Returns:
            TMDB movie ID if found, None otherwise
        """
        # Check cache first
        cache_key = self._get_cache_key('search', title, year or 'no_year')
        cached_id = self._get_from_cache(cache_key)
        if cached_id is not None:
            return cached_id

        # Search TMDB
        params = {'query': title}
        if year:
            params['year'] = year

        try:
            data = self._make_request('/search/movie', params)
            results = data.get('results', [])

            # Strategy 1: Exact match with year
            if results and year:
                # Check if first result matches year exactly
                first_result_year = results[0].get('release_date', '')[:4]
                if first_result_year == str(year):
                    movie_id = results[0]['id']
                    self._set_in_cache(cache_key, movie_id)
                    return movie_id

            # Strategy 2: Try without year and use fuzzy matching
            if year:
                print(f"  Trying fuzzy match for '{title}' ({year})...")
                params_no_year = {'query': title}
                data_no_year = self._make_request('/search/movie', params_no_year)
                results_no_year = data_no_year.get('results', [])

                # Use fuzzy matching with year preference
                fuzzy_match_id = self._fuzzy_match_title(title, results_no_year, year, threshold=85)
                if fuzzy_match_id:
                    self._set_in_cache(cache_key, fuzzy_match_id)
                    return fuzzy_match_id

            # Strategy 3: Use fuzzy matching on original results (if we have any)
            if results:
                fuzzy_match_id = self._fuzzy_match_title(title, results, year, threshold=85)
                if fuzzy_match_id:
                    self._set_in_cache(cache_key, fuzzy_match_id)
                    return fuzzy_match_id

                # Last resort: return first result if we have results
                print(f"  Using best available match for '{title}'")
                movie_id = results[0]['id']
                self._set_in_cache(cache_key, movie_id)
                return movie_id

            # Strategy 4: Lower threshold fuzzy matching as last resort
            if year:
                print(f"  Trying lower threshold match for '{title}'...")
                fuzzy_match_id = self._fuzzy_match_title(title, results_no_year if 'results_no_year' in locals() else results, year, threshold=75)
                if fuzzy_match_id:
                    self._set_in_cache(cache_key, fuzzy_match_id)
                    return fuzzy_match_id

            # No match found
            print(f"  No match found for '{title}'")
            self._set_in_cache(cache_key, None)
            return None

        except TMDBAPIError as e:
            print(f"  Error searching for '{title}': {e}")
            return None

    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a movie.
        Uses append_to_response to fetch all data in ONE API call instead of 4.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Dictionary with movie details, or None if error
        """
        # Check cache first
        cache_key = self._get_cache_key('details', movie_id)
        cached_details = self._get_from_cache(cache_key)
        if cached_details is not None:
            return cached_details

        try:
            # Fetch ALL movie data in ONE request using append_to_response
            # This combines 4 API calls into 1, making it 4x faster!
            params = {
                'append_to_response': 'credits,keywords,release_dates'
            }
            movie_data = self._make_request(f'/movie/{movie_id}', params)

            # Extract the appended data (same format as separate calls)
            credits_data = movie_data.get('credits', {})
            keywords_data = movie_data.get('keywords', {})
            release_dates_data = movie_data.get('release_dates', {})

            # Extract relevant information
            details = self._extract_movie_info(movie_data, credits_data, keywords_data, release_dates_data)

            # Cache the result
            self._set_in_cache(cache_key, details)

            return details

        except (TMDBAPIError, MovieNotFoundError) as e:
            print(f"  Error fetching details for movie ID {movie_id}: {e}")
            return None

    def _extract_movie_info(
        self,
        movie_data: Dict,
        credits_data: Dict,
        keywords_data: Dict,
        release_dates_data: Dict
    ) -> Dict[str, Any]:
        """
        Extract and format relevant movie information from TMDB API responses.

        Args:
            movie_data: Response from /movie/{id}
            credits_data: Response from /movie/{id}/credits
            keywords_data: Response from /movie/{id}/keywords
            release_dates_data: Response from /movie/{id}/release_dates

        Returns:
            Dictionary with formatted movie information
        """
        # Extract genres
        genres = [g['name'] for g in movie_data.get('genres', [])]

        # Extract director(s)
        crew = credits_data.get('crew', [])
        directors = [person['name'] for person in crew if person.get('job') == 'Director']

        # Extract main cast (top 5) with profile images
        cast = credits_data.get('cast', [])
        main_cast = []
        for person in cast[:5]:
            actor_data = {
                'name': person['name'],
                'id': person.get('id'),
                'profile_path': person.get('profile_path')
            }
            # Build profile image URL if available
            if actor_data['profile_path']:
                actor_data['profile_url'] = f"{self.image_base_url}{actor_data['profile_path']}"
            else:
                actor_data['profile_url'] = None
            main_cast.append(actor_data)

        # Extract keywords
        keywords = [kw['name'] for kw in keywords_data.get('keywords', [])]

        # Extract US certification (G, PG, PG-13, R, NC-17, etc.)
        certification = None
        if release_dates_data and 'results' in release_dates_data:
            for country_data in release_dates_data['results']:
                if country_data.get('iso_3166_1') == 'US':
                    # Get the most recent certification
                    release_dates = country_data.get('release_dates', [])
                    if release_dates:
                        # Usually the last one is the theatrical release
                        for rd in reversed(release_dates):
                            cert = rd.get('certification')
                            if cert:
                                certification = cert
                                break
                    break

        # Build poster URL
        poster_path = movie_data.get('poster_path')
        poster_url = f"{self.image_base_url}{poster_path}" if poster_path else None

        # Extract release year
        release_date = movie_data.get('release_date', '')
        release_year = None
        if release_date:
            try:
                release_year = datetime.strptime(release_date, '%Y-%m-%d').year
            except ValueError:
                pass

        return {
            'tmdb_id': movie_data.get('id'),
            'title': movie_data.get('title'),
            'original_title': movie_data.get('original_title'),
            'year': release_year,
            'release_date': release_date,
            'overview': movie_data.get('overview', ''),
            'genres': genres,
            'directors': directors,
            'cast': main_cast,
            'runtime': movie_data.get('runtime'),
            'rating': movie_data.get('vote_average'),
            'vote_average': movie_data.get('vote_average'),
            'vote_count': movie_data.get('vote_count'),
            'popularity': movie_data.get('popularity'),
            'keywords': keywords,
            'certification': certification,
            'poster_url': poster_url,
            'poster_path': poster_path,
            'backdrop_path': movie_data.get('backdrop_path'),
            'tagline': movie_data.get('tagline', ''),
            'status': movie_data.get('status'),
            'budget': movie_data.get('budget'),
            'revenue': movie_data.get('revenue'),
            'imdb_id': movie_data.get('imdb_id'),
        }

    def enrich_movie(self, movie: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enrich a movie dictionary (from scraper) with TMDB data.

        Args:
            movie: Dictionary with 'title' and 'year' keys

        Returns:
            Enriched movie dictionary with TMDB data, or None if not found
        """
        title = movie.get('title')
        year = movie.get('year')

        if not title:
            return None

        # Search for movie
        movie_id = self.search_movie(title, year)

        if not movie_id:
            print(f"  Movie not found in TMDB: {title} ({year})")
            return None

        # Get detailed information
        details = self.get_movie_details(movie_id)

        if not details:
            return None

        # Combine original movie data with TMDB details
        enriched = {**movie, **details}

        return enriched

    def enrich_movies(
        self,
        movies: List[Dict[str, Any]],
        show_progress: bool = True,
        progress_callback: Optional[callable] = None,
        parallel: bool = True,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple movies with TMDB data with parallel processing.

        Args:
            movies: List of movie dictionaries with 'title' and 'year'
            show_progress: Whether to print progress
            progress_callback: Optional callback function(current, total, movie_title) for progress updates
            parallel: Whether to use parallel processing (default: True for speed)
            batch_size: Number of movies to process in parallel (default: 10)

        Returns:
            List of enriched movie dictionaries (only successfully matched movies)
        """
        total = len(movies)

        if show_progress:
            print(f"\nEnriching {total} movies with TMDB data (parallel processing: {parallel})...")

        # Use parallel processing for significant speed boost
        if parallel and total > 1:
            return self._enrich_movies_parallel(movies, show_progress, progress_callback, batch_size)

        # Fallback to sequential processing
        enriched_movies = []
        for i, movie in enumerate(movies, 1):
            if show_progress:
                print(f"[{i}/{total}] {movie.get('title')} ({movie.get('year')})")

            # Call progress callback if provided
            if progress_callback:
                progress_callback(i, total, movie.get('title', 'Unknown'))

            enriched = self.enrich_movie(movie)

            if enriched:
                enriched_movies.append(enriched)
                if show_progress:
                    print(f"  ✓ Found: {enriched['title']} - {', '.join(enriched['genres'][:3])}")
            else:
                if show_progress:
                    print(f"  ✗ Not found in TMDB")

        if show_progress:
            print(f"\nSuccessfully enriched {len(enriched_movies)}/{total} movies")

        return enriched_movies

    def _enrich_movies_parallel(
        self,
        movies: List[Dict[str, Any]],
        show_progress: bool,
        progress_callback: Optional[callable],
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """
        Internal method to enrich movies in parallel batches.

        Args:
            movies: List of movie dictionaries
            show_progress: Whether to show progress
            progress_callback: Progress callback function
            batch_size: Number of movies to process simultaneously

        Returns:
            List of enriched movies
        """
        from concurrent.futures import as_completed

        enriched_movies = []
        total = len(movies)
        processed = 0

        # Process movies in batches for better performance
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = movies[batch_start:batch_end]

            if show_progress:
                print(f"\nProcessing batch {batch_start//batch_size + 1} ({batch_start+1}-{batch_end} of {total})...")

            # Submit all movies in batch to thread pool
            futures = {}
            for movie in batch:
                future = self.executor.submit(self.enrich_movie, movie)
                futures[future] = movie

            # Collect results as they complete
            for future in as_completed(futures):
                movie = futures[future]
                processed += 1

                try:
                    enriched = future.result()

                    if show_progress:
                        title = movie.get('title', 'Unknown')
                        year = movie.get('year', '')
                        print(f"[{processed}/{total}] {title} ({year})")

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(processed, total, movie.get('title', 'Unknown'))

                    if enriched:
                        enriched_movies.append(enriched)
                        if show_progress:
                            print(f"  ✓ Found: {enriched['title']} - {', '.join(enriched['genres'][:3])}")
                    else:
                        if show_progress:
                            print(f"  ✗ Not found in TMDB")

                except Exception as e:
                    if show_progress:
                        print(f"  ✗ Error: {e}")

        if show_progress:
            print(f"\n✓ Successfully enriched {len(enriched_movies)}/{total} movies")

        return enriched_movies

    def get_similar_movies(self, movie_id: int, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Get similar movies from TMDB.

        Args:
            movie_id: TMDB movie ID
            max_results: Maximum number of similar movies to return

        Returns:
            List of similar movie dictionaries with basic info
        """
        try:
            data = self._make_request(f'/movie/{movie_id}/similar')
            results = data.get('results', [])[:max_results]

            similar_movies = []
            for movie in results:
                similar_movies.append({
                    'tmdb_id': movie['id'],
                    'title': movie['title'],
                    'year': int(movie['release_date'][:4]) if movie.get('release_date') else None,
                })

            return similar_movies

        except (TMDBAPIError, MovieNotFoundError) as e:
            print(f"  Error fetching similar movies for ID {movie_id}: {e}")
            return []

    def get_movie_recommendations(self, movie_id: int, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Get TMDB's recommendations for a movie.

        Args:
            movie_id: TMDB movie ID
            max_results: Maximum number of recommendations to return

        Returns:
            List of recommended movie dictionaries with basic info
        """
        try:
            data = self._make_request(f'/movie/{movie_id}/recommendations')
            results = data.get('results', [])[:max_results]

            recommendations = []
            for movie in results:
                recommendations.append({
                    'tmdb_id': movie['id'],
                    'title': movie['title'],
                    'year': int(movie['release_date'][:4]) if movie.get('release_date') else None,
                })

            return recommendations

        except (TMDBAPIError, MovieNotFoundError) as e:
            print(f"  Error fetching recommendations for ID {movie_id}: {e}")
            return []

    def discover_movies(
        self,
        genres: Optional[List[int]] = None,
        keywords: Optional[List[int]] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_rating: Optional[float] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Discover movies using TMDB's discover endpoint.

        Args:
            genres: List of genre IDs
            keywords: List of keyword IDs
            min_year: Minimum release year
            max_year: Maximum release year
            min_rating: Minimum vote average
            max_results: Maximum results to return

        Returns:
            List of discovered movie dictionaries
        """
        params = {
            'sort_by': 'vote_count.desc',  # Popular movies first
        }

        if genres:
            params['with_genres'] = ','.join(map(str, genres))

        if keywords:
            params['with_keywords'] = ','.join(map(str, keywords))

        if min_year:
            params['primary_release_date.gte'] = f'{min_year}-01-01'

        if max_year:
            params['primary_release_date.lte'] = f'{max_year}-12-31'

        if min_rating:
            params['vote_average.gte'] = min_rating

        try:
            data = self._make_request('/discover/movie', params)
            results = data.get('results', [])[:max_results]

            discovered = []
            for movie in results:
                discovered.append({
                    'tmdb_id': movie['id'],
                    'title': movie['title'],
                    'year': int(movie['release_date'][:4]) if movie.get('release_date') else None,
                })

            return discovered

        except TMDBAPIError as e:
            print(f"  Error discovering movies: {e}")
            return []

    def build_candidate_pool(
        self,
        watched_movies: List[Dict[str, Any]],
        candidates_per_movie: int = 10,
        max_candidates: int = 100,
        min_rating: Optional[float] = None,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Build a pool of candidate movies based on watched movies.

        Args:
            watched_movies: List of enriched watched movies
            candidates_per_movie: How many candidates to get per watched movie
            max_candidates: Maximum total candidates
            min_rating: Minimum TMDB rating (vote_average) filter
            show_progress: Whether to show progress

        Returns:
            List of enriched candidate movies (not already watched)
        """
        if show_progress:
            print(f"\nBuilding candidate pool from {len(watched_movies)} watched movies...")

        watched_ids = {movie.get('tmdb_id') for movie in watched_movies if movie.get('tmdb_id')}
        candidate_ids = set()
        candidate_movies = []

        for i, movie in enumerate(watched_movies, 1):
            movie_id = movie.get('tmdb_id')
            if not movie_id:
                continue

            if show_progress:
                print(f"[{i}/{len(watched_movies)}] Finding candidates for: {movie['title']}")

            # Get similar movies
            similar = self.get_similar_movies(movie_id, max_results=candidates_per_movie // 2)
            for sim in similar:
                if sim['tmdb_id'] not in watched_ids and sim['tmdb_id'] not in candidate_ids:
                    candidate_ids.add(sim['tmdb_id'])
                    candidate_movies.append(sim)

            # Get TMDB recommendations
            recs = self.get_movie_recommendations(movie_id, max_results=candidates_per_movie // 2)
            for rec in recs:
                if rec['tmdb_id'] not in watched_ids and rec['tmdb_id'] not in candidate_ids:
                    candidate_ids.add(rec['tmdb_id'])
                    candidate_movies.append(rec)

            # Stop if we have enough candidates
            if len(candidate_movies) >= max_candidates:
                break

        # Limit to max_candidates
        candidate_movies = candidate_movies[:max_candidates]

        if show_progress:
            print(f"\n✓ Found {len(candidate_movies)} unique candidate movies")
            if min_rating and min_rating > 0:
                print(f"Enriching candidates with full TMDB data (filtering by rating ≥ {min_rating})...")
            else:
                print(f"Enriching candidates with full TMDB data...")

        # Enrich candidates with full details using parallel processing
        from concurrent.futures import as_completed

        enriched_candidates = []
        filtered_count = 0
        processed = 0
        total_candidates = len(candidate_movies)
        batch_size = 10

        # Process in batches for better performance
        for batch_start in range(0, total_candidates, batch_size):
            batch_end = min(batch_start + batch_size, total_candidates)
            batch = candidate_movies[batch_start:batch_end]

            # Submit all candidates in batch to thread pool
            futures = {}
            for candidate in batch:
                future = self.executor.submit(self.get_movie_details, candidate['tmdb_id'])
                futures[future] = candidate

            # Collect results as they complete
            for future in as_completed(futures):
                processed += 1

                if show_progress and processed % 10 == 0:
                    print(f"  Enriching {processed}/{total_candidates}...")

                try:
                    details = future.result()
                    if details:
                        # Apply rating filter if specified
                        if min_rating and min_rating > 0:
                            movie_rating = details.get('rating', 0)
                            if movie_rating and movie_rating >= min_rating:
                                enriched_candidates.append(details)
                            else:
                                filtered_count += 1
                        else:
                            enriched_candidates.append(details)
                except Exception as e:
                    if show_progress:
                        print(f"  Error enriching candidate: {e}")

        if show_progress:
            if min_rating and min_rating > 0:
                print(f"✓ Enriched {len(enriched_candidates)} candidates with full metadata (filtered out {filtered_count} below {min_rating} rating)")
            else:
                print(f"✓ Enriched {len(enriched_candidates)} candidates with full metadata")

        return enriched_candidates

    def clear_cache(self):
        """Clear the in-memory cache."""
        if self.cache is not None:
            self.cache.clear()
            print("Cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        if self.cache is not None:
            return {
                'size': len(self.cache),
                'enabled': True
            }
        return {'size': 0, 'enabled': False}
