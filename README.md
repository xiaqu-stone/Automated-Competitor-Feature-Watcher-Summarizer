# ACFWS - Automated Competitor Feature Watcher & Summarizer

A competitive intelligence system that monitors competitor announcements and uses Google Gemini to identify new feature releases. Now with Web interface for easy team collaboration!

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

### 3. Choose Your Interface

#### Option A: Web Interface (Recommended)
```bash
python web_app.py
```
The app will automatically find an available port (starting from 8080) and display the URL.

**How to stop the web service:**
- Press `Ctrl+C` in the terminal where the service is running

#### Option B: Command Line
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

## Features

### 🌐 Web Interface
- **Real-time monitoring** - Watch script execution live
- **Beautiful dashboard** - Status, progress, and quick stats
- **Results visualization** - Card-based layout with filtering
- **Team collaboration** - Share results easily via web browser

### 🤖 AI Analysis
- **Gemini-powered** intelligent feature detection
- **Structured output** with competitive insights
- **Special alerts** for new feature announcements (🚀)
- **Context-aware** analysis of competitor updates

## Files

- `web_app.py` - Flask web application
- `mvp_demo.py` - Core analysis script
- `templates/` - Web interface templates
- `static/` - CSS and static assets
- `grab_articles.txt` - Cache of processed URLs
- `requirements.txt` - Python dependencies
- `.env` - API keys (create this yourself)
- `ENV_SETUP.md` - Environment setup guide

## MVP Limitations

- Only monitors Grab (Singapore)
- Uses hardcoded article URLs instead of dynamic scraping
- Text-based output only
- No database storage
- Single-run execution (no scheduling)

This is a 6-hour MVP focused on core functionality and demonstrating the concept. 