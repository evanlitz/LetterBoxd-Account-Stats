"""
Letterboxd Movie Recommender - FastAPI Application
Main web application that orchestrates scraping, enrichment, and recommendations.
"""

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, AsyncGenerator, List, Dict, Any
import traceback
import json
import asyncio

from modules.letterboxd_scraper import scrape_list, InvalidURLError, ListNotFoundError
from modules.letterboxd_profile_scraper import (
    scrape_profile,
    get_profile_stats,
    InvalidUsernameError,
    ProfileNotFoundError
)
from modules.tmdb_client import TMDBClient, TMDBError
from modules.recommender_v2 import MovieRecommender, RecommenderError
from modules.profile_analyzer import ProfileAnalyzer
from modules.profile_comparator import ProfileComparator
from config import Config

# Initialize FastAPI app
app = FastAPI(
    title="Letterboxd Movie Recommender",
    description="AI-powered movie recommendations based on your Letterboxd lists",
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize clients (will be reused across requests)
tmdb_client = TMDBClient()


def generate_fresh_recommendations(
    profiles: List[Dict[str, Any]],
    comparator: ProfileComparator,
    tmdb_client: TMDBClient,
    max_recommendations: int = 15
) -> List[Dict[str, Any]]:
    """
    Generate fresh movie recommendations based on shared favorites.

    Args:
        profiles: List of user profiles
        comparator: ProfileComparator instance
        tmdb_client: TMDB client for fetching similar movies
        max_recommendations: Maximum number of recommendations to return

    Returns:
        List of recommended movies neither user has watched
    """
    # Get all watched movie titles by both users
    all_watched_titles = set()
    for profile in profiles:
        all_watched_titles.update(m['title'] for m in profile['movies'])

    # Get seed movies (shared favorites)
    movies1 = {m['title']: m for m in profiles[0]['movies']}
    movies2 = {m['title']: m for m in profiles[1]['movies']}
    shared_titles = set(movies1.keys()) & set(movies2.keys())

    seed_movies = comparator.get_seed_movies_for_recommendations(
        movies1, movies2, shared_titles
    )

    if not seed_movies:
        return []

    # Collect similar movies from TMDB
    similar_movies_map = {}  # tmdb_id -> movie data

    for seed in seed_movies:
        try:
            # Get similar movies from TMDB
            similar = tmdb_client.get_similar_movies(seed['tmdb_id'], max_results=10)

            for movie in similar:
                tmdb_id = movie['tmdb_id']
                title = movie['title']

                # Skip if already watched by either user
                if title in all_watched_titles:
                    continue

                # Add to map (or increment count if already seen from multiple seeds)
                if tmdb_id not in similar_movies_map:
                    similar_movies_map[tmdb_id] = {
                        'tmdb_id': tmdb_id,
                        'title': title,
                        'year': movie.get('year', ''),
                        'count': 1  # Number of seed movies this was similar to
                    }
                else:
                    similar_movies_map[tmdb_id]['count'] += 1

        except Exception as e:
            print(f"Error fetching similar movies for {seed['title']}: {e}")
            continue

    # Convert to list and sort by count (movies similar to multiple favorites rank higher)
    recommendations = list(similar_movies_map.values())
    recommendations.sort(key=lambda x: x['count'], reverse=True)

    # Enrich top recommendations with full TMDB data
    top_recs = recommendations[:max_recommendations]
    enriched_recs = []

    for rec in top_recs:
        try:
            # Get full movie details from TMDB
            details = tmdb_client.get_movie_details(rec['tmdb_id'])
            enriched_recs.append({
                'title': details.get('title', rec['title']),
                'year': details.get('release_date', '')[:4] if details.get('release_date') else rec['year'],
                'poster_path': details.get('poster_path'),
                'genres': details.get('genres', []),
                'overview': details.get('overview', ''),
                'vote_average': details.get('vote_average', 0),
                'similarity_score': rec['count']  # How many shared favorites this is similar to
            })
        except Exception as e:
            print(f"Error enriching recommendation {rec['title']}: {e}")
            # Add basic info even if enrichment fails
            enriched_recs.append({
                'title': rec['title'],
                'year': rec['year'],
                'poster_path': None,
                'genres': [],
                'overview': '',
                'vote_average': 0,
                'similarity_score': rec['count']
            })

    return enriched_recs


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Render the main landing page.
    """
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "title": "Letterboxd Tools"
        }
    )


@app.get("/list-recommendations", response_class=HTMLResponse)
async def list_recommendations_page(request: Request):
    """
    Render the list recommendations page with input form.
    """
    return templates.TemplateResponse(
        "list_recommendations.html",
        {
            "request": request,
            "title": "List Recommendations"
        }
    )


@app.post("/recommend", response_class=HTMLResponse)
async def recommend(
    request: Request,
    letterboxd_url: str = Form(...),
    user_preferences: Optional[str] = Form(""),
    max_candidates: Optional[int] = Form(50),
    min_rating: Optional[float] = Form(0.0)
):
    """
    Main recommendation endpoint.
    Orchestrates: Scrape → Enrich → Build Candidates → Analyze → Recommend
    """
    # Initialize variables for error handling
    scraped_movies = []
    enriched_movies = []
    candidates = []
    recommendations = []
    error_message = None
    step_completed = 0

    try:
        # ==========================================
        # STEP 1: Scrape Letterboxd List
        # ==========================================
        step_completed = 1
        print(f"\n{'='*70}")
        print(f"NEW RECOMMENDATION REQUEST")
        print(f"{'='*70}")
        print(f"URL: {letterboxd_url}")
        print(f"\nStep 1: Scraping Letterboxd list...")

        scraped_movies = scrape_list(letterboxd_url)

        if not scraped_movies:
            error_message = "No movies found in the Letterboxd list. The list might be empty."
            raise ValueError(error_message)

        print(f"✓ Scraped {len(scraped_movies)} movies")

        # ==========================================
        # STEP 2: Enrich with TMDB
        # ==========================================
        step_completed = 2
        print(f"\nStep 2: Enriching with TMDB data...")

        enriched_movies = tmdb_client.enrich_movies(scraped_movies, show_progress=True)

        if not enriched_movies:
            error_message = "Could not match any movies in TMDB. Please check the list and try again."
            raise ValueError(error_message)

        match_rate = (len(enriched_movies) / len(scraped_movies)) * 100
        print(f"✓ Enriched {len(enriched_movies)}/{len(scraped_movies)} movies ({match_rate:.1f}% match rate)")

        # Check minimum requirement
        if len(enriched_movies) < Config.MIN_MOVIES_REQUIRED:
            error_message = (
                f"Need at least {Config.MIN_MOVIES_REQUIRED} movies to generate recommendations. "
                f"Only found {len(enriched_movies)} matching movies in TMDB."
            )
            raise ValueError(error_message)

        # ==========================================
        # STEP 3: Build Candidate Pool
        # ==========================================
        step_completed = 3
        print(f"\nStep 3: Building candidate pool from TMDB...")

        if min_rating and min_rating > 0:
            print(f"Applying minimum rating filter: {min_rating}+")

        candidates = tmdb_client.build_candidate_pool(
            enriched_movies,
            candidates_per_movie=10,
            max_candidates=max_candidates,
            min_rating=min_rating if min_rating and min_rating > 0 else None,
            show_progress=True
        )

        if not candidates:
            error_message = "Could not find any candidate movies. Please try a different list."
            raise ValueError(error_message)

        print(f"✓ Built pool of {len(candidates)} candidates")

        # ==========================================
        # STEP 4: Generate Recommendations
        # ==========================================
        step_completed = 4
        print(f"\nStep 4: Analyzing with Claude AI...")

        if user_preferences and user_preferences.strip():
            print(f"User preferences: {user_preferences[:100]}...")

        recommender = MovieRecommender()
        recommendations = recommender.generate_recommendations(
            watched_movies=enriched_movies,
            candidates=candidates,
            user_preferences=user_preferences if user_preferences and user_preferences.strip() else None,
            min_rating=min_rating if min_rating and min_rating > 0 else None
        )

        if not recommendations:
            error_message = "Could not generate recommendations. Please try again."
            raise ValueError(error_message)

        print(f"✓ Generated {len(recommendations)} recommendations")

        # ==========================================
        # Success - Render Results
        # ==========================================
        print(f"\n{'='*70}")
        print(f"SUCCESS - Returning {len(recommendations)} recommendations")
        print(f"{'='*70}\n")

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "recommendations": recommendations,
                "stats": {
                    "scraped": len(scraped_movies),
                    "enriched": len(enriched_movies),
                    "match_rate": f"{match_rate:.1f}",
                    "candidates": len(candidates),
                    "final_count": len(recommendations)
                }
            }
        )

    except InvalidURLError as e:
        error_message = f"Invalid Letterboxd URL: {str(e)}"
        print(f"\n✗ Error: {error_message}")

    except ListNotFoundError as e:
        error_message = f"Could not access the Letterboxd list: {str(e)}"
        print(f"\n✗ Error: {error_message}")

    except TMDBError as e:
        error_message = f"TMDB API error: {str(e)}"
        print(f"\n✗ Error: {error_message}")

    except RecommenderError as e:
        error_message = f"Recommendation error: {str(e)}"
        print(f"\n✗ Error: {error_message}")

    except ValueError as e:
        # Custom errors we raised
        if not error_message:
            error_message = str(e)
        print(f"\n✗ Error: {error_message}")

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"\n✗ Error: {error_message}")
        traceback.print_exc()

    # ==========================================
    # Error - Render Error Page
    # ==========================================
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_message": error_message,
            "step_completed": step_completed,
            "stats": {
                "scraped": len(scraped_movies),
                "enriched": len(enriched_movies),
                "candidates": len(candidates),
            }
        }
    )


@app.post("/recommend-stream")
async def recommend_stream(
    letterboxd_url: str = Form(...),
    user_preferences: Optional[str] = Form(""),
    max_candidates: Optional[int] = Form(50),
    min_rating: Optional[float] = Form(0.0)
):
    """
    Streaming recommendation endpoint with real-time progress updates.
    Uses Server-Sent Events (SSE) to stream progress to the client.
    """

    async def generate_progress() -> AsyncGenerator[str, None]:
        """Generate SSE-formatted progress updates"""

        def send_event(event_type: str, data: dict):
            """Helper to format SSE messages"""
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # ==========================================
            # STEP 1: Scrape Letterboxd List
            # ==========================================
            yield send_event('progress', {
                'step': 1,
                'message': '🎬 Scraping Letterboxd list...',
                'detail': letterboxd_url
            })
            await asyncio.sleep(0.1)  # Allow event to be sent

            # Run scraper in thread pool (blocking I/O)
            loop = asyncio.get_event_loop()
            scraped_movies = await loop.run_in_executor(None, scrape_list, letterboxd_url)

            if not scraped_movies:
                yield send_event('error', {
                    'message': 'No movies found in the Letterboxd list.',
                    'step': 1
                })
                return

            yield send_event('progress', {
                'step': 1,
                'message': f'✓ Found {len(scraped_movies)} movies',
                'count': len(scraped_movies),
                'completed': True
            })
            await asyncio.sleep(0.1)

            # ==========================================
            # STEP 2: Enrich with TMDB
            # ==========================================
            yield send_event('progress', {
                'step': 2,
                'message': '🎞️ Enriching with TMDB data...',
                'total': len(scraped_movies)
            })
            await asyncio.sleep(0.1)

            # Enrich movies with progress updates
            enriched_movies = []
            for i, movie in enumerate(scraped_movies, 1):
                # Run in thread pool
                enriched = await loop.run_in_executor(
                    None,
                    tmdb_client.enrich_movie,
                    movie
                )

                if enriched:
                    enriched_movies.append(enriched)

                # Send progress every 5 movies or at the end
                if i % 5 == 0 or i == len(scraped_movies):
                    yield send_event('progress', {
                        'step': 2,
                        'message': f'Matched {len(enriched_movies)}/{i} movies...',
                        'current': len(enriched_movies),
                        'total': len(scraped_movies)
                    })
                    await asyncio.sleep(0.05)

            if not enriched_movies:
                yield send_event('error', {
                    'message': 'Could not match any movies in TMDB.',
                    'step': 2
                })
                return

            match_rate = (len(enriched_movies) / len(scraped_movies)) * 100
            yield send_event('progress', {
                'step': 2,
                'message': f'✓ Matched {len(enriched_movies)}/{len(scraped_movies)} movies ({match_rate:.1f}%)',
                'completed': True,
                'match_rate': match_rate
            })
            await asyncio.sleep(0.1)

            # Check minimum requirement
            if len(enriched_movies) < Config.MIN_MOVIES_REQUIRED:
                yield send_event('error', {
                    'message': f'Need at least {Config.MIN_MOVIES_REQUIRED} movies. Only found {len(enriched_movies)}.',
                    'step': 2
                })
                return

            # ==========================================
            # STEP 3: Build Candidate Pool
            # ==========================================
            yield send_event('progress', {
                'step': 3,
                'message': '🎯 Building candidate pool...',
                'target': max_candidates
            })
            await asyncio.sleep(0.1)

            # Build candidates
            candidates = await loop.run_in_executor(
                None,
                tmdb_client.build_candidate_pool,
                enriched_movies,
                10,  # candidates_per_movie
                max_candidates,
                min_rating if min_rating and min_rating > 0 else None,
                False  # show_progress
            )

            if not candidates:
                yield send_event('error', {
                    'message': 'Could not find any candidate movies.',
                    'step': 3
                })
                return

            yield send_event('progress', {
                'step': 3,
                'message': f'✓ Found {len(candidates)} candidate movies',
                'count': len(candidates),
                'completed': True
            })
            await asyncio.sleep(0.1)

            # ==========================================
            # STEP 4: AI Analysis
            # ==========================================
            yield send_event('progress', {
                'step': 4,
                'message': '🤖 Claude AI analyzing your taste...',
                'detail': 'This may take 15-30 seconds'
            })
            await asyncio.sleep(0.1)

            # Generate recommendations
            recommender = MovieRecommender()
            recommendations = await loop.run_in_executor(
                None,
                recommender.generate_recommendations,
                enriched_movies,
                candidates,
                user_preferences if user_preferences and user_preferences.strip() else None,
                min_rating if min_rating and min_rating > 0 else None
            )

            if not recommendations:
                yield send_event('error', {
                    'message': 'Could not generate recommendations.',
                    'step': 4
                })
                return

            yield send_event('progress', {
                'step': 4,
                'message': f'✓ Generated {len(recommendations)} recommendations!',
                'count': len(recommendations),
                'completed': True
            })
            await asyncio.sleep(0.1)

            # ==========================================
            # SUCCESS - Send final results
            # ==========================================
            yield send_event('complete', {
                'recommendations': recommendations,
                'stats': {
                    'scraped': len(scraped_movies),
                    'enriched': len(enriched_movies),
                    'match_rate': f"{match_rate:.1f}",
                    'candidates': len(candidates),
                    'final_count': len(recommendations)
                }
            })

        except InvalidURLError as e:
            yield send_event('error', {
                'message': f'Invalid Letterboxd URL: {str(e)}',
                'step': 1
            })
        except ListNotFoundError as e:
            yield send_event('error', {
                'message': f'Could not access the list: {str(e)}',
                'step': 1
            })
        except TMDBError as e:
            yield send_event('error', {
                'message': f'TMDB API error: {str(e)}',
                'step': 2
            })
        except RecommenderError as e:
            yield send_event('error', {
                'message': f'Recommendation error: {str(e)}',
                'step': 4
            })
        except Exception as e:
            yield send_event('error', {
                'message': f'Unexpected error: {str(e)}',
                'step': 0
            })
            traceback.print_exc()

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.post("/display-results", response_class=HTMLResponse)
async def display_results(
    request: Request,
    recommendations: str = Form(...),
    stats: str = Form(...)
):
    """
    Display results from streaming endpoint.
    Receives JSON data and renders the results template.
    """
    import json

    # Parse JSON data
    recommendations_data = json.loads(recommendations)
    stats_data = json.loads(stats)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "recommendations": recommendations_data,
            "stats": stats_data
        }
    )


@app.get("/profile-analysis", response_class=HTMLResponse)
async def profile_analysis_page(request: Request):
    """
    Render the profile analysis input page.
    Completely separate feature from list-based recommendations.
    """
    return templates.TemplateResponse(
        "profile_analysis.html",
        {
            "request": request,
            "title": "Profile Taste Analysis"
        }
    )


@app.post("/analyze-profile-stream")
async def analyze_profile_stream(
    username: str = Form(...),
    analysis_depth: str = Form("rated_only"),
    user_preferences: Optional[str] = Form("")
):
    """
    Streaming profile analysis endpoint with real-time progress updates.
    Uses Server-Sent Events (SSE) to stream progress to the client.
    """

    async def generate_progress() -> AsyncGenerator[str, None]:
        """Generate SSE-formatted progress updates"""

        def send_event(event_type: str, data: dict):
            """Helper to format SSE messages"""
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # ==========================================
            # STEP 1: Scrape Profile
            # ==========================================
            yield send_event('progress', {
                'step': 1,
                'message': f'🎬 Scraping profile for {username}...',
                'detail': 'Fetching your watch history from Letterboxd'
            })
            await asyncio.sleep(0.1)

            # Run scraper in thread pool (blocking I/O)
            loop = asyncio.get_event_loop()
            scraped_films = await loop.run_in_executor(None, scrape_profile, username, None)

            if not scraped_films:
                yield send_event('error', {
                    'message': 'No films found in your profile.',
                    'step': 1
                })
                return

            # Get basic stats
            profile_stats = get_profile_stats(scraped_films)

            yield send_event('progress', {
                'step': 1,
                'message': f'✓ Found {len(scraped_films)} films ({profile_stats["rated_films"]} rated)',
                'count': len(scraped_films),
                'completed': True
            })
            await asyncio.sleep(0.1)

            # Filter by analysis depth
            if analysis_depth == "rated_only":
                films_to_analyze = [f for f in scraped_films if f.get('rating') is not None]
            else:
                films_to_analyze = scraped_films

            if not films_to_analyze:
                yield send_event('error', {
                    'message': 'No rated films found to analyze.',
                    'step': 1
                })
                return

            # ==========================================
            # STEP 2: Enrich with TMDB
            # ==========================================
            yield send_event('progress', {
                'step': 2,
                'message': '🎞️ Enriching with TMDB data...',
                'total': len(films_to_analyze)
            })
            await asyncio.sleep(0.1)

            # Enrich movies with progress updates
            enriched_movies = []
            for i, film in enumerate(films_to_analyze, 1):
                # Prepare movie dict for TMDB enrichment
                movie_dict = {
                    'title': film['title'],
                    'year': film.get('year')
                }

                # Run in thread pool
                enriched = await loop.run_in_executor(
                    None,
                    tmdb_client.enrich_movie,
                    movie_dict
                )

                if enriched:
                    # Preserve original rating from Letterboxd
                    enriched['rating'] = film.get('rating')
                    enriched['rating_stars'] = film.get('rating_stars')
                    enriched['liked'] = film.get('liked', False)
                    enriched['reviewed'] = film.get('reviewed', False)
                    enriched_movies.append(enriched)

                # Send progress every 10 movies or at the end
                if i % 10 == 0 or i == len(films_to_analyze):
                    yield send_event('progress', {
                        'step': 2,
                        'message': f'Matched {len(enriched_movies)}/{i} films...',
                        'current': len(enriched_movies),
                        'total': len(films_to_analyze)
                    })
                    await asyncio.sleep(0.05)

            if not enriched_movies:
                yield send_event('error', {
                    'message': 'Could not match any films in TMDB.',
                    'step': 2
                })
                return

            match_rate = (len(enriched_movies) / len(films_to_analyze)) * 100
            yield send_event('progress', {
                'step': 2,
                'message': f'✓ Matched {len(enriched_movies)}/{len(films_to_analyze)} films ({match_rate:.1f}%)',
                'completed': True,
                'match_rate': match_rate
            })
            await asyncio.sleep(0.1)

            # ==========================================
            # STEP 3: Analyze Taste Patterns
            # ==========================================
            yield send_event('progress', {
                'step': 3,
                'message': '🧠 Analyzing your taste patterns...',
                'detail': 'Calculating genre preferences, favorite creators, and more'
            })
            await asyncio.sleep(0.1)

            # Run analyzer
            analyzer = ProfileAnalyzer(
                enriched_movies=enriched_movies,
                rated_only=(analysis_depth == "rated_only")
            )
            analysis = await loop.run_in_executor(
                None,
                analyzer.analyze
            )

            yield send_event('progress', {
                'step': 3,
                'message': f'✓ Analyzed {len(analysis["genres"])} genres and {len(analysis["directors"])} directors',
                'completed': True
            })
            await asyncio.sleep(0.1)

            # ==========================================
            # STEP 4: Build Candidates & Recommend
            # ==========================================
            yield send_event('progress', {
                'step': 4,
                'message': '🤖 Generating personalized recommendations...',
                'detail': 'Claude AI is analyzing your taste to find perfect matches'
            })
            await asyncio.sleep(0.1)

            # Build candidate pool
            candidates = await loop.run_in_executor(
                None,
                tmdb_client.build_candidate_pool,
                enriched_movies,
                10,  # candidates_per_movie
                50,  # max_candidates
                None,  # min_rating
                False  # show_progress
            )

            if not candidates:
                yield send_event('error', {
                    'message': 'Could not find any candidate movies.',
                    'step': 4
                })
                return

            # Generate recommendations using taste preferences
            recommender = MovieRecommender()

            # Build context about user preferences
            context_message = ""
            if user_preferences and user_preferences.strip():
                context_message = user_preferences.strip()

            recommendations = await loop.run_in_executor(
                None,
                recommender.generate_recommendations,
                enriched_movies,
                candidates,
                context_message if context_message else None,
                None  # min_rating
            )

            if not recommendations:
                yield send_event('error', {
                    'message': 'Could not generate recommendations.',
                    'step': 4
                })
                return

            yield send_event('progress', {
                'step': 4,
                'message': f'✓ Generated {len(recommendations)} personalized recommendations!',
                'count': len(recommendations),
                'completed': True
            })
            await asyncio.sleep(0.1)

            # ==========================================
            # SUCCESS - Send final results
            # ==========================================
            yield send_event('complete', {
                'username': username,
                'analysis': analysis,
                'recommendations': recommendations
            })

        except InvalidUsernameError as e:
            yield send_event('error', {
                'message': f'Invalid username: {str(e)}',
                'step': 1
            })
        except ProfileNotFoundError as e:
            yield send_event('error', {
                'message': f'Could not access profile: {str(e)}',
                'step': 1
            })
        except TMDBError as e:
            yield send_event('error', {
                'message': f'TMDB API error: {str(e)}',
                'step': 2
            })
        except RecommenderError as e:
            yield send_event('error', {
                'message': f'Recommendation error: {str(e)}',
                'step': 4
            })
        except Exception as e:
            yield send_event('error', {
                'message': f'Unexpected error: {str(e)}',
                'step': 0
            })
            traceback.print_exc()

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.post("/display-profile-results", response_class=HTMLResponse)
async def display_profile_results(
    request: Request,
    results_data: str = Form(...)
):
    """
    Display profile analysis results.
    Receives JSON data from streaming endpoint and renders the results template.
    """
    # Parse JSON data
    data = json.loads(results_data)

    return templates.TemplateResponse(
        "profile_results.html",
        {
            "request": request,
            "username": data.get('username', 'User'),
            "analysis": data.get('analysis', {}),
            "recommendations": data.get('recommendations', []),
            "enriched_movies": data.get('enriched_movies', [])
        }
    )


@app.get("/compare", response_class=HTMLResponse)
async def compare_profiles_page(request: Request):
    """
    Render the profile comparison input page.
    """
    return templates.TemplateResponse(
        "compare.html",
        {
            "request": request,
            "title": "Compare Profiles"
        }
    )


@app.get("/compare-profiles-stream")
async def compare_profiles_stream(
    request: Request,
    usernames: str = Query(...),
    comparison_type: str = Query("two_user")
):
    """
    Compare multiple Letterboxd profiles with streaming progress.
    """
    async def generate_progress() -> AsyncGenerator[str, None]:
        def send_event(event_type: str, data: dict) -> str:
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        try:
            # Parse usernames
            username_list = [u.strip() for u in usernames.split(',') if u.strip()]

            if len(username_list) < 2:
                yield send_event('error', {
                    'message': 'Please enter at least 2 usernames',
                    'step': 0
                })
                return

            if len(username_list) > 5:
                yield send_event('error', {
                    'message': 'Maximum 5 users can be compared at once',
                    'step': 0
                })
                return

            # Fetch and analyze each profile
            profiles = []
            loop = asyncio.get_event_loop()

            for i, username in enumerate(username_list):
                yield send_event('progress', {
                    'step': 1,
                    'message': f'Scraping {username}\'s profile ({i+1}/{len(username_list)})...',
                    'current': i + 1,
                    'total': len(username_list)
                })

                # Scrape profile
                scraped_movies = await loop.run_in_executor(
                    None,
                    scrape_profile,
                    username
                )

                # Enrich movies in batches with progress updates
                enriched_movies = []
                batch_size = 20
                total_movies = len(scraped_movies)

                for batch_start in range(0, total_movies, batch_size):
                    batch_end = min(batch_start + batch_size, total_movies)
                    batch = scraped_movies[batch_start:batch_end]

                    yield send_event('progress', {
                        'step': 2,
                        'message': f'Enriching {username}\'s films ({batch_end}/{total_movies})...',
                        'current': i + 1,
                        'total': len(username_list)
                    })

                    # Enrich this batch
                    batch_enriched = await loop.run_in_executor(
                        None,
                        tmdb_client.enrich_movies,
                        batch,
                        False  # show_progress
                    )
                    enriched_movies.extend(batch_enriched)

                # Analyze profile
                analyzer = ProfileAnalyzer(enriched_movies)
                analysis = await loop.run_in_executor(None, analyzer.analyze)

                profiles.append({
                    'username': username,
                    'movies': enriched_movies,
                    'analysis': analysis
                })

            # Perform comparison
            yield send_event('progress', {
                'step': 3,
                'message': 'Comparing profiles...'
            })

            comparator = ProfileComparator(profiles)

            if comparison_type == "two_user" and len(profiles) == 2:
                comparison_result = comparator.compare_two_users()
                result_type = 'two_user'

                # Generate fresh recommendations (movies neither has seen)
                yield send_event('progress', {
                    'step': 3,
                    'message': 'Finding fresh recommendations...'
                })

                fresh_recs = await loop.run_in_executor(
                    None,
                    generate_fresh_recommendations,
                    profiles,
                    comparator,
                    tmdb_client
                )
                comparison_result['fresh_recommendations'] = fresh_recs
            else:
                comparison_result = comparator.find_group_consensus()
                result_type = 'group'

            # Send complete event
            yield send_event('complete', {
                'result_type': result_type,
                'comparison': comparison_result,
                'usernames': username_list
            })

        except InvalidUsernameError as e:
            yield send_event('error', {
                'message': f'Invalid username: {str(e)}',
                'step': 1
            })
        except ProfileNotFoundError as e:
            yield send_event('error', {
                'message': f'Profile not found: {str(e)}',
                'step': 1
            })
        except Exception as e:
            yield send_event('error', {
                'message': f'Error: {str(e)}',
                'step': 0
            })
            traceback.print_exc()

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/display-comparison-results", response_class=HTMLResponse)
async def display_comparison_results(request: Request):
    """
    Display comparison results page.
    """
    return templates.TemplateResponse(
        "comparison_results.html",
        {
            "request": request,
            "title": "Profile Comparison Results"
        }
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "tmdb_configured": bool(Config.TMDB_API_KEY),
        "claude_configured": bool(Config.ANTHROPIC_API_KEY),
        "cache_size": tmdb_client.get_cache_stats()['size']
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print("LETTERBOXD MOVIE RECOMMENDER")
    print("="*70)
    print("\nStarting server...")
    print("Open your browser to: http://localhost:8000")
    print("\nPress CTRL+C to stop the server")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
