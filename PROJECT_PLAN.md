# Movie Recommender Bot - Implementation Plan

## Project Overview
A Python web application that scrapes Letterboxd lists, enriches movie data via TMDB API, and uses Claude LLM to generate personalized movie recommendations.

---

## Project Requirements (from discussion)

### Application Type
- **Web application** (Python-based)

### Data Input
- **Public Letterboxd list URL** for list scraping
- **Account name** for future account-based scraping
- Initially focused on **lists only** (ratings/reviews later)

### LLM Strategy
- **Primary**: Claude (Anthropic API) - Claude 3.5 Sonnet recommended
- **Secondary**: OpenAI (for specific tasks if needed in future)

### Recommendation Approach
Combine multiple strategies:
1. Similar movies to what user has watched
2. Hidden gems they might have missed
3. Fill gaps in their viewing (same director, adjacent genres, etc.)
4. Provide diverse, well-rounded recommendations

### Caching & Performance
- In-memory caching for API optimization
- Load data fresh each session (can expand persistence later)
- Optimize for cost vs. time tradeoff

### Output Format
- **10 movie recommendations**
- **No explanations initially** (can add brief reasons later)
- Display with movie posters and basic info

### Starting Point
- **From scratch** - no existing codebase

---

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **LLM**: Claude 3.5 Sonnet (Anthropic API)
- **Data Source**: TMDB API v3
- **Web Scraping**: BeautifulSoup4 + Requests
- **Frontend**: Jinja2 Templates + HTML/CSS/JS
- **Server**: Uvicorn (ASGI)

---

## Project Structure

```
letterboxd-recommender/
├── app.py                  # FastAPI main application
├── config.py               # Configuration and API keys
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── .gitignore             # Git ignore file
├── README.md              # Setup and usage instructions
├── PROJECT_PLAN.md        # This file - comprehensive plan
├── modules/
│   ├── __init__.py
│   ├── letterboxd_scraper.py   # Scrape Letterboxd lists
│   ├── tmdb_client.py          # TMDB API integration
│   └── recommender.py          # Claude LLM recommendation logic
├── templates/
│   ├── index.html              # Main page
│   └── results.html            # Recommendations display
└── static/
    ├── style.css               # Styling
    └── script.js               # Frontend logic
```

---

## Core Components

### 1. Letterboxd Scraper (`letterboxd_scraper.py`)

**Purpose**: Extract movie data from Letterboxd lists

**Key Functions**:
- Parse list URLs (format: `letterboxd.com/username/list/listname/`)
- Handle pagination for large lists (100+ movies)
- Extract: movie titles, release years
- Return: List of movie objects

