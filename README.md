# Letterboxd Movie Recommender Bot

A Python web application that analyzes your Letterboxd lists and generates personalized movie recommendations using AI.

## Features

- Scrapes public Letterboxd lists
- Enriches movie data with TMDB API
- Uses Claude AI (Anthropic) to generate intelligent, personalized recommendations
- Displays 10 diverse movie recommendations with posters
- Clean, responsive web interface

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **LLM**: Claude 3.5 Sonnet (Anthropic API)
- **Data Source**: TMDB API v3
- **Web Scraping**: BeautifulSoup4 + Requests
- **Frontend**: Jinja2 Templates + HTML/CSS/JS

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- TMDB API Key (free)
- Anthropic API Key (paid, ~$0.02 per recommendation)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Letterboxd_Proj
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up API Keys

#### Get TMDB API Key (Free)
1. Sign up at https://www.themoviedb.org/signup
2. Go to Settings → API → Request API Key
3. Choose "Developer" option
4. Copy your API Key (v3 auth)

#### Get Anthropic API Key (Paid)
1. Sign up at https://console.anthropic.com
2. Go to API Keys → Create Key
3. Copy the key (starts with `sk-ant-`)
4. Add credits to your account

#### Create .env File

Copy the example file and add your keys:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
TMDB_API_KEY=your_actual_tmdb_key_here
ENVIRONMENT=development
DEBUG=True
```

### 5. Run the Application

```bash
uvicorn app:app --reload
```

The application will be available at: http://localhost:8000

## Usage

1. Open your browser to http://localhost:8000
2. Enter a public Letterboxd list URL (e.g., `https://letterboxd.com/username/list/listname/`)
3. Click "Get Recommendations"
4. Wait while the app:
   - Scrapes the Letterboxd list
   - Fetches movie data from TMDB
   - Analyzes your taste with Claude AI
   - Generates 10 personalized recommendations
5. View your recommendations with movie posters and details

## Project Structure

```
Letterboxd_Proj/
├── app.py                  # FastAPI main application
├── config.py               # Configuration and API keys
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── .env.example           # Environment template
├── .gitignore             # Git ignore file
├── README.md              # This file
├── PROJECT_PLAN.md        # Comprehensive implementation plan
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

## Cost Estimates

- **TMDB API**: FREE (40 requests per 10 seconds)
- **Claude API**: ~$0.02 per recommendation
- **Monthly usage**: ~$6/month for moderate use (10 requests/day)

## Troubleshooting

### "Movie not found in TMDB"
- Some movies from Letterboxd may not match TMDB's database
- The app will skip these and continue with matched movies
- Need at least 5 matched movies to generate recommendations

### "Unable to access Letterboxd list"
- Make sure the list is **public** (not private)
- Check the URL format: `letterboxd.com/username/list/listname/`
- Ensure the list exists and hasn't been deleted

### "API Key Invalid"
- Check that you've correctly copied your API keys to `.env`
- Ensure there are no extra spaces or quotes
- For Anthropic, verify you have credits in your account

### Slow Response Times
- Large lists (100+ movies) take longer to process
- First request is slower (no cache)
- Check your internet connection

## Future Enhancements

See PROJECT_PLAN.md for detailed roadmap, including:
- Ratings/reviews integration
- Explanation for each recommendation
- Streaming availability integration
- User accounts and history
- Recommendation filters and modes

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues, questions, or feedback, please open a GitHub issue.
