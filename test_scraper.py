"""
Test script for Letterboxd scraper.
Run this to verify the scraper is working correctly.
"""

from modules.letterboxd_scraper import scrape_list, InvalidURLError, ListNotFoundError


def test_url_validation():
    """Test URL validation."""
    print("\n" + "="*60)
    print("TEST 1: URL Validation")
    print("="*60)
    
    from modules.letterboxd_scraper import LetterboxdScraper
    scraper = LetterboxdScraper()
    
    # Valid URLs
    valid_urls = [
        "https://letterboxd.com/dave/list/official-top-250-narrative-feature-films/",
        "letterboxd.com/jack/list/1001-movies-you-must-see-before-you-die/",
        "https://www.letterboxd.com/lifeasfiction/list/top-100-action-movies/",
    ]
    
    print("\nTesting valid URLs:")
    for url in valid_urls:
        try:
            normalized = scraper.validate_url(url)
            print(f"✓ {url[:50]}... → Valid")
        except InvalidURLError as e:
            print(f"✗ {url[:50]}... → ERROR: {e}")
    
    # Invalid URLs
    invalid_urls = [
        "https://google.com/some/path",
        "https://letterboxd.com/dave/films/",
        "not-a-url",
    ]
    
    print("\nTesting invalid URLs (should fail):")
    for url in invalid_urls:
        try:
            normalized = scraper.validate_url(url)
            print(f"✗ {url[:50]}... → Should have failed!")
        except InvalidURLError as e:
            print(f"✓ {url[:50]}... → Correctly rejected")


def test_small_list():
    """Test scraping a small public list."""
    print("\n" + "="*60)
    print("TEST 2: Small List Scraping")
    print("="*60)
    
    # Example: A popular public list (you can replace with any public list)
    # This is Dave's Official Top 250 list (may have many movies)
    test_url = "https://letterboxd.com/dave/list/official-top-250-narrative-feature-films/"
    
    print(f"\nScraping first 10 movies from list...")
    print(f"URL: {test_url}")
    
    try:
        movies = scrape_list(test_url, max_movies=10)
        
        if movies:
            print(f"\n✓ Successfully scraped {len(movies)} movies!")
            print("\nFirst 5 movies:")
            for i, movie in enumerate(movies[:5], 1):
                print(f"  {i}. {movie['title']} ({movie['year']})")
        else:
            print("✗ No movies found (list might be empty or structure changed)")
            
    except (InvalidURLError, ListNotFoundError) as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def test_error_handling():
    """Test error handling for invalid/private lists."""
    print("\n" + "="*60)
    print("TEST 3: Error Handling")
    print("="*60)
    
    # Test with invalid URL
    print("\nTesting invalid URL...")
    try:
        movies = scrape_list("https://letterboxd.com/invalid/url/format")
        print("✗ Should have raised InvalidURLError")
    except InvalidURLError:
        print("✓ Correctly raised InvalidURLError")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Test with non-existent list (404)
    print("\nTesting non-existent list...")
    try:
        movies = scrape_list("https://letterboxd.com/testuser/list/definitely-does-not-exist-12345/")
        print("✗ Should have raised ListNotFoundError")
    except ListNotFoundError:
        print("✓ Correctly raised ListNotFoundError (404)")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("LETTERBOXD SCRAPER TEST SUITE")
    print("="*60)
    
    try:
        test_url_validation()
        test_small_list()
        test_error_handling()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("\n✓ If you see movies listed above, the scraper is working!")
        print("\nNext steps:")
        print("1. Try scraping your own Letterboxd lists")
        print("2. Move on to Phase 3: TMDB Client integration")
        
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