**Technical Details**:
- Use `requests` + `BeautifulSoup4`
- Handle edge cases: private lists, invalid URLs, deleted lists
- Extract data from HTML structure (Letterboxd's poster grid)

**Output Format**:
```python
[
    {"title": "The Godfather", "year": 1972},
    {"title": "Pulp Fiction", "year": 1994},
    ...
]
```

---

### 2. TMDB Client (`tmdb_client.py`)

**Purpose**: Enrich movie data with detailed metadata from TMDB

**Key Functions**:
- `search_movie(title, year)` - Find TMDB ID for a movie
- `get_movie_details(movie_id)` - Fetch comprehensive metadata
- `cache_manager()` - In-memory caching to reduce API calls

**Data to Fetch**:
- Title, overview, genres
- Director, main cast (top 5 actors)
- Release date, rating, runtime
- Keywords, poster image URL
- Similar movies (for context)

**Technical Details**:
- TMDB API endpoint: `https://api.themoviedb.org/3/`
- Rate limiting: 40 requests per 10 seconds
- Caching: Python dict with `(title, year)` as key
- Error handling: Retry logic for failed requests

**API Endpoints Used**:
- `/search/movie` - Search by title
- `/movie/{id}` - Get movie details
- `/movie/{id}/credits` - Get cast/crew

---

### 3. Recommender (`recommender.py`)

**Purpose**: Use Claude LLM to analyze user's taste and generate recommendations

**Key Functions**:
- `format_movie_data(movies)` - Structure data for Claude
- `generate_recommendations(watched_movies)` - Call Claude API
- `parse_response(claude_output)` - Extract movie list from JSON

**Claude Prompt Template**:
```
You are an expert film curator and analyst. Analyze this user's watched movies and recommend 10 films they haven't seen yet.

USER'S WATCHED MOVIES:
[Structured list with: title, year, genre, director, cast, overview, rating, keywords]

RECOMMENDATION STRATEGY:
1. Identify patterns in their taste:
   - Favorite genres, directors, actors
   - Preferred themes, storytelling styles
   - Time periods and film movements
   - Rating patterns

2. Provide 10 diverse recommendations:
   - 3-4 similar movies they'll likely love (safe bets based on clear preferences)
   - 2-3 hidden gems (critically acclaimed but lesser-known films in their taste profile)
   - 2-3 gap-fillers (expand horizons: same director but different genre, adjacent movements, thematic connections)

3. Ensure variety in your recommendations:
   - Mix of decades/eras
   - Different genres (while staying in taste profile)
   - Balance between classics and modern films

OUTPUT FORMAT (valid JSON only):
{
  "recommendations": [
    {"title": "Movie Title", "year": 2020},
    {"title": "Another Movie", "year": 1995},
    ...
  ]
}

Provide ONLY the JSON output, no additional commentary.
```

**Model Selection**:
- **Claude 3.5 Sonnet**: Best balance of reasoning and cost
- Input tokens: ~2,000-5,000 per request (depending on list size)
- Output tokens: ~200-300
- Cost per request: ~$0.01-0.03

---

### 4. FastAPI Application (`app.py`)

**Purpose**: Web server orchestrating all components

**Routes**:

1. **GET `/`**
   - Render home page
   - Display input form for Letterboxd URL

2. **POST `/recommend`**
   - Accept Letterboxd list URL
   - Orchestrate full pipeline
   - Return recommendations

**Request Flow**:
```
1. Receive POST request with list URL
2. Validate URL format
3. Call letterboxd_scraper.scrape_list(url)
   → Get list of movie titles/years
4. For each movie:
   - Call tmdb_client.search_movie(title, year)
   - Call tmdb_client.get_movie_details(movie_id)
   - Cache results
5. Call recommender.generate_recommendations(enriched_movies)
   → Get 10 recommended movie titles
6. For each recommendation:
   - Call tmdb_client.get_movie_details(movie_id)
   - Fetch poster image, metadata
7. Render results.html with recommendations
```

**Error Handling**:
- Invalid URL → 400 error with helpful message
- List not found → 404 error
- API failures → 503 with retry suggestion
- Partial failures → Continue with available data (log errors)

**Performance Optimizations**:
- Async API calls where possible
- Batch TMDB requests
- Progress indicators for user

---

### 5. Frontend (`templates/` + `static/`)

**index.html** - Home Page:
```html
- Header with app title/description
- Input form:
  - Text field for Letterboxd list URL
  - Submit button
  - Example URL placeholder
- Instructions section
- Footer
```

**results.html** - Recommendations Display:
```html
- Header with "Your Recommendations"
- Grid layout (2-3 columns) showing:
  - Movie poster (from TMDB)
  - Title + Year
  - Genre tags
  - Link to TMDB page
  - Link to Letterboxd page
- "Try another list" button
```

**style.css** - Styling:
- Clean, modern design
- Responsive layout (mobile-friendly)
- Loading spinner/animation
- Smooth transitions
- Dark mode friendly

**script.js** - Frontend Logic:
- Form validation
- Loading state management
- Smooth scrolling to results
- Error message display

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                               │
│              (Letterboxd List URL)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              LETTERBOXD SCRAPER                             │
│  - Parse HTML                                               │
│  - Extract movie titles + years                             │
│  - Handle pagination                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              [List of Movie Titles]
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 TMDB CLIENT (Search)                        │
│  - Search each movie by title + year                        │
│  - Get TMDB movie IDs                                       │
│  - Check cache first                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
               [List of Movie IDs]
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              TMDB CLIENT (Details)                          │
│  - Fetch comprehensive metadata for each movie              │
│  - Director, cast, genres, overview, keywords               │
│  - Cache results                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
          [Enriched Movie Dataset]
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CLAUDE RECOMMENDER                             │
│  - Format data for Claude                                   │
│  - Send analysis prompt                                     │
│  - Parse JSON response                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        [10 Recommended Movie Titles]
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         TMDB CLIENT (Recommendation Details)                │
│  - Fetch metadata for recommended movies                    │
│  - Get poster images                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  DISPLAY RESULTS                            │
│  - Show 10 movies with posters                              │
│  - Include title, year, genre                               │
│  - Links to TMDB/Letterboxd                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Caching Strategy

### Why Cache?
- **TMDB API**: Free but rate-limited (40 req/10 sec)
- **Claude API**: Costs money per token
- **User Experience**: Faster responses

### What to Cache?

**✅ Cache TMDB Responses**:
- Store: Full movie metadata
- Key: `(movie_title, year)`
- Duration: Session-based (in-memory dict)
- Benefit: Avoid re-fetching same movies in a session

**❌ Don't Cache Claude Responses**:
- User might want different recommendations each time
- Small cost savings vs. reduced flexibility

### Implementation:

```python
# In tmdb_client.py
class TMDBClient:
    def __init__(self):
        self.cache = {}  # In-memory cache

    def get_movie_details(self, title, year):
        cache_key = f"{title}_{year}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        # Fetch from API
        data = self._fetch_from_api(title, year)
        self.cache[cache_key] = data
        return data
```

### Future Improvements:
- **Redis**: For persistent, cross-session caching
- **JSON files**: Simple file-based persistence
- **TTL**: Expire cache after 24 hours to keep data fresh

---

## Dependencies

### requirements.txt

```
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# LLM Integration
anthropic==0.7.0

# HTTP & Web Scraping
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3

# Environment Management
python-dotenv==1.0.0

# Templating (included with FastAPI but explicit)
jinja2==3.1.2

# Data Validation (included with FastAPI)
pydantic==2.5.0

# Optional but recommended
httpx==0.25.1          # Async HTTP client
tenacity==8.2.3        # Retry logic
```

### Why Each Dependency?

- **FastAPI**: Modern, async web framework
- **Uvicorn**: ASGI server for FastAPI
- **anthropic**: Official Claude API SDK
- **requests**: HTTP library for web scraping
- **beautifulsoup4**: HTML parsing for Letterboxd
- **lxml**: Fast XML/HTML parser for BS4
- **python-dotenv**: Load environment variables from .env
- **jinja2**: Template engine for HTML rendering
- **pydantic**: Data validation and serialization

---

## Environment Setup

### Required API Keys

1. **TMDB API Key** (Free)
   - Sign up at: https://www.themoviedb.org/signup
   - Navigate to: Settings → API → Request API Key
   - Choose "Developer" option
   - Copy the API Key (v3 auth)

2. **Anthropic API Key** (Paid)
   - Sign up at: https://console.anthropic.com
   - Go to: API Keys → Create Key
   - Copy the key (starts with `sk-ant-`)
   - Add credits to account

### .env File

Create `.env` in project root:

```bash
# Anthropic API Key for Claude
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# TMDB API Key
TMDB_API_KEY=your_tmdb_api_key_here

# Optional: Environment
ENVIRONMENT=development

# Optional: Debug mode
DEBUG=True
```

### .gitignore

```
# Environment
.env
venv/
__pycache__/
*.pyc

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Cache
.cache/
```

---

## Implementation Order

### Phase 1: Project Setup (30 mins)
1. Create project directory structure
2. Initialize virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Create `requirements.txt` and install:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up `.env` file with API keys
5. Create `.gitignore`
6. Initialize git repository

### Phase 2: Letterboxd Scraper (1-2 hours)
1. Create `modules/letterboxd_scraper.py`
2. Implement `scrape_list(url)` function
3. Test with sample Letterboxd lists:
   - Small list (~10 movies)
   - Large list (100+ movies)
   - Edge cases (invalid URL, private list)
4. Add error handling
5. Write unit tests

### Phase 3: TMDB Client (1-2 hours)
1. Create `modules/tmdb_client.py`
2. Implement `search_movie(title, year)`
3. Implement `get_movie_details(movie_id)`
4. Add in-memory caching
5. Test with scraper output
6. Handle edge cases (movie not found, API errors)
7. Add retry logic for failed requests

### Phase 4: Claude Recommender (1 hour)
1. Create `modules/recommender.py`
2. Design Claude prompt template
3. Implement `generate_recommendations(movies)`
4. Test with sample movie data
5. Refine prompt based on output quality
6. Add JSON parsing and validation

### Phase 5: FastAPI Backend (2 hours)
1. Create `app.py` with basic routes
2. Implement `GET /` route (home page)
3. Implement `POST /recommend` route
4. Connect all modules:
   - Scraper → TMDB → Recommender → TMDB
5. Add error handling at each stage
6. Add logging for debugging
7. Test end-to-end flow

### Phase 6: Frontend (2-3 hours)
1. Create `templates/index.html`
   - Input form
   - Instructions
   - Styling
2. Create `templates/results.html`
   - Grid layout for recommendations
   - Movie posters and info
3. Create `static/style.css`
   - Responsive design
   - Loading states
4. Create `static/script.js`
   - Form validation
   - Loading spinner
5. Test UI/UX flow

### Phase 7: Testing & Refinement (2 hours)
1. End-to-end testing with various lists
2. Test error handling
3. Optimize performance
4. Refine Claude prompt for better recommendations
5. Improve error messages
6. Add logging and monitoring

### Phase 8: Documentation (30 mins)
1. Write `README.md` with:
   - Project description
   - Setup instructions
   - Usage guide
   - API key setup
   - Troubleshooting
2. Add code comments
3. Document API endpoints

**Total Estimated Time: 10-13 hours**

---

## Error Handling Strategy

### Categories of Errors

#### 1. User Input Errors
- **Invalid URL format**
  - Detection: Regex validation for Letterboxd URLs
  - Response: "Please enter a valid Letterboxd list URL (e.g., letterboxd.com/username/list/listname/)"

- **Private/deleted list**
  - Detection: HTTP 404 or 403 from Letterboxd
  - Response: "This list is private or doesn't exist. Please use a public list."

#### 2. TMDB API Errors
- **Movie not found**
  - Detection: Empty search results
  - Action: Log movie title, skip it, continue with others
  - User notification: "Matched X out of Y movies"

- **API rate limiting**
  - Detection: HTTP 429 response
  - Action: Wait and retry with exponential backoff

- **API key invalid**
  - Detection: HTTP 401 response
  - Action: Stop execution, show setup instructions

#### 3. Claude API Errors
- **API failure**
  - Detection: HTTP 500/503 errors
  - Action: Retry up to 3 times with backoff
  - Fallback: Show cached recommendations or generic suggestions

- **Invalid API key**
  - Detection: HTTP 401
  - Action: Show setup instructions

- **Malformed response**
  - Detection: JSON parsing error
  - Action: Retry prompt with stricter formatting instructions

#### 4. Network Errors
- **Timeout**
  - Action: Retry with increased timeout
  - User notification: "This is taking longer than usual..."

- **Connection failure**
  - Action: Check internet connection, retry
  - Response: "Unable to connect. Please check your internet connection."

### Graceful Degradation Rules

1. **Minimum viable data**: Need at least 5 matched movies to generate recommendations
2. **Partial success**: If 50%+ of movies matched, proceed with warnings
3. **Fallback recommendations**: If Claude fails, use TMDB's "similar movies" feature
4. **User feedback**: Always inform user of what went wrong and how to fix it

### Implementation Pattern

```python
# Example error handling pattern
async def recommend(url: str):
    try:
        # Step 1: Scrape
        try:
            movies = scrape_list(url)
            if not movies:
                raise ValueError("No movies found in list")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return {"error": "Unable to access Letterboxd list. Is it public?"}

        # Step 2: Enrich with TMDB
        enriched = []
        for movie in movies:
            try:
                details = get_movie_details(movie['title'], movie['year'])
                enriched.append(details)
            except Exception as e:
                logger.warning(f"Couldn't find {movie['title']}: {e}")
                continue

        if len(enriched) < 5:
            return {"error": "Not enough movies matched. Try a different list."}

        # Step 3: Get recommendations
        try:
            recs = generate_recommendations(enriched)
            return {"recommendations": recs}
        except Exception as e:
            logger.error(f"Recommendation failed: {e}")
            return {"error": "Unable to generate recommendations. Please try again."}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "Something went wrong. Please try again later."}
```

---

## API Cost Estimates

### TMDB API
- **Cost**: FREE
- **Rate Limit**: 40 requests per 10 seconds
- **Requests per recommendation**:
  - Search: 1 per movie in user's list (~50 movies avg)
  - Details: 1 per movie (~50 movies)
  - Recommendations: 10 movies
  - **Total**: ~110 requests per recommendation flow
- **Time**: ~3-5 seconds with batching

### Claude API (Anthropic)

**Pricing** (Claude 3.5 Sonnet):
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens

**Token Usage per Request**:
- Input tokens: ~2,000-5,000 (depends on list size)
  - Prompt template: ~500 tokens
  - Movie data: ~30-50 tokens per movie × 50 movies = 1,500-2,500 tokens
- Output tokens: ~200-300 (JSON with 10 movie recommendations)

**Cost per Request**:
- Input: (5,000 tokens / 1,000,000) × $3 = $0.015
- Output: (300 tokens / 1,000,000) × $15 = $0.0045
- **Total: ~$0.02 per recommendation**

**Monthly Costs** (estimated usage):
- 10 requests/day × 30 days = 300 requests
- 300 × $0.02 = **$6/month**

**Optimization Tips**:
- Use Claude 3.5 Haiku for cheaper option (~$1/M input, $5/M output)
- Reduce token count by sending only essential movie metadata
- Cache common recommendations if patterns emerge

---

## Success Metrics & MVP Goals

### MVP Success Criteria

#### Functionality
- ✅ Successfully scrapes public Letterboxd lists
- ✅ Handles lists of 10-200 movies
- ✅ Matches 80%+ of movies in TMDB
- ✅ Returns 10 diverse, relevant recommendations
- ✅ Displays results with movie posters

#### Performance
- ✅ End-to-end process completes in < 30 seconds (for 50-movie list)
- ✅ Handles concurrent users (3-5 simultaneous requests)
- ✅ Graceful error handling (no crashes)

#### User Experience
- ✅ Clean, intuitive web interface
- ✅ Clear error messages
- ✅ Loading indicators during processing
- ✅ Responsive design (mobile-friendly)

### Quality Metrics

**Recommendation Quality** (subjective):
- Recommendations should feel personalized
- Mix of familiar and surprising choices
- Appropriate diversity (not all same genre/era)
- Actually match user's taste profile

**Test with**:
- Your own Letterboxd lists
- Friends/family lists with known preferences
- Curated test lists (e.g., "all horror", "French New Wave", "modern blockbusters")

---

## Future Enhancements Roadmap

### Phase 2: Enhanced Personalization
1. **Ratings/Reviews Integration**
   - Scrape user ratings from Letterboxd
   - Weight recommendations toward higher-rated patterns
   - Avoid recommending movies similar to low-rated ones

2. **Explanation Feature**
   - Add "Why recommended" section (1-2 sentences per movie)
   - Update Claude prompt to include reasoning
   - Display in UI as expandable text

3. **Account-Wide Scraping**
   - Support username input (not just lists)
   - Scrape all watched films, diary entries
   - More comprehensive taste analysis

### Phase 3: Advanced Features
1. **Streaming Availability**
   - Integrate JustWatch API
   - Show where to watch each recommendation
   - Filter by streaming service

2. **User Accounts & Persistence**
   - User registration/login
   - Save watched history
   - Track recommendation success (did they watch it?)
   - Improve recommendations over time

3. **Recommendation Filters**
   - Filter by genre, decade, runtime
   - "Mood" selector (e.g., "lighthearted", "intense", "weird")
   - Country/language preferences

### Phase 4: Social & Export Features
1. **Comparison Mode**
   - Input two users' Letterboxd profiles
   - Recommend movies both would enjoy
   - "Date night mode"

2. **Export Options**
   - Export recommendations to Letterboxd watchlist
   - Generate shareable recommendation cards
   - Email/PDF report

3. **Recommendation Modes**
   - "Surprise me" (prioritize unexpected picks)
   - "Safe bets" (high-confidence matches)
   - "Deep cuts" (obscure films only)
   - "Catch up" (famous films they haven't seen)

### Phase 5: Analytics & Intelligence
1. **Taste Profile Dashboard**
   - Visualize user's taste patterns
   - Favorite genres, directors, decades
   - Taste "gaps" to explore

2. **Trending Recommendations**
   - Recommend newly released films
   - Letterboxd-trending movies in user's taste

3. **Collaborative Filtering**
   - "Users with similar taste also loved..."
   - Build recommendation database across users

---

## Technical Considerations

### Security
- **API Key Protection**: Store in `.env`, never commit
- **Input Validation**: Sanitize all user inputs
- **Rate Limiting**: Prevent abuse of recommendation endpoint
- **HTTPS**: Use SSL in production
- **CORS**: Configure properly for API access

### Performance Optimization
- **Async Operations**: Use `asyncio` for concurrent API calls
- **Connection Pooling**: Reuse HTTP connections
- **Batch Processing**: Group TMDB requests
- **Response Caching**: Cache static assets (posters)
- **CDN**: Serve static files from CDN in production

### Monitoring & Logging
- **Application Logs**: Track all API calls and errors
- **Performance Metrics**: Log response times
- **Error Tracking**: Integrate Sentry or similar
- **Analytics**: Track usage patterns (privacy-compliant)

### Deployment Considerations
- **Local Development**: Uvicorn dev server
- **Production**:
  - Gunicorn + Uvicorn workers
  - Docker containerization
  - Deploy to: Render, Railway, Fly.io, or Heroku
- **Environment Variables**: Properly configure for prod vs. dev
- **Database**: Add PostgreSQL/Redis if adding user accounts

---

## Testing Strategy

### Unit Tests
- Test letterboxd_scraper with mocked HTML
- Test tmdb_client with mocked API responses
- Test recommender with sample data

### Integration Tests
- Test full pipeline with real APIs (limited test data)
- Verify error handling at each stage
- Test caching behavior

### End-to-End Tests
- Test with various Letterboxd lists
- Verify UI displays correctly
- Test on different browsers/devices

### Test Lists for Quality Assurance
1. **Genre-specific**: All horror, all comedy, etc.
2. **Director-focused**: Kubrick, Tarantino, Ghibli films
3. **Era-specific**: 1970s classics, 2020s releases
4. **Mixed bag**: Completely random selections
5. **Edge cases**: Very obscure films, foreign cinema

---

## Development Workflow

### Git Workflow
1. **Main branch**: Production-ready code
2. **Dev branch**: Active development
3. **Feature branches**: Individual features
4. **Commit messages**: Clear, descriptive

### Code Quality
- **Linting**: Use `ruff` or `pylint`
- **Formatting**: Use `black`
- **Type hints**: Add where beneficial
- **Docstrings**: Document all public functions

### Review Checklist Before Launch
- [ ] All API keys in `.env`, not hardcoded
- [ ] Error handling for all external calls
- [ ] User-friendly error messages
- [ ] Loading states in UI
- [ ] Tested with 5+ different lists
- [ ] README complete with setup instructions
- [ ] `.gitignore` properly configured
- [ ] Requirements.txt up to date
- [ ] Comments in complex code sections
- [ ] No console.log or debug prints in production

---

## Resources & References

### Documentation
- **FastAPI**: https://fastapi.tiangolo.com
- **TMDB API**: https://developers.themoviedb.org/3
- **Anthropic (Claude)**: https://docs.anthropic.com
- **BeautifulSoup**: https://www.crummy.com/software/BeautifulSoup/bs4/doc/

### Helpful Links
- **Letterboxd URL patterns**: https://letterboxd.com/about/api/ (no official API, scraping necessary)
- **TMDB Python Library**: https://github.com/AntonDeMeester/tmdbv3api
- **FastAPI Templates**: https://fastapi.tiangolo.com/advanced/templates/

### Community
- **r/Letterboxd**: Reddit community for user feedback
- **r/FastAPI**: Technical support
- **Anthropic Discord**: Claude API help

---

## Quick Start Commands

```bash
# 1. Clone/create project
mkdir letterboxd-recommender
cd letterboxd-recommender

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
# Create .env file with:
# ANTHROPIC_API_KEY=your_key
# TMDB_API_KEY=your_key

# 5. Run development server
uvicorn app:app --reload

# 6. Open browser
# Navigate to: http://localhost:8000
```

---

## Support & Maintenance

### Common Issues
1. **"Movie not found in TMDB"**
   - Letterboxd and TMDB naming differences
   - Solution: Fuzzy matching, manual overrides

2. **"Recommendations not diverse enough"**
   - Claude prompt needs refinement
   - Solution: Iterate on prompt engineering

3. **"Slow response times"**
   - Too many API calls
   - Solution: Better caching, async optimization

### Getting Help
- Check logs in console
- Review TMDB API status: https://www.themoviedb.org/talk
- Review Anthropic API status: https://status.anthropic.com
- GitHub issues (if open-sourced)

---

## Project Timeline

**Week 1**: Core functionality
- Days 1-2: Setup + Letterboxd scraper + TMDB client
- Days 3-4: Claude recommender + FastAPI backend
- Days 5-7: Frontend + testing

**Week 2**: Polish & launch
- Days 1-3: Bug fixes, UX improvements
- Days 4-5: Documentation, deployment prep
- Days 6-7: Deploy, test in production, gather feedback

**Ongoing**: Iterate based on usage and feedback

---

*This plan is a living document. Update as the project evolves!*
