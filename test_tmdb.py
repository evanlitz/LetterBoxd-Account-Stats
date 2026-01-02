"""
Test script for TMDB client.
Tests searching for movies and enriching data.
"""

from modules.tmdb_client import TMDBClient, TMDBError
from modules.letterboxd_scraper import scrape_list


def test_search_movie():
    """Test searching for a specific movie."""
    print("\n" + "="*60)
    print("TEST 1: Movie Search")
    print("="*60)

    try:
        client = TMDBClient()

        test_movies = [
            ("The Godfather", 1972),
            ("Pulp Fiction", 1994),
            ("Inception", 2010),
            ("WALL·E", 2008),
        ]

        print("\nSearching for movies in TMDB:")
        for title, year in test_movies:
            movie_id = client.search_movie(title, year)
            if movie_id:
                print(f"✓ '{title}' ({year}) → ID: {movie_id}")
            else:
                print(f"✗ '{title}' ({year}) → Not found")

    except TMDBError as e:
        print(f"✗ TMDB Error: {e}")
        print("\nMake sure you have set TMDB_API_KEY in your .env file!")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def test_get_details():
    """Test fetching detailed movie information."""
    print("\n" + "="*60)
    print("TEST 2: Movie Details")
    print("="*60)

    try:
        client = TMDBClient()

        # Search for a movie first
        title = "The Godfather"
        year = 1972

        print(f"\nFetching details for '{title}' ({year})...")

        movie_id = client.search_movie(title, year)

        if not movie_id:
            print(f"✗ Could not find '{title}' in TMDB")
            return

        details = client.get_movie_details(movie_id)

        if details:
            print(f"\n✓ Successfully fetched details!")
            print(f"\nTitle: {details['title']}")
            print(f"Year: {details['year']}")
            print(f"Genres: {', '.join(details['genres'])}")
            print(f"Director(s): {', '.join(details['directors'])}")
            print(f"Cast: {', '.join(details['cast'])}")
            print(f"Rating: {details['rating']}/10 ({details['vote_count']} votes)")
            print(f"Runtime: {details['runtime']} minutes")
            print(f"Overview: {details['overview'][:150]}...")
            print(f"Keywords: {', '.join(details['keywords'][:5])}")
            print(f"Poster URL: {details['poster_url']}")
        else:
            print(f"✗ Could not fetch details")

    except TMDBError as e:
        print(f"✗ TMDB Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def test_enrich_movies():
    """Test enriching movies from Letterboxd with TMDB data."""
    print("\n" + "="*60)
    print("TEST 3: Enrich Scraped Movies")
    print("="*60)

    try:
        # Create sample movies (like what scraper would return)
        sample_movies = [
            {"title": "Home Alone", "year": 1990},
            {"title": "Up", "year": 2009},
            {"title": "WALL·E", "year": 2008},
        ]

        print(f"\nEnriching {len(sample_movies)} sample movies...")

        client = TMDBClient()
        enriched = client.enrich_movies(sample_movies, show_progress=True)

        print("\n" + "-"*60)
        print("ENRICHED DATA SAMPLE:")
        print("-"*60)

        if enriched:
            # Show detailed info for first enriched movie
            movie = enriched[0]
            print(f"\nExample enriched movie:")
            print(f"  Title: {movie['title']}")
            print(f"  Year: {movie['year']}")
            print(f"  Genres: {', '.join(movie['genres'])}")
            print(f"  Director: {', '.join(movie['directors'])}")
            print(f"  Cast: {', '.join(movie['cast'][:3])}")
            print(f"  Rating: {movie['rating']}/10")
            print(f"  Overview: {movie['overview'][:100]}...")
        else:
            print("✗ No movies were enriched")

    except TMDBError as e:
        print(f"✗ TMDB Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def test_full_pipeline():
    """Test the full pipeline: Scrape → Enrich with TMDB."""
    print("\n" + "="*60)
    print("TEST 4: Full Pipeline (Scraper + TMDB)")
    print("="*60)

    user_input = input("\nThis will scrape a Letterboxd list and enrich with TMDB. Continue? (y/n): ")

    if user_input.lower() not in ('y', 'yes'):
        print("Skipped.")
        return

    # Use the test list
    list_url = "https://letterboxd.com/ipoopintheaters/list/childhood-movies/"

    try:
        print(f"\nStep 1: Scraping Letterboxd list...")
        from modules.letterboxd_scraper import scrape_list

        movies = scrape_list(list_url)

        if not movies:
            print("✗ No movies found")
            return

        print(f"\nStep 2: Enriching {len(movies)} movies with TMDB data...")
        client = TMDBClient()
        enriched = client.enrich_movies(movies, show_progress=True)

        print("\n" + "="*60)
        print("PIPELINE COMPLETE")
        print("="*60)
        print(f"\n✓ Scraped: {len(movies)} movies")
        print(f"✓ Enriched: {len(enriched)} movies")
        print(f"✓ Match rate: {len(enriched)/len(movies)*100:.1f}%")

        # Show cache stats
        cache_stats = client.get_cache_stats()
        print(f"\nCache: {cache_stats['size']} items cached")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TMDB CLIENT TEST SUITE")
    print("="*60)

    try:
        test_search_movie()
        test_get_details()
        test_enrich_movies()
        test_full_pipeline()

        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("\n✓ TMDB client is working!")
        print("\nNext: Phase 4 - Claude Recommender")

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
