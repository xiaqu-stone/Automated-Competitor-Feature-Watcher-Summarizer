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
from bs4 import BeautifulSoup

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
    'end_time': None,
    'article_metadata': {}  # Store article info by URL
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
            result = get_article_urls(BASE_URL, ARTICLE_LINK_SELECTOR)
            
            # Handle both old and new function signatures
            if isinstance(result, tuple):
                all_urls, articles = result
                # Store article metadata
                for article in articles:
                    app_state['article_metadata'][article['url']] = article
            else:
                # Fallback for old signature
                all_urls = result
                articles = []
            
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

def get_article_urls(base_url, selector, limit=10):
    """获取Grab最新文章列表，包含标题、URL、发布日期等信息"""
    
    try:
        print("🔍 Fetching latest articles from Grab...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找所有文章链接
        blog_links = soup.find_all('a', class_='blogHyperlink')
        print(f"Found {len(blog_links)} article links on press page.")
        
        articles = []
        valid_articles = 0
        
        for link in blog_links:
            if valid_articles >= limit:
                break
                
            try:
                # 获取URL
                article_url = link.get('href')
                if not article_url or article_url == '#':
                    continue
                    
                # 获取文章容器
                article_panel = link.find('article', class_=lambda x: x and 'panel-article' in str(x))
                if not article_panel:
                    continue
                
                # 获取标题
                title_elem = article_panel.find('h2')
                if not title_elem:
                    title_elem = article_panel.find(['h1', 'h3', 'h4', 'h5'])
                
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                # 获取发布日期
                date_elem = article_panel.find(class_='post-date')
                publish_date = None
                original_date_text = ""
                
                if date_elem:
                    original_date_text = date_elem.get_text(strip=True)
                    # 解析日期格式 "11 Jun 2025" 或其他格式
                    try:
                        # 尝试多种日期格式
                        for fmt in ["%d %b %Y", "%B %d, %Y", "%d %B %Y"]:
                            try:
                                publish_date = datetime.strptime(original_date_text, fmt)
                                break
                            except:
                                continue
                        
                        if not publish_date:
                            # 如果无法解析，使用当前时间作为默认值
                            publish_date = datetime.now()
                    except:
                        publish_date = datetime.now()
                else:
                    publish_date = datetime.now()
                
                # 获取分类
                cat_elem = article_panel.find(class_='post-cat')
                category = "Others"
                if cat_elem:
                    category = cat_elem.get_text(strip=True).replace('**', '').strip()
                
                # 获取描述
                description = ""
                desc_p = article_panel.find('p')
                if desc_p:
                    description = desc_p.get_text(strip=True)
                
                article_info = {
                    'url': article_url,
                    'title': title,
                    'publish_date': publish_date,
                    'original_date_text': original_date_text,
                    'description': description,
                    'category': category,
                    'source': 'grab'
                }
                
                articles.append(article_info)
                valid_articles += 1
                print(f"  ✓ {valid_articles:2d}. {title[:50]}... ({original_date_text})")
                
            except Exception as e:
                print(f"  ❌ Error processing article: {e}")
                continue
        
        if articles:
            # 按发布日期排序（最新的在前）
            articles.sort(key=lambda x: x['publish_date'], reverse=True)
            print(f"Successfully fetched {len(articles)} articles, sorted by date (newest first)")
            return [article['url'] for article in articles], articles
        else:
            print("⚠️  No valid articles found, falling back to demo mode")
            return get_demo_article_urls()
            
    except Exception as e:
        print(f"❌ Failed to fetch latest articles: {e}")
        print("⚠️  Falling back to demo mode with hardcoded articles")
        return get_demo_article_urls()

def get_demo_article_urls():
    """获取演示用的硬编码文章URL列表（备用方案）"""
    print("Fetching hardcoded article links for demo...")
    
    demo_articles = [
        {
            'url': 'https://www.grab.com/sg/press/others/grab-prices-upsized-1-5-billion-convertible-notes-offering/',
            'title': 'Grab Prices Upsized $1.5 Billion Convertible Notes Offering',
            'publish_date': datetime(2025, 6, 11),
            'original_date_text': '11 Jun 2025',
            'category': 'Others',
            'description': 'Grab today announced the pricing of an upsized offering of $1.5 billion aggregate principal amount of zero coupon convertible senior notes due 2030',
            'source': 'grab'
        },
        {
            'url': 'https://www.grab.com/sg/press/others/grab-announces-proposed-offering-of-convertible-notes/',
            'title': 'Grab Announces Proposed Offering of Convertible Notes',
            'publish_date': datetime(2025, 6, 10),
            'original_date_text': '10 Jun 2025',
            'category': 'Others',
            'description': 'Grab proposes to offer US$1,250,000,000 in aggregate principal amount of convertible senior notes due 2030',
            'source': 'grab'
        },
        {
            'url': 'https://www.grab.com/sg/press/others/grab-launches-first-artificial-intelligence-centre-of-excellence-with-support-from-digital-industry-singapore/',
            'title': 'Grab Launches First Artificial Intelligence Centre of Excellence',
            'publish_date': datetime(2025, 5, 23),
            'original_date_text': '23 May 2025',
            'category': 'Others',
            'description': 'Centre aims to push the boundaries of AI innovation to improve accessibility; productivity and growth',
            'source': 'grab'
        },
        {
            'url': 'https://www.grab.com/sg/press/others/grab-announces-leadership-appointments-in-singapore-and-vietnam/',
            'title': 'Grab Announces Leadership Appointments in Singapore and Vietnam',
            'publish_date': datetime(2025, 5, 5),
            'original_date_text': '5 May 2025',
            'category': 'Others',
            'description': 'Alejandro Osorio appointed as Managing Director of Grab Singapore',
            'source': 'grab'
        }
    ]
    
    urls = [article['url'] for article in demo_articles]
    print(f"Found {len(urls)} article links (from mock data).")
    return urls, demo_articles

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