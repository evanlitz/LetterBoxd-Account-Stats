"""
Letterboxd Profile Scraper
Scrapes a user's complete watched/rated films from their Letterboxd profile.
"""

import re
import time
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup


class InvalidUsernameError(Exception):
    """Raised when username is invalid."""
    pass


class ProfileNotFoundError(Exception):
    """Raised when profile cannot be accessed."""
    pass


def validate_username(username: str) -> str:
    """
    Validate and clean a Letterboxd username.

    Args:
        username: Username or URL to validate

    Returns:
        Clean username

    Raises:
        InvalidUsernameError: If username is invalid
    """
    if not username or not username.strip():
        raise InvalidUsernameError("Username cannot be empty")

    username = username.strip()

    # If they pasted a URL, extract username
    if 'letterboxd.com/' in username:
        # Extract username from URL patterns:
        # https://letterboxd.com/username/
        # https://letterboxd.com/username/films/
        match = re.search(r'letterboxd\.com/([a-zA-Z0-9_-]+)', username)
        if match:
            username = match.group(1)
        else:
            raise InvalidUsernameError("Could not extract username from URL")

    # Validate username format (alphanumeric, underscore, hyphen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise InvalidUsernameError(
            "Username can only contain letters, numbers, underscores, and hyphens"
        )

    return username.lower()


def scrape_profile(username: str, max_pages: Optional[int] = None) -> List[Dict[str, any]]:
    """
    Scrape all rated/watched films from a Letterboxd user profile.

    Args:
        username: Letterboxd username
        max_pages: Optional limit on pages to scrape (for testing)

    Returns:
        List of film dictionaries with title, year, rating, etc.

    Raises:
        InvalidUsernameError: If username is invalid
        ProfileNotFoundError: If profile cannot be accessed
    """
    # Validate username
    username = validate_username(username)

    print(f"\n{'='*70}")
    print(f"SCRAPING LETTERBOXD PROFILE: {username}")
    print(f"{'='*70}")

    base_url = f"https://letterboxd.com/{username}/films/"
    all_films = []
    page = 1

    # Setup session with headers to mimic a real browser
    # Note: Don't manually set Accept-Encoding - let requests handle compression automatically
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })

    while True:
        # Construct page URL - all pages use /page/N/ format
        url = f"{base_url}page/{page}/"

        print(f"\nFetching page {page}: {url}")

        # Small delay before each request to avoid rate limiting
        if page > 1:
            time.sleep(1.0)

        try:
            # Fetch page
            response = session.get(url, timeout=30)

            if response.status_code == 404:
                if page == 1:
                    raise ProfileNotFoundError(
                        f"Profile '{username}' not found. Check the username and try again."
                    )
                else:
                    # Reached end of pagination
                    print(f"✓ Reached end of profile (page {page} doesn't exist)")
                    break

            if response.status_code == 403:
                raise ProfileNotFoundError(
                    f"Access denied to profile '{username}'. The profile might be private."
                )

            if response.status_code != 200:
                raise ProfileNotFoundError(
                    f"Error accessing profile: HTTP {response.status_code}"
                )

            # Parse HTML (use response.text to let requests handle encoding)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Debug: Check if we got valid HTML
            print(f"  Response length: {len(response.text)} chars")
            print(f"  Content type: {response.headers.get('Content-Type', 'unknown')}")

            # Check for film elements
            film_elements_count = len(soup.find_all('div', {'data-film-id': True}))
            print(f"  Found {film_elements_count} div elements with data-film-id")

            # Debug: Save first page HTML for inspection
            if page == 1 and film_elements_count == 0:
                debug_file = f"debug_profile_{username}_page1.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  ⚠ Saved response to {debug_file} for debugging")

                # Check what classes exist on the page
                poster_grid = soup.find('div', class_='poster-grid')
                print(f"  Found poster-grid div: {poster_grid is not None}")

                # Check for React components
                react_components = soup.find_all('div', class_='react-component')
                print(f"  Found {len(react_components)} react-component divs")

            # Extract films from this page
            films = extract_films_from_page(soup, page)

            if not films:
                if page == 1:
                    print("⚠ No films found on profile")
                    break
                else:
                    print(f"✓ No more films on page {page}")
                    break

            all_films.extend(films)
            print(f"✓ Extracted {len(films)} films from page {page} (total: {len(all_films)})")

            # Check if we should continue
            if max_pages and page >= max_pages:
                print(f"✓ Reached max pages limit ({max_pages})")
                break

            # Check for next page
            if not has_next_page(soup):
                print(f"✓ No more pages (total pages: {page})")
                break

            page += 1

        except requests.exceptions.Timeout:
            print(f"⚠ Timeout fetching page {page}, stopping")
            break
        except requests.exceptions.RequestException as e:
            print(f"⚠ Network error on page {page}: {e}")
            if page == 1:
                raise ProfileNotFoundError(f"Network error: {str(e)}")
            break

    print(f"\n{'='*70}")
    print(f"✓ SCRAPING COMPLETE: {len(all_films)} total films")
    print(f"{'='*70}\n")

    return all_films


def extract_films_from_page(soup: BeautifulSoup, page_num: int) -> List[Dict[str, any]]:
    """
    Extract film data from a single page.

    Args:
        soup: BeautifulSoup object of the page
        page_num: Page number (for logging)

    Returns:
        List of film dictionaries
    """
    films = []

    # Find all film poster containers
    # Films are in divs with class "react-component" and data-film-id
    film_elements = soup.find_all('div', {'data-film-id': True})

    for element in film_elements:
        try:
            # Extract film data from data attributes
            film_data = {
                'title': element.get('data-item-name', ''),
                'year': None,
                'slug': element.get('data-item-slug', ''),
                'film_id': element.get('data-film-id', ''),
                'letterboxd_url': element.get('data-item-link', ''),
                'rating': None,
                'rating_stars': None,
                'liked': False,
                'reviewed': False
            }

            # Extract year from title if present (format: "Title (2024)")
            title_with_year = film_data['title']
            year_match = re.search(r'\((\d{4})\)$', title_with_year)
            if year_match:
                film_data['year'] = int(year_match.group(1))
                # Clean title (remove year)
                film_data['title'] = re.sub(r'\s*\(\d{4}\)$', '', title_with_year).strip()

            # Find the viewing data section (contains rating, liked, reviewed)
            parent = element.find_parent('li') or element.find_parent('div')
            if parent:
                viewing_data = parent.find('p', class_='poster-viewingdata')

                if viewing_data:
                    # Extract rating
                    rating_span = viewing_data.find('span', class_='rating')
                    if rating_span:
                        # Rating classes: rated-1 (0.5★) to rated-10 (5★)
                        rating_class = [c for c in rating_span.get('class', []) if c.startswith('rated-')]
                        if rating_class:
                            # Extract number from class (e.g., "rated-10" -> 10)
                            rating_value = int(rating_class[0].split('-')[1])
                            film_data['rating'] = rating_value  # Store as 1-10
                            film_data['rating_stars'] = rating_value / 2  # Convert to 0.5-5.0 stars

                    # Check if liked
                    liked_span = viewing_data.find('span', class_='like')
                    if liked_span and 'liked-micro' in liked_span.get('class', []):
                        film_data['liked'] = True

                    # Check if reviewed
                    review_link = viewing_data.find('a', class_='review-micro')
                    if review_link:
                        film_data['reviewed'] = True

            # Only add if we have at least a title
            if film_data['title']:
                films.append(film_data)

        except Exception as e:
            print(f"⚠ Error extracting film data: {e}")
            continue

    return films


def has_next_page(soup: BeautifulSoup) -> bool:
    """
    Check if there's a next page in pagination.

    Args:
        soup: BeautifulSoup object of current page

    Returns:
        True if next page exists, False otherwise
    """
    # Look for pagination next link
    pagination = soup.find('div', class_='pagination')
    if pagination:
        next_link = pagination.find('a', class_='next')
        return next_link is not None

    return False


def get_profile_stats(films: List[Dict[str, any]]) -> Dict[str, any]:
    """
    Calculate statistics from scraped films.

    Args:
        films: List of film dictionaries

    Returns:
        Dictionary of statistics
    """
    total_films = len(films)

    # Count rated vs unrated
    rated_films = [f for f in films if f.get('rating') is not None]
    unrated_films = total_films - len(rated_films)

    # Calculate average rating
    avg_rating = 0
    if rated_films:
        avg_rating = sum(f['rating'] for f in rated_films) / len(rated_films)

    # Count liked films
    liked_count = sum(1 for f in films if f.get('liked'))

    # Count reviewed films
    reviewed_count = sum(1 for f in films if f.get('reviewed'))

    # Rating distribution
    rating_distribution = {}
    for i in range(1, 11):
        rating_distribution[i] = sum(1 for f in rated_films if f.get('rating') == i)

    # Years distribution
    years = [f['year'] for f in films if f.get('year')]
    year_range = (min(years), max(years)) if years else (None, None)

    return {
        'total_films': total_films,
        'rated_films': len(rated_films),
        'unrated_films': unrated_films,
        'average_rating': avg_rating,
        'average_rating_stars': avg_rating / 2,
        'liked_count': liked_count,
        'reviewed_count': reviewed_count,
        'rating_distribution': rating_distribution,
        'year_range': year_range
    }


# Convenience function
def scrape_user_profile(username: str, max_pages: Optional[int] = None) -> tuple[List[Dict], Dict]:
    """
    Scrape profile and return films + statistics.

    Returns:
        Tuple of (films, stats)
    """
    films = scrape_profile(username, max_pages)
    stats = get_profile_stats(films)
    return films, stats
