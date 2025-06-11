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
import re

# Configure proxy settings
def setup_proxy():
    """Configure proxy for network requests"""
    # Check if proxy is already configured via environment
    if os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
        print(f"🌐 Using existing proxy configuration: {os.environ.get('HTTP_PROXY', os.environ.get('http_proxy'))}")
        return
    
    # Default proxy settings - commonly used proxy ports
    # You can modify these settings according to your proxy configuration
    proxy_host = os.environ.get('PROXY_HOST', '127.0.0.1')
    proxy_port = os.environ.get('PROXY_PORT', '7890')
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    
    proxy_settings = {
        'http': proxy_url,
        'https': proxy_url,
    }
    
    # Set proxy for requests library and other libraries
    os.environ['HTTP_PROXY'] = proxy_settings['http']
    os.environ['HTTPS_PROXY'] = proxy_settings['https']
    os.environ['http_proxy'] = proxy_settings['http']
    os.environ['https_proxy'] = proxy_settings['https']
    
    print(f"🌐 Proxy configured: {proxy_url}")
    print(f"💡 You can customize proxy by setting PROXY_HOST and PROXY_PORT environment variables")
    return proxy_settings

# Setup proxy before importing MVP logic
setup_proxy()

# Import our existing MVP logic
from mvp_demo import (
    load_processed_urls, save_processed_url, get_article_urls,
    get_article_text, analyze_text, display_results,
    CACHE_FILE, BASE_URL, ARTICLE_LINK_SELECTOR
)

app = Flask(__name__)

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
        self.original_stdout = sys.stdout  # Save original stdout
    
    def write(self, text):
        if text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {text.strip()}"
            self.logs.append(log_entry)
            log_queue.put(log_entry)
            # Print to original console (not captured stdout)
            self.original_stdout.write(f"{log_entry}\n")
            self.original_stdout.flush()
    
    def flush(self):
        pass

def parse_analysis_result(analysis_text, url):
    """Parse the raw Gemini analysis text into structured data for the template"""
    
    result = {
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'analysis': analysis_text,
        'title': 'Feature Analysis',
        'summary': '',
        'is_new_feature': False,
        'category': 'Unknown',
        'source': 'grab',
        'key_features': [],
        'relevance_score': 0
    }
    
    try:
        lines = analysis_text.split('\n')
        
        # Extract key information from the analysis
        for line in lines:
            line = line.strip()
            
            # Extract feature name/title
            if 'feature/product name:' in line.lower():
                title = line.split(':', 1)[1].strip()
                if title and title != '[Name if applicable]':
                    result['title'] = title
            
            # Extract category
            elif 'category:' in line.lower():
                category = line.split(':', 1)[1].strip()
                if category and not category.startswith('['):
                    result['category'] = category
            
            # Check if it's a new feature
            elif 'is this announcing a new feature' in line.lower():
                result['is_new_feature'] = 'yes' in line.lower()
            
            # Extract relevance score
            elif 'relevance score:' in line.lower():
                try:
                    score_text = line.split(':', 1)[1].strip()
                    # Extract numeric part
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        result['relevance_score'] = int(score_match.group(1))
                except:
                    pass
        
        # Extract summary from SUMMARY section
        summary_start = analysis_text.find('**SUMMARY:**')
        if summary_start != -1:
            summary_section = analysis_text[summary_start:]
            summary_end = summary_section.find('**COMPETITIVE INTELLIGENCE:**')
            if summary_end != -1:
                summary_text = summary_section[len('**SUMMARY:**'):summary_end].strip()
                result['summary'] = summary_text
            else:
                # If no competitive intelligence section, take until next ** section
                lines_after_summary = summary_section.split('\n')[1:]  # Skip the SUMMARY line
                summary_lines = []
                for line in lines_after_summary:
                    if line.strip().startswith('**') and line.strip().endswith('**'):
                        break
                    summary_lines.append(line)
                result['summary'] = '\n'.join(summary_lines).strip()
        
        # If no summary found, create one from the analysis
        if not result['summary']:
            # Take first few lines that aren't headers
            content_lines = []
            for line in lines:
                if line.strip() and not line.strip().startswith('**') and not line.strip().startswith('-'):
                    content_lines.append(line.strip())
                    if len(' '.join(content_lines)) > 200:
                        break
            result['summary'] = ' '.join(content_lines)[:300]
        
        # Extract key features (simple heuristic)
        if result['is_new_feature']:
            # Look for bullet points or key feature mentions
            feature_keywords = ['feature', 'functionality', 'service', 'capability', 'option']
            for line in lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in feature_keywords) and len(line.strip()) > 10:
                    result['key_features'].append(line.strip()[:100])
                    if len(result['key_features']) >= 3:
                        break
        
        # Determine source from URL
        if 'grab.com' in url:
            result['source'] = 'grab'
        elif 'foodpanda' in url:
            result['source'] = 'foodpanda'
        elif 'deliveroo' in url:
            result['source'] = 'deliveroo'
        
    except Exception as e:
        print(f"  ⚠️  Error parsing analysis: {e}")
    
    return result

