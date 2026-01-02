# Complete Python Web Development & AI Integration Course
## Based on the Letterboxd Movie Recommender Project

**Course Philosophy**: Learn by building. Each lesson builds on previous concepts using the movie recommender as a living example.

---

## 📚 COURSE OUTLINE

### **MODULE 1: Python Foundations** (Lessons 1-8)
*Start here if you're new to Python or need a refresher*

- **Lesson 1**: Python Basics - Variables, Types, and Basic Operations
  - Example: Understanding `title`, `year`, `rating` in our movie dictionaries
  
- **Lesson 2**: Data Structures - Lists, Dictionaries, and Sets
  - Example: How we store movies as `List[Dict[str, Any]]`
  
- **Lesson 3**: Functions - Definition, Parameters, Return Values
  - Example: Breaking down `search_movie()` and `enrich_movie()`
  
- **Lesson 4**: Type Hints and Optional Values
  - Example: `Optional[str] = None` in our function signatures
  
- **Lesson 5**: Classes and Object-Oriented Programming
  - Example: The `TMDBClient` and `MovieRecommender` classes
  
- **Lesson 6**: Exception Handling - Try/Except/Finally
  - Example: Custom exceptions like `TMDBError`, `RecommenderError`
  
- **Lesson 7**: File I/O and Path Handling
  - Example: Reading `.env` files and handling file paths
  
- **Lesson 8**: Python Modules and Imports
  - Example: How `modules/` folder structure works

---

### **MODULE 2: Working with External Data** (Lessons 9-14)

- **Lesson 9**: HTTP Basics - Understanding Web Requests
  - Example: What happens when we call TMDB API
  
- **Lesson 10**: The `requests` Library - Making HTTP Calls
  - Example: `self.session.get(url, params=params)`
  
- **Lesson 11**: JSON - Parsing and Creating JSON Data
  - Example: TMDB API responses and Claude's JSON output
  
- **Lesson 12**: HTML Structure and the DOM
  - Example: Letterboxd's `<li class="posteritem">` structure
  
- **Lesson 13**: Web Scraping with BeautifulSoup
  - Example: Extracting movies from Letterboxd lists
  
- **Lesson 14**: Regular Expressions (Regex)
  - Example: Parsing "Movie Title (YEAR)" format

---

### **MODULE 3: API Integration Patterns** (Lessons 15-20)

- **Lesson 15**: REST APIs - Concepts and Conventions
  - Example: TMDB API endpoints structure
  
- **Lesson 16**: API Authentication and Keys
  - Example: Managing `TMDB_API_KEY` and `ANTHROPIC_API_KEY`
  
- **Lesson 17**: Rate Limiting and Throttling
  - Example: `_wait_for_rate_limit()` implementation
  
- **Lesson 18**: Retry Logic with Tenacity
  - Example: The `@retry` decorator on `_make_request()`
  
- **Lesson 19**: Caching Strategies
  - Example: In-memory cache in `TMDBClient`
  
- **Lesson 20**: API Error Handling
  - Example: Handling 401, 404, 429 status codes

---

### **MODULE 4: Application Architecture** (Lessons 21-26)

- **Lesson 21**: Separation of Concerns
  - Example: Scraper → TMDB Client → Recommender → App
  
- **Lesson 22**: Configuration Management
  - Example: The `Config` class and environment variables
  
- **Lesson 23**: The Pipeline Pattern
  - Example: Scrape → Enrich → Build Candidates → Recommend
  
- **Lesson 24**: Data Enrichment Strategies
  - Example: Adding TMDB metadata to scraped movies
  
- **Lesson 25**: Candidate Pool Architecture
  - Example: Why we build candidates first, then analyze
  
- **Lesson 26**: Error Propagation and User-Friendly Messages
  - Example: Converting exceptions to readable error pages

---

### **MODULE 5: Web Development with FastAPI** (Lessons 27-33)

- **Lesson 27**: FastAPI Basics - Routes and Responses
  - Example: `@app.get("/")` and `@app.post("/recommend")`
  
- **Lesson 28**: HTML Templates with Jinja2
  - Example: Rendering `index.html` with dynamic data
  
- **Lesson 29**: Form Handling - Form Data and Validation
  - Example: `letterboxd_url: str = Form(...)`
  
- **Lesson 30**: Static Files - CSS and JavaScript
  - Example: Serving `/static/style.css`
  
- **Lesson 31**: Request/Response Cycle
  - Example: Following a recommendation request through the app
  
- **Lesson 32**: Error Pages and User Experience
  - Example: The `error.html` template with progress tracking
  
- **Lesson 33**: Async vs Sync in FastAPI
  - Example: When to use `async def` vs `def`

---

### **MODULE 6: Frontend Essentials** (Lessons 34-37)

- **Lesson 34**: HTML Structure and Semantic Markup
  - Example: Form structure in `index.html`
  
- **Lesson 35**: CSS Styling - Layout and Design
  - Example: Grid layout for movie cards
  
- **Lesson 36**: JavaScript Basics - DOM Manipulation
  - Example: Loading spinner and form validation in `script.js`
  
- **Lesson 37**: Responsive Design Principles
  - Example: Mobile-friendly movie grid

---

### **MODULE 7: AI/LLM Integration** (Lessons 38-44)

- **Lesson 38**: Understanding Large Language Models
  - Example: Claude Haiku vs Sonnet - choosing the right model
  
- **Lesson 39**: Prompt Engineering Fundamentals
  - Example: The structure of our recommendation prompt
  
- **Lesson 40**: Structured Output with JSON Mode
  - Example: Getting Claude to return valid JSON
  
- **Lesson 41**: Context Window Management
  - Example: Compact movie formatting to fit more data
  
- **Lesson 42**: Data-Driven vs Knowledge-Driven AI
  - Example: Why we use candidate pools instead of LLM memory
  
- **Lesson 43**: User Preference Integration
  - Example: Incorporating natural language preferences
  
- **Lesson 44**: Temperature and Model Parameters
  - Example: `temperature=1.0` for creative recommendations

---

### **MODULE 8: Advanced Patterns** (Lessons 45-50)

- **Lesson 45**: Defensive Programming
  - Example: Checking `if not scraped_movies:` before proceeding
  
- **Lesson 46**: Data Validation and Sanitization
  - Example: Validating URLs and handling edge cases
  
- **Lesson 47**: Progress Tracking and User Feedback
  - Example: `show_progress` parameter and step_completed tracking
  
- **Lesson 48**: Performance Optimization
  - Example: Session pooling with `requests.Session()`
  
- **Lesson 49**: Debugging Strategies
  - Example: Print statements and traceback analysis
  
- **Lesson 50**: Testing Your Code
  - Example: How to write tests for each module

---

### **MODULE 9: Real-World Considerations** (Lessons 51-55)

- **Lesson 51**: Environment Variables and Security
  - Example: Never commit `.env` files
  
- **Lesson 52**: API Cost Management
  - Example: Understanding Claude API pricing
  
- **Lesson 53**: Scalability Considerations
  - Example: When in-memory cache isn't enough
  
- **Lesson 54**: Deployment Basics
  - Example: Running the app with Uvicorn
  
- **Lesson 55**: Monitoring and Logging
  - Example: Console output and error tracking

---

### **MODULE 10: Project Deep Dives** (Lessons 56-60)

- **Lesson 56**: Code Reading Exercise - `letterboxd_scraper.py`
  - Line-by-line walkthrough with exercises
  
- **Lesson 57**: Code Reading Exercise - `tmdb_client.py`
  - Understanding the full client architecture
  
- **Lesson 58**: Code Reading Exercise - `recommender_v2.py`
  - How the AI recommendation engine works
  
- **Lesson 59**: Code Reading Exercise - `app.py`
  - The complete request lifecycle
  
- **Lesson 60**: Final Project - Build Your Own Variation
  - Ideas: Book recommender, Music recommender, etc.

---

## 📖 How to Use This Course

### For Complete Beginners:
Start with **Module 1** and work through sequentially. Each lesson includes:
- **Concept Explanation**: Theory and background
- **Code Examples**: From our project
- **Hands-On Exercise**: Practice what you learned
- **Common Pitfalls**: What to avoid
- **Challenge**: Optional advanced exercise

### For Intermediate Developers:
Skip to modules that interest you, but scan earlier modules for project-specific patterns.

### For Advanced Developers:
Focus on **Modules 7-10** for AI integration patterns and architecture deep dives.

---

## 🎯 Learning Outcomes

By completing this course, you will be able to:

1. ✅ Build full-stack web applications with Python and FastAPI
2. ✅ Integrate external APIs (REST, authentication, error handling)
3. ✅ Scrape and parse web data responsibly
4. ✅ Design data pipelines with multiple stages
5. ✅ Integrate AI/LLMs into applications effectively
6. ✅ Write maintainable, well-structured Python code
7. ✅ Handle errors gracefully and provide good UX
8. ✅ Understand modern web development patterns
9. ✅ Deploy and manage real-world applications
10. ✅ Read and understand other people's code

---

## 📝 Assessment Checkpoints

- **After Module 2**: Build a simple web scraper
- **After Module 3**: Integrate a public API (weather, news, etc.)
- **After Module 5**: Create a basic FastAPI application
- **After Module 7**: Build an AI-powered feature
- **After Module 10**: Complete the final project

---

## 💡 Next Steps

Ready to start? Ask me to generate:
```
"Generate Lesson 1: Python Basics"
```

Or jump to any lesson:
```
"Generate Lesson 27: FastAPI Basics"
```

Each lesson will be saved as a separate file in this folder for easy reference.

---

**Note**: This course is designed to be completed over 60-90 hours of study. Take your time, practice with each exercise, and reference the actual project code as you learn.

**Last Updated**: December 2025
**Project Version**: 1.0.0
