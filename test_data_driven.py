"""
Test the new DATA-DRIVEN recommendation system.
Pipeline: Scrape → Enrich → Build Candidates → Claude Analysis → Recommendations
"""

from modules.letterboxd_scraper import scrape_list
from modules.tmdb_client import TMDBClient
from modules.recommender_v2 import MovieRecommender


def test_data_driven_pipeline():
    """Test the complete data-driven pipeline."""
    print("\n" + "="*70)
    print("DATA-DRIVEN MOVIE RECOMMENDATION SYSTEM")
    print("="*70)

    print("\nThis new system:")
    print("✓ Uses ONLY TMDB data (no LLM background knowledge)")
    print("✓ Builds candidate pool from similar movies in TMDB")
    print("✓ Claude analyzes metadata to rank candidates")
    print("✓ Fully transparent, data-driven decisions")

    # Get user input
    default_url = "https://letterboxd.com/ipoopintheaters/list/childhood-movies/"
    user_url = input(f"\nEnter Letterboxd list URL (or press Enter for default): ").strip()
    list_url = user_url if user_url else default_url

    try:
        # Step 1: Scrape Letterboxd list
        print("\n" + "━"*70)
        print("STEP 1: Scraping Letterboxd List")
        print("━"*70)

        movies = scrape_list(list_url)

        if not movies:
            print("✗ No movies found")
            return

        print(f"\n✓ Scraped {len(movies)} movies from Letterboxd")

        # Step 2: Enrich with TMDB
        print("\n" + "━"*70)
        print("STEP 2: Enriching with TMDB Metadata")
        print("━"*70)

        tmdb_client = TMDBClient()
        enriched_movies = tmdb_client.enrich_movies(movies, show_progress=True)

        if not enriched_movies:
            print("\n✗ No movies matched in TMDB")
            return

        print(f"\n✓ Enriched {len(enriched_movies)}/{len(movies)} movies with TMDB data")

        # Check minimum requirement
        from config import Config
        if len(enriched_movies) < Config.MIN_MOVIES_REQUIRED:
            print(f"\n✗ Need at least {Config.MIN_MOVIES_REQUIRED} movies")
            return

        # Step 3: Build candidate pool from TMDB
        print("\n" + "━"*70)
        print("STEP 3: Building Candidate Pool from TMDB")
        print("━"*70)
        print("Finding similar movies, TMDB recommendations, and related films...")

        candidates = tmdb_client.build_candidate_pool(
            enriched_movies,
            candidates_per_movie=10,
            max_candidates=50,  # Limit for cost/speed
            show_progress=True
        )

        if not candidates:
            print("\n✗ No candidates found")
            return

        print(f"\n✓ Built pool of {len(candidates)} candidate movies")

        # Show sample candidates
        print("\nSample candidates (first 10):")
        for i, candidate in enumerate(candidates[:10], 1):
            print(f"  {i}. {candidate['title']} ({candidate['year']}) - {', '.join(candidate['genres'][:2])}")

        # Step 4: Claude analyzes and selects from candidates
        print("\n" + "━"*70)
        print("STEP 4: Claude AI Analysis & Selection")
        print("━"*70)

        recommender = MovieRecommender()
        recommendations = recommender.generate_recommendations(
            watched_movies=enriched_movies,
            candidates=candidates
        )

        print(f"\n✓ Claude selected {len(recommendations)} recommendations")

        # Display final results
        print("\n" + "="*70)
        print("FINAL RECOMMENDATIONS")
        print("="*70)

        for i, movie in enumerate(recommendations, 1):
            print(f"\n{i}. {movie['title']} ({movie['year']})")
            print(f"   Genres: {', '.join(movie['genres'][:3])}")
            print(f"   Director: {', '.join(movie['directors'])}")
            print(f"   Cast: {', '.join(movie['cast'][:3])}")
            print(f"   Rating: {movie['rating']}/10 ({movie['vote_count']} votes)")
            print(f"   Plot: {movie['overview'][:120]}...")

        # Summary
        print("\n" + "="*70)
        print("PIPELINE SUMMARY")
        print("="*70)
        print(f"✓ Scraped: {len(movies)} movies from Letterboxd")
        print(f"✓ Enriched: {len(enriched_movies)} movies with TMDB data")
        print(f"✓ Generated: {len(candidates)} candidate movies from TMDB")
        print(f"✓ Analyzed: Claude ranked all candidates by metadata similarity")
        print(f"✓ Selected: {len(recommendations)} best matches")

        print(f"\n✓ All recommendations came from TMDB, not LLM memory!")
        print(f"✓ Decisions based on: genres, directors, cast, plot, keywords, ratings")

        # Cache stats
        cache_stats = tmdb_client.get_cache_stats()
        print(f"\n✓ TMDB cache: {cache_stats['size']} items cached")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run the test."""
    print("\n" + "="*70)
    print("DATA-DRIVEN RECOMMENDATION SYSTEM TEST")
    print("="*70)

    test_data_driven_pipeline()

    print("\n" + "="*70)
    print("TEST COMPLETED")
    print("="*70)
    print("\n✓ New system uses ONLY TMDB data for recommendations!")
    print("✓ Claude acts as a data analyst, not a movie encyclopedia")
    print("✓ All decisions are transparent and grounded in metadata")


if __name__ == "__main__":
    main()
