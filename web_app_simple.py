from flask import Flask, render_template, jsonify, request, Response
import threading
import queue
import time
import json
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
COMPETITOR_NAME = "Grab"
BASE_URL = "https://www.grab.com/sg/press/"
CACHE_FILE = f"{COMPETITOR_NAME.lower()}_articles.txt"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Analysis prompt
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

# Global state management
app_state = {
    'status': 'ready',  # ready, running, completed, error
    'progress': 0,
    'total_articles': 0,
    'processed_articles': 0,
    'current_task': '',
    'results': [],
    'logs': [],
    'start_time': None,
    'end_time': None
}

# Thread-safe queue for real-time logs
log_queue = queue.Queue()

class LogCapture:
    """Capture print statements and send to web interface"""
    def __init__(self):
        self.logs = []
    
    def write(self, text):
        if text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {text.strip()}"
            self.logs.append(log_entry)
            log_queue.put(log_entry)
            print(text, end='')  # Also print to console
    
    def flush(self):
        pass

def get_mock_article_urls():
    """Get hardcoded article URLs for demo"""
    mock_urls = [
        "https://www.grab.com/sg/press/others/grab-introduces-grabfood-dine-in-beta/",
        "https://www.grab.com/sg/press/others/grab-reports-fourth-quarter-and-full-year-2024-results/",
        "https://www.grab.com/sg/press/consumers/grabshares-new-data-insights-on-e-hailing-and-food-delivery-trends-in-malaysia/",
        "https://www.grab.com/sg/press/others/grab-and-starbucks-expand-partnership-across-southeast-asia/"
    ]
    return mock_urls

def load_processed_urls_simple():
    """Load processed URLs from cache file"""
    try:
        if not os.path.exists(CACHE_FILE):
            return set()
        with open(CACHE_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"Warning: Could not load cache file: {e}")
        return set()

def save_processed_url_simple(url):
    """Save URL to cache file"""
    try:
        with open(CACHE_FILE, 'a') as f:
            f.write(url + '\n')
    except Exception as e:
        print(f"Warning: Could not save to cache file: {e}")

def get_article_text_simple(url):
    """Get article text content"""
    print(f"  - Fetching content for {url}...")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find main content
        article_body = soup.find('div', class_='entry-content')
        if not article_body:
            article_body = soup.find('article') or soup.find('main')

        if article_body:
            text_parts = article_body.find_all(['p', 'h1', 'h2', 'h3', 'li'])
            return ' '.join(part.get_text(separator=' ', strip=True) for part in text_parts)
        else:
            return soup.body.get_text(separator=' ', strip=True)

    except Exception as e:
        print(f"  - Error fetching article content: {e}")
        return ""

def analyze_text_simple(article_text):
    """Analyze article text using Gemini API"""
    if not GEMINI_API_KEY:
        return "ERROR: Gemini API key not configured"
    
    if not article_text.strip():
        return "ERROR: No article text provided"
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        formatted_prompt = ANALYSIS_PROMPT.format(article_text=article_text[:4000])
        
        print(f"  - Sending to Gemini for analysis...")
        response = model.generate_content(formatted_prompt)
        
        if response.text:
            print(f"  - Analysis completed successfully")
            return response.text
        else:
            return "ERROR: Empty response from Gemini"
            
    except Exception as e:
        print(f"  - Error during Gemini analysis: {e}")
        return f"ERROR: Gemini analysis failed - {str(e)}"

def run_simple_analysis():
    """Simplified analysis task"""
    global app_state
    
    try:
        app_state['status'] = 'running'
        app_state['start_time'] = datetime.now()
        app_state['current_task'] = 'Starting analysis...'
        
        log_capture = LogCapture()
        
        with redirect_stdout(log_capture):
            print("🚀 Starting competitor feature analysis...")
            time.sleep(1)
            
            print("📂 Loading processed article cache...")
            app_state['current_task'] = 'Cache loaded'
            time.sleep(1)
            
            print("🔍 Getting article URL list...")
            app_state['total_articles'] = 4
            app_state['current_task'] = 'Found 4 articles'
            time.sleep(1)
            
            # Simulate processing articles
            for i in range(4):
                app_state['processed_articles'] = i
                app_state['progress'] = int((i / 4) * 100)
                app_state['current_task'] = f'Analyzing article {i+1}/4'
                
                print(f"\n📖 Processing article {i+1}/4...")
                print("  🔄 Getting article content...")
                time.sleep(1)
                print("  🤖 Using AI to analyze content...")
                time.sleep(2)
                
                # Mock result
                result = {
                    'url': f'https://example.com/article-{i+1}',
                    'analysis': f'Mock analysis result for article {i+1}',
                    'timestamp': datetime.now().isoformat()
                }
                app_state['results'].append(result)
                
                print(f"  ✅ Article analysis completed")
            
            app_state['processed_articles'] = 4
            app_state['progress'] = 100
            app_state['status'] = 'completed'
            app_state['end_time'] = datetime.now()
            
            print(f"\n🎉 Analysis completed! Processed 4 articles")
            
    except Exception as e:
        app_state['status'] = 'error'
        app_state['current_task'] = f'Error: {str(e)}'
        app_state['end_time'] = datetime.now()
        print(f"❌ Error during analysis: {str(e)}")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', state=app_state)

@app.route('/start', methods=['POST'])
def start_analysis():
    """Start analysis task"""
    if app_state['status'] in ['running']:
        return jsonify({'error': 'Analysis is already running'}), 400
    
    # Reset state
    app_state.update({
        'status': 'ready',
        'progress': 0,
        'total_articles': 0,
        'processed_articles': 0,
        'current_task': '',
        'results': [],
        'logs': [],
        'start_time': None,
        'end_time': None
    })
    
    # Clear log queue
    while not log_queue.empty():
        log_queue.get()
    
    # Start background task
    thread = threading.Thread(target=run_simple_analysis)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Analysis task started'})

@app.route('/status')
def get_status():
    """Get current status"""
    return jsonify(app_state)

@app.route('/logs')
def stream_logs():
    """Real-time log stream"""
    def generate():
        while True:
            try:
                log = log_queue.get(timeout=1)
                yield f"data: {json.dumps({'log': log})}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                if app_state['status'] in ['completed', 'error']:
                    break
    
    return Response(generate(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache'})

@app.route('/monitor')
def monitor():
    """Monitor page"""
    return render_template('monitor.html', state=app_state)

@app.route('/results')
def results():
    """Results page"""
    return render_template('results.html', state=app_state)

if __name__ == '__main__':
    import socket
    
    def find_free_port(start_port=8080):
        for port in range(start_port, start_port + 100):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
        return None
    
    port = find_free_port()
    if port is None:
        print("❌ Unable to find available port")
        exit(1)
    
    print("🚀 ACFWS Web Demo starting...")
    print(f"📱 Please visit in browser: http://localhost:{port}")
    print("⭐ Tip: Use Ctrl+C to stop service")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n👋 Service stopped") 