def run_analysis_task():
    """Background task to run the ACFWS analysis"""
    global app_state
    
    try:
        app_state['status'] = 'running'
        app_state['start_time'] = datetime.now()
        app_state['current_task'] = 'Initializing analysis task...'
        
        # Capture stdout to get script output
        log_capture = LogCapture()
        
        with redirect_stdout(log_capture):
            print("🚀 Starting competitor feature analysis...")
            
            # Load processed URLs
            print("📂 Loading processed article cache...")
            processed_urls = load_processed_urls(CACHE_FILE)
            app_state['current_task'] = 'Cache loaded'
            
            # Get article URLs
            print("🔍 Getting article URL list...")
            all_urls = get_article_urls(BASE_URL, ARTICLE_LINK_SELECTOR)
            app_state['total_articles'] = len(all_urls)
            app_state['current_task'] = f'Found {len(all_urls)} articles'
            
            # Filter new URLs
            new_urls = [url for url in all_urls if url not in processed_urls]
            print(f"📊 Found {len(new_urls)} new articles to analyze")
            
            if not new_urls:
                print("✅ All articles already analyzed, no reprocessing needed")
                app_state['status'] = 'completed'
                app_state['end_time'] = datetime.now()
                return
            
            # Process each new article
            results = []
            for i, url in enumerate(new_urls):
                app_state['current_task'] = f'Analyzing article {i+1}/{len(new_urls)}'
                
                print(f"\n📖 Processing article {i+1}/{len(new_urls)}: {url}")
                
                # Get article content
                print("  🔄 Getting article content...")
                article_text = get_article_text(url)
                
                if article_text and len(article_text.strip()) > 100:
                    print("  🤖 Using AI to analyze content...")
                    analysis = analyze_text(article_text)
                    
                    if analysis and not analysis.startswith("ERROR:"):
                        # Parse the analysis to extract structured data
                        parsed_result = parse_analysis_result(analysis, url)
                        results.append(parsed_result)
                        
                        # Display results (this will be captured in logs)
                        display_results(analysis, url)
                        
                        # Save to cache
                        save_processed_url(CACHE_FILE, url)
                        print(f"  ✅ Article analysis completed and saved to cache")
                    else:
                        print(f"  ❌ AI analysis failed: {analysis}")
                else:
                    print(f"  ⚠️  Article content retrieval failed or content too short")
                
                # Update progress after processing each article
                app_state['processed_articles'] = i + 1  # Show completed articles (1-based)
                app_state['progress'] = int(((i + 1) / len(new_urls)) * 100)
                
                time.sleep(0.5)  # Small delay for demo effect
            
            app_state['results'] = results
            app_state['processed_articles'] = len(new_urls)
            app_state['progress'] = 100
            app_state['status'] = 'completed'
            app_state['end_time'] = datetime.now()
            
            print(f"\n🎉 Analysis completed! Processed {len(new_urls)} articles, found {len(results)} analysis results")
            
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
    thread = threading.Thread(target=run_analysis_task)
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
                # Get log from queue with timeout
                log = log_queue.get(timeout=1)
                yield f"data: {json.dumps({'log': log})}\n\n"
            except queue.Empty:
                # Send heartbeat
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                
                # If analysis is complete, stop streaming
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
    
    # Find available port starting from 8080
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