import requests
from bs4 import BeautifulSoup
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Constants ---
# Configuration
COMPETITOR_NAME = "Grab"
BASE_URL = "https://www.grab.com/sg/press/"
CACHE_FILE = f"{COMPETITOR_NAME.lower()}_articles.txt"

# Gemini API Configuration
# Note: Create a .env file with GEMINI_API_KEY=your_api_key_here
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")
    print("Please create a .env file with GEMINI_API_KEY=your_api_key_here")
    print("Get your API key from: https://makersuite.google.com/app/apikey")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# This selector will need to be verified and is likely to change.
# Based on a quick inspection, this seems to be a good starting point.
ARTICLE_LINK_SELECTOR = "div.elementor-post__text > h3 > a"

# Core Analysis Prompt for Gemini
ANALYSIS_PROMPT = """
You are an expert product analyst focused on identifying new features and product releases from competitor announcements.

Please analyze the following article text and provide a structured analysis:

ARTICLE TEXT:
{article_text}

Please provide your analysis in the following format:

**FEATURE ANALYSIS:**
- Is this announcing a new feature or product? (Yes/No)
- Feature/Product Name: [Name if applicable]
- Category: [e.g., Food Delivery, Transportation, Payments, etc.]
- Target Market: [e.g., Singapore, Malaysia, Southeast Asia]

**SUMMARY:**
[2-3 sentence summary of what this announcement contains]

**COMPETITIVE INTELLIGENCE:**
[Key insights about what this means for competitors in the market]

**RELEVANCE SCORE:** [1-10, where 10 is highly relevant new feature announcement]

Only respond with the structured analysis above. Be concise but thorough.""" 

def get_article_urls(url: str, selector: str):
    """
    [MVP PIVOT] Fetches a hardcoded list of article URLs for the demo.
    Direct scraping of the target site is proving difficult due to anti-scraping
    measures, so we are simulating this step to focus on the core summarization logic.

    Args:
        url: The URL of the main blog/news page (unused in this version).
        selector: The CSS selector (unused in this version).

    Returns:
        A hardcoded list of absolute URLs to articles.
    """
    print("Fetching hardcoded article links for demo...")
    
    # In a real-world scenario, this is where the robust scraping logic would be.
    # For the MVP, we are using a static list to ensure the demo is runnable.
    mock_urls = [
        "https://www.grab.com/sg/press/others/grab-introduces-grabfood-dine-in-beta/",
        "https://www.grab.com/sg/press/others/grab-reports-fourth-quarter-and-full-year-2024-results/",
        "https://www.grab.com/sg/press/consumers/grabshares-new-data-insights-on-e-hailing-and-food-delivery-trends-in-malaysia/",
        "https://www.grab.com/sg/press/others/grab-and-starbucks-expand-partnership-across-southeast-asia/"
    ]
    
    print(f"Found {len(mock_urls)} article links (from mock data).")
    return mock_urls

def load_processed_urls(cache_file: str) -> set:
    """Loads processed URLs from the cache file to a set."""
    try:
        if not os.path.exists(cache_file):
            return set()
        with open(cache_file, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"Warning: Could not load cache file {cache_file}: {e}")
        return set()

def save_processed_url(cache_file: str, url: str):
    """Appends a new URL to the cache file."""
    try:
        with open(cache_file, 'a') as f:
            f.write(url + '\\n')
    except Exception as e:
        print(f"Warning: Could not save to cache file {cache_file}: {e}")

def get_article_text(url: str) -> str:
    """
    Fetches the content of a single article and extracts the text.
    """
    print(f"  - Fetching content for {url}...")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # A simple approach to get the main content. This can be improved.
        # We target common tags where article text resides.
        article_body = soup.find('div', class_='entry-content') # A common class for content
        if not article_body:
             article_body = soup.find('article') or soup.find('main')

        if article_body:
            text_parts = article_body.find_all(['p', 'h1', 'h2', 'h3', 'li'])
            return ' '.join(part.get_text(separator=' ', strip=True) for part in text_parts)
        else:
            print(f"  - Could not find main article body for {url}. Falling back to body text.")
            return soup.body.get_text(separator=' ', strip=True)

    except requests.RequestException as e:
        print(f"  - Error fetching article content for {url}: {e}")
        return ""

def analyze_text(article_text: str) -> str:
    """
    Analyzes article text using Gemini API to identify new features and competitive intelligence.
    
    Args:
        article_text: The cleaned text content of the article
        
    Returns:
        The analysis results from Gemini, or an error message
    """
    if not GEMINI_API_KEY:
        return "ERROR: Gemini API key not configured"
    
    if not article_text.strip():
        return "ERROR: No article text provided"
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Format the prompt with the article text
        formatted_prompt = ANALYSIS_PROMPT.format(article_text=article_text[:4000])  # Limit text to avoid token limits
        
        print(f"  - Sending to Gemini for analysis...")
        
        # Generate analysis
        response = model.generate_content(formatted_prompt)
        
        if response.text:
            print(f"  - Analysis completed successfully")
            return response.text
        else:
            return "ERROR: Empty response from Gemini"
            
    except Exception as e:
        print(f"  - Error during Gemini analysis: {e}")
        return f"ERROR: Gemini analysis failed - {str(e)}"

def display_results(analysis: str, url: str) -> None:
    """
    Displays the analysis results in a formatted way and identifies key feature announcements.
    
    Args:
        analysis: The analysis text from Gemini
        url: The source URL
    """
    if analysis.startswith("ERROR:"):
        print(f"  - {analysis}")
        return
    
    print(f"\\n=== ANALYSIS RESULTS ===")
    print(f"Source: {url}")
    print("-" * 50)
    print(analysis)
    print("-" * 50)
    
    # Check if this is a significant feature announcement
    analysis_lower = analysis.lower()
    
    # Look for indicators of new features
    if "yes" in analysis_lower and any(keyword in analysis_lower for keyword in 
                                     ["new feature", "product launch", "announcing", "introduces", "launches"]):
        
        # Try to extract feature name from the analysis
        lines = analysis.split('\\n')
        feature_name = "Unknown Feature"
        for line in lines:
            if "feature/product name:" in line.lower():
                feature_name = line.split(':', 1)[1].strip()
                break
        
        print(f"\\n🚀 NEW FEATURE DETECTED: {feature_name}")
        print(f"📄 Source: {url}")
        print("⚠️  This requires competitive intelligence review!")
        print("=" * 60)

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Competitor Feature Watcher MVP ---")

    processed_urls = load_processed_urls(CACHE_FILE)
    print(f"Loaded {len(processed_urls)} processed URLs from cache.")
    
    all_urls = get_article_urls(BASE_URL, ARTICLE_LINK_SELECTOR)
    
    new_urls = [url for url in all_urls if url not in processed_urls]
    
    if not new_urls:
        print("\\n--- No new articles found. ---")
    else:
        print(f"\\n--- Found {len(new_urls)} new articles to process ---")
        for url in new_urls:
            print(f"Processing new article: {url}")
            
            # Save to cache immediately to avoid reprocessing failed URLs in the MVP
            save_processed_url(CACHE_FILE, url)
            print(f"  - Marked as processed and saved to cache.")

            article_text = get_article_text(url)
            
            if article_text:
                print(f"  - Successfully extracted text. Length: {len(article_text)} chars.")
                
                # Analyze with Gemini
                analysis = analyze_text(article_text)
                
                # Display results using the formatted display function
                display_results(analysis, url)
            else:
                print(f"  - Failed to extract text.")

    print("\\n--- MVP script finished ---") 