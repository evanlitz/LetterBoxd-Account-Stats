"""
Letterboxd List Scraper
Scrapes public Letterboxd lists to extract movie titles and years.
"""

import re
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


class LetterboxdScraperError(Exception):
    """Base exception for Letterboxd scraper errors."""
    pass


class InvalidURLError(LetterboxdScraperError):
    """Raised when the provided URL is invalid."""
    pass


class ListNotFoundError(LetterboxdScraperError):
    """Raised when the list cannot be accessed (404, 403, etc.)."""
    pass


class LetterboxdScraper:
    """Scraper for extracting movie data from Letterboxd lists."""
    
    BASE_URL = "https://letterboxd.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    def __init__(self, request_delay: float = 0.5):
        """
        Initialize the scraper.
        
        Args:
            request_delay: Delay between requests in seconds (be nice to Letterboxd servers)
        """
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def validate_url(self, url: str) -> str:
        """
        Validate and normalize a Letterboxd list URL.
        Supports both full URLs (letterboxd.com/user/list/name/) and short URLs (boxd.it/xxxxx).

        Args:
            url: The Letterboxd list URL to validate

        Returns:
            Normalized URL (or original if short URL)

        Raises:
            InvalidURLError: If the URL is not a valid Letterboxd list URL
        """
        # Remove trailing slashes and whitespace
        url = url.strip().rstrip('/')

        # Add https:// if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Parse URL
        parsed = urlparse(url)

        # Check if it's a short URL (boxd.it)
        if parsed.netloc in ('boxd.it', 'www.boxd.it'):
            # Short URL - return as is, will be resolved during fetch
            return url

        # Check domain for full URLs
        if parsed.netloc not in ('letterboxd.com', 'www.letterboxd.com'):
            raise InvalidURLError(
                f"URL must be from letterboxd.com or boxd.it, got: {parsed.netloc}"
            )

        # Check path format: /username/list/listname/
        path_pattern = r'^/[\w-]+/list/[\w-]+/?$'
        if not re.match(path_pattern, parsed.path):
            raise InvalidURLError(
                f"URL must be a Letterboxd list in format: "
                f"letterboxd.com/username/list/listname/, got: {parsed.path}"
            )

        # Normalize to include trailing slash
        if not parsed.path.endswith('/'):
            parsed = parsed._replace(path=parsed.path + '/')

        # Return normalized URL
        return f"https://letterboxd.com{parsed.path}"
    
    def fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse a page from Letterboxd.
        
        Args:
            url: The URL to fetch
            
        Returns:
            BeautifulSoup object of the parsed HTML
            
        Raises:
            ListNotFoundError: If the page cannot be accessed
        """
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 404:
                raise ListNotFoundError(f"List not found (404): {url}")
            elif response.status_code == 403:
                raise ListNotFoundError(f"List is private or forbidden (403): {url}")
            elif response.status_code != 200:
                raise ListNotFoundError(f"Failed to access list (HTTP {response.status_code}): {url}")
            
            return BeautifulSoup(response.text, 'lxml')
            
        except requests.exceptions.RequestException as e:
            raise ListNotFoundError(f"Network error while accessing list: {str(e)}")
    
    def extract_movies_from_page(self, soup: BeautifulSoup) -> List[Dict[str, any]]:
        """
        Extract movie data from a Letterboxd list page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of movie dictionaries with 'title' and 'year' keys
        """
        movies = []

        # Find all movie items in the list
        # Letterboxd uses <li class="posteritem"> for each movie
        poster_items = soup.find_all('li', class_='posteritem')

        for item in poster_items:
            try:
                # Find the div with React component data
                react_div = item.find('div', class_='react-component')

                if not react_div:
                    continue

                # Extract movie name from data-item-name or data-item-full-display-name
                # Format: "Movie Title (YEAR)"
                full_name = react_div.get('data-item-full-display-name') or react_div.get('data-item-name')

                if not full_name:
                    continue

                # Parse title and year from format "Movie Title (YEAR)"
                # Use regex to extract title and year
                match = re.match(r'^(.+?)\s*\((\d{4})\)$', full_name.strip())

                if match:
                    title = match.group(1).strip()
                    year = int(match.group(2))

                    movies.append({
                        'title': title,
                        'year': year
                    })
                else:
                    # If no year in parentheses, just use the title
                    # Try to get year from slug as fallback
                    title = full_name.strip()
                    slug = react_div.get('data-item-slug', '')
                    year_match = re.search(r'-(\d{4})$', slug)

                    if year_match:
                        year = int(year_match.group(1))
                        movies.append({
                            'title': title,
                            'year': year
                        })

            except (ValueError, AttributeError) as e:
                # Skip this movie if we can't parse it properly
                continue

        return movies
    
    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """
        Determine the total number of pages in the list.
        
        Args:
            soup: BeautifulSoup object of the first page
            
        Returns:
            Total number of pages (minimum 1)
        """
        # Look for pagination
        pagination = soup.find('div', class_='pagination')
        
        if not pagination:
            return 1
        
        # Find all page links
        page_links = pagination.find_all('a', class_='paginate-page')
        
        if not page_links:
            return 1
        
        # Get the highest page number
        max_page = 1
        for link in page_links:
            try:
                page_num = int(link.text.strip())
                max_page = max(max_page, page_num)
            except ValueError:
                continue
        
        return max_page
    
    def scrape_list(self, url: str, max_movies: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Scrape a Letterboxd list and return all movies.
        
        Args:
            url: The Letterboxd list URL
            max_movies: Optional limit on number of movies to return
            
        Returns:
            List of movie dictionaries with 'title' and 'year' keys
            
        Raises:
            InvalidURLError: If the URL is invalid
            ListNotFoundError: If the list cannot be accessed
        """
        # Validate and normalize URL
        normalized_url = self.validate_url(url)
        
        print(f"Scraping Letterboxd list: {normalized_url}")
        
        # Fetch first page
        soup = self.fetch_page(normalized_url)
        
        # Extract movies from first page
        all_movies = self.extract_movies_from_page(soup)
        print(f"Found {len(all_movies)} movies on page 1")
        
        # Check if there are more pages
        total_pages = self.get_total_pages(soup)
        
        if total_pages > 1:
            print(f"List has {total_pages} pages, scraping remaining pages...")
            
            # Scrape remaining pages
            for page_num in range(2, total_pages + 1):
                # Stop if we've reached max_movies limit
                if max_movies and len(all_movies) >= max_movies:
                    break
                
                # Be nice to Letterboxd servers
                time.sleep(self.request_delay)
                
                # Construct paginated URL
                page_url = f"{normalized_url}page/{page_num}/"
                
                try:
                    page_soup = self.fetch_page(page_url)
                    page_movies = self.extract_movies_from_page(page_soup)
                    all_movies.extend(page_movies)
                    print(f"Found {len(page_movies)} movies on page {page_num}")
                    
                except ListNotFoundError as e:
                    print(f"Warning: Could not fetch page {page_num}: {e}")
                    # Continue with what we have
                    break
        
        # Apply max_movies limit if specified
        if max_movies:
            all_movies = all_movies[:max_movies]
        
        print(f"Total movies scraped: {len(all_movies)}")
        
        return all_movies


def scrape_list(url: str, max_movies: Optional[int] = None) -> List[Dict[str, any]]:
    """
    Convenience function to scrape a Letterboxd list.
    
    Args:
        url: The Letterboxd list URL
        max_movies: Optional limit on number of movies to return
        
    Returns:
        List of movie dictionaries with 'title' and 'year' keys
        
    Raises:
        InvalidURLError: If the URL is invalid
        ListNotFoundError: If the list cannot be accessed
    """
    scraper = LetterboxdScraper()
    return scraper.scrape_list(url, max_movies)
