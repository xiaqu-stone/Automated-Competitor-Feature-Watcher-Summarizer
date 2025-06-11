# ACFWS - Automated Competitor Feature Watcher & Summarizer (MVP)

A 6-hour MVP that monitors competitor announcements and uses Google Gemini to identify new feature releases.

## Quick Start

### 1. Install Dependencies
```bash
uv pip install -r requirements.txt
```

### 2. Setup Gemini API Key
Create a `.env` file in the project root:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

### 3. Run the Script
```bash
uv run python mvp_demo.py
```

## What It Does

1. **Simulates scraping** Grab's press releases (hardcoded URLs for MVP)
2. **Caches processed articles** to avoid re-processing
3. **Extracts article text** from web pages
4. **Analyzes with Gemini** to identify new features
5. **Highlights important findings** with special formatting

## Output Format

- Regular analysis results with structured competitive intelligence
- 🚀 **Special alerts** for detected new feature announcements
- Error handling for network issues and API failures

## Files

- `mvp_demo.py` - Main script
- `grab_articles.txt` - Cache of processed URLs
- `requirements.txt` - Python dependencies
- `.env` - API keys (create this yourself)

## MVP Limitations

- Only monitors Grab (Singapore)
- Uses hardcoded article URLs instead of dynamic scraping
- Text-based output only
- No database storage
- Single-run execution (no scheduling)

This is a 6-hour MVP focused on core functionality and demonstrating the concept. 