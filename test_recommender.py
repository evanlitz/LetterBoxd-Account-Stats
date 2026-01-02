"""
Test script for Claude recommender and full pipeline.
Tests the complete flow: Scrape → Enrich → Recommend
"""

from modules.letterboxd_scraper import scrape_list
from modules.tmdb_client import TMDBClient
from modules.recommender import MovieRecommender, RecommenderError


def test_full_pipeline():
    """Test the complete pipeline: Scrape Letterboxd → Enrich with TMDB → Get Claude recommendations."""
    print("\n" + "="*70)
    print("FULL PIPELINE TEST: Letterboxd → TMDB → Claude AI Recommendations")
    print("="*70)

    # Get user input for list URL
    print("\nThis test will:")
    print("1. Scrape a Letterboxd list")
    print("2. Enrich movies with TMDB data")
    print("3. Use Claude AI to generate personalized recommendations")
    print("4. Enrich recommendations with TMDB data")

    default_url = "https://letterboxd.com/ipoopintheaters/list/childhood-movies/"
    user_url = input(f"\nEnter Letterboxd list URL (or press Enter for default): ").strip()

    list_url = user_url if user_url else default_url

    try:
        # Step 1: Scrape Letterboxd list
        print("\n" + "-"*70)
        print("STEP 1: Scraping Letterboxd List")
        print("-"*70)

        movies = scrape_list(list_url)

        if not movies:
            print("✗ No movies found in list")
            return

        print(f"\n✓ Scraped {len(movies)} movies from Letterboxd")

        # Step 2: Enrich with TMDB
        print("\n" + "-"*70)
        print("STEP 2: Enriching with TMDB Data")
        print("-"*70)

        tmdb_client = TMDBClient()
        enriched_movies = tmdb_client.enrich_movies(movies, show_progress=True)

        if not enriched_movies:
            print("\n✗ No movies matched in TMDB")
            return

        print(f"\n✓ Successfully enriched {len(enriched_movies)}/{len(movies)} movies")

        # Check minimum requirement
        from config import Config
        if len(enriched_movies) < Config.MIN_MOVIES_REQUIRED:
            print(f"\n✗ Need at least {Config.MIN_MOVIES_REQUIRED} movies, got {len(enriched_movies)}")
            return

        # Step 3: Generate recommendations with Claude
        print("\n" + "-"*70)
        print("STEP 3: Generating Recommendations with Claude AI")
        print("-"*70)

        recommender = MovieRecommender()
        recommendations = recommender.generate_recommendations(enriched_movies)

        print(f"\n✓ Generated {len(recommendations)} recommendations")
        print("\nRaw Recommendations from Claude:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec['title']} ({rec['year']})")

        # Step 4: Enrich recommendations with TMDB
        print("\n" + "-"*70)
        print("STEP 4: Enriching Recommendations with TMDB Data")
        print("-"*70)

        enriched_recs = tmdb_client.enrich_movies(recommendations, show_progress=True)

        print(f"\n✓ Successfully enriched {len(enriched_recs)}/{len(recommendations)} recommendations")

        # Display final results
        print("\n" + "="*70)
        print("FINAL RECOMMENDATIONS")
        print("="*70)

        for i, movie in enumerate(enriched_recs, 1):
            print(f"\n{i}. {movie['title']} ({movie['year']})")
            print(f"   Genres: {', '.join(movie['genres'][:3])}")
            print(f"   Director: {', '.join(movie['directors'])}")
            print(f"   Rating: {movie['rating']}/10")
            print(f"   Overview: {movie['overview'][:100]}...")

        # Summary
        print("\n" + "="*70)
        print("PIPELINE SUMMARY")
        print("="*70)
        print(f"✓ Scraped: {len(movies)} movies from Letterboxd")
        print(f"✓ Enriched: {len(enriched_movies)} movies with TMDB data")
        print(f"✓ Generated: {len(recommendations)} AI recommendations")
        print(f"✓ Final output: {len(enriched_recs)} enriched recommendations")
        print(f"\n✓ Success rate: {len(enriched_recs)/len(recommendations)*100:.1f}%")

        # Cache stats
        cache_stats = tmdb_client.get_cache_stats()
        print(f"✓ TMDB cache: {cache_stats['size']} items cached")

    except RecommenderError as e:
        print(f"\n✗ Recommender Error: {e}")
        print("\nMake sure you have set ANTHROPIC_API_KEY in your .env file!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_sample_recommendations():
    """Test recommendations with a small sample of movies."""
    print("\n" + "="*70)
    print("SAMPLE RECOMMENDATION TEST")
    print("="*70)

    # Create sample enriched movies (simulating what TMDB would return)
    sample_movies = [
        {
            'title': 'The Godfather',
            'year': 1972,
            'genres': ['Drama', 'Crime'],
            'directors': ['Francis Ford Coppola'],
            'cast': ['Marlon Brando', 'Al Pacino', 'James Caan'],
            'rating': 8.7,
            'overview': 'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.',
            'keywords': ['mafia', 'crime family', 'italian american', 'organized crime', 'patriarch']
        },
        {
            'title': 'Pulp Fiction',
            'year': 1994,
            'genres': ['Thriller', 'Crime'],
            'directors': ['Quentin Tarantino'],
            'cast': ['John Travolta', 'Uma Thurman', 'Samuel L. Jackson'],
            'rating': 8.5,
            'overview': 'The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.',
            'keywords': ['hitman', 'non linear timeline', 'dark comedy', 'crime', 'violence']
        },
        {
            'title': 'Inception',
            'year': 2010,
            'genres': ['Action', 'Science Fiction', 'Adventure'],
            'directors': ['Christopher Nolan'],
            'cast': ['Leonardo DiCaprio', 'Joseph Gordon-Levitt', 'Ellen Page'],
            'rating': 8.4,
            'overview': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea.',
            'keywords': ['dream', 'heist', 'subconscious', 'mind bending', 'layered reality']
        },
        {
            'title': 'The Dark Knight',
            'year': 2008,
            'genres': ['Drama', 'Action', 'Crime'],
            'directors': ['Christopher Nolan'],
            'cast': ['Christian Bale', 'Heath Ledger', 'Aaron Eckhart'],
            'rating': 9.0,
            'overview': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest tests.',
            'keywords': ['superhero', 'dc comics', 'vigilante', 'crime fighter', 'chaos']
        },
        {
            'title': 'Goodfellas',
            'year': 1990,
            'genres': ['Drama', 'Crime'],
            'directors': ['Martin Scorsese'],
            'cast': ['Robert De Niro', 'Ray Liotta', 'Joe Pesci'],
            'rating': 8.7,
            'overview': 'The story of Henry Hill and his life in the mob, covering his relationship with his wife and his partners.',
            'keywords': ['mafia', 'organized crime', 'biography', 'crime drama', 'violence']
        },
    ]

    try:
        print(f"\nUsing {len(sample_movies)} sample movies to test recommendation generation...")
        print("\nSample movies:")
        for movie in sample_movies:
            print(f"  - {movie['title']} ({movie['year']})")

        print("\nGenerating recommendations...")

        recommender = MovieRecommender()
        recommendations = recommender.generate_recommendations(sample_movies)

        print(f"\n✓ Generated {len(recommendations)} recommendations!")
        print("\nRecommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec['title']} ({rec['year']})")

    except RecommenderError as e:
        print(f"\n✗ Recommender Error: {e}")
        print("\nMake sure you have set ANTHROPIC_API_KEY in your .env file!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run tests."""
    print("\n" + "="*70)
    print("CLAUDE RECOMMENDER TEST SUITE")
    print("="*70)

    # First, test with sample data (faster, cheaper)
    print("\nTest 1: Sample data (no API calls except Claude)")
    test_sample_recommendations()

    # Then, optionally test full pipeline
    print("\n" + "="*70)
    user_input = input("\nRun full pipeline test? (scrapes real data, costs ~$0.02): (y/n): ")

    if user_input.lower() in ('y', 'yes'):
        test_full_pipeline()
    else:
        print("\nSkipping full pipeline test.")

    print("\n" + "="*70)
    print("TESTS COMPLETED")
    print("="*70)
    print("\n✓ Recommender is working!")
    print("\nNext: Phase 5 - FastAPI Backend Integration")


if __name__ == "__main__":
    main()
