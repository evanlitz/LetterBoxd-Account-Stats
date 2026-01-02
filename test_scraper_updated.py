"""
Updated test script for Letterboxd scraper with real data.
Tests both local HTML file and live URLs.
"""

from bs4 import BeautifulSoup
from modules.letterboxd_scraper import LetterboxdScraper, scrape_list, InvalidURLError, ListNotFoundError


def test_local_html():
    """Test parsing the local HTML file."""
    print("\n" + "="*60)
    print("TEST 1: Local HTML File Parsing")
    print("="*60)

    try:
        # Read the local HTML file
        with open('samplelistsiteinfo.html', 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml')

        # Create scraper and extract movies
        scraper = LetterboxdScraper()
        movies = scraper.extract_movies_from_page(soup)

        if movies:
            print(f"\n✓ Successfully extracted {len(movies)} movies from HTML file!")
            print("\nFirst 10 movies:")
            for i, movie in enumerate(movies[:10], 1):
                print(f"  {i}. {movie['title']} ({movie['year']})")

            if len(movies) > 10:
                print(f"\n  ... and {len(movies) - 10} more movies")
        else:
            print("✗ No movies found in HTML file")

    except FileNotFoundError:
        print("✗ HTML file not found. Make sure 'samplelistsiteinfo.html' is in the project directory.")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_short_url():
    """Test scraping with the short URL (boxd.it)."""
    print("\n" + "="*60)
    print("TEST 2: Short URL (boxd.it)")
    print("="*60)

    short_url = "https://boxd.it/R0oQe"

    print(f"\nScraping: {short_url}")
    print("(This will fetch live data from Letterboxd)")

    try:
        movies = scrape_list(short_url, max_movies=10)

        if movies:
            print(f"\n✓ Successfully scraped {len(movies)} movies!")
            print("\nMovies found:")
            for i, movie in enumerate(movies, 1):
                print(f"  {i}. {movie['title']} ({movie['year']})")
        else:
            print("✗ No movies found")

    except (InvalidURLError, ListNotFoundError) as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def test_full_url():
    """Test scraping with the full URL."""
    print("\n" + "="*60)
    print("TEST 3: Full URL (letterboxd.com)")
    print("="*60)

    full_url = "https://letterboxd.com/ipoopintheaters/list/childhood-movies/"

    print(f"\nScraping: {full_url}")
    print("(This will fetch live data from Letterboxd)")

    try:
        movies = scrape_list(full_url, max_movies=10)

        if movies:
            print(f"\n✓ Successfully scraped {len(movies)} movies!")
            print("\nMovies found:")
            for i, movie in enumerate(movies, 1):
                print(f"  {i}. {movie['title']} ({movie['year']})")
        else:
            print("✗ No movies found")

    except (InvalidURLError, ListNotFoundError) as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("LETTERBOXD SCRAPER - UPDATED TEST SUITE")
    print("="*60)

    # Test 1: Local HTML file (fast, no network needed)
    test_local_html()

    # Ask user if they want to test live URLs
    print("\n" + "="*60)
    user_input = input("\nTest live URLs? This will fetch data from Letterboxd. (y/n): ")

    if user_input.lower() in ('y', 'yes'):
        # Test 2: Short URL
        test_short_url()

        # Test 3: Full URL
        test_full_url()
    else:
        print("Skipping live URL tests.")

    print("\n" + "="*60)
    print("TESTS COMPLETED")
    print("="*60)
    print("\n✓ If you see movies listed above, the scraper is working!")


if __name__ == "__main__":
    main()
