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

# Multi-Competitor Configuration
COMPETITORS = {
    'grab': {
        'name': 'Grab',
        'base_url': 'https://www.grab.com/sg/press/',
        'selector': 'div.elementor-post__text > h3 > a',
        'cache_file': 'grab_articles.txt',
        'color': 'success',
        'demo_articles': [
            {
                'url': 'https://www.grab.com/sg/press/others/grab-introduces-grabfood-dine-in-beta/',
                'title': 'Grab Introduces GrabFood Dine-in BETA',
                'publish_date': '2025-01-15T00:00:00',
                'category': 'Product Launch',
                'description': 'Grab launches new dine-in ordering feature for restaurants'
            },
            {
                'url': 'https://www.grab.com/sg/press/others/grab-reports-fourth-quarter-and-full-year-2024-results/',
                'title': 'Grab Reports Fourth Quarter and Full Year 2024 Results',
                'publish_date': '2025-01-10T00:00:00',
                'category': 'Financial Results',
                'description': 'Quarterly financial results and business updates'
            },
            {
                'url': 'https://www.grab.com/sg/press/consumers/grabshares-new-data-insights-on-e-hailing-and-food-delivery-trends-in-malaysia/',
                'title': 'GrabShares New Data Insights on E-hailing and Food Delivery Trends in Malaysia',
                'publish_date': '2025-01-08T00:00:00',
                'category': 'Market Insights',
                'description': 'Data insights on transportation and delivery trends'
            },
            {
                'url': 'https://www.grab.com/sg/press/others/grab-and-starbucks-expand-partnership-across-southeast-asia/',
                'title': 'Grab and Starbucks Expand Partnership Across Southeast Asia',
                'publish_date': '2025-01-05T00:00:00',
                'category': 'Partnership',
                'description': 'Strategic partnership expansion announcement'
            }
        ]
    },
    'foodme': {
        'name': 'FeedMe',
        'base_url': 'https://www.foodme.asia/news/',
        'selector': 'article.news-item h2 > a',
        'cache_file': 'foodme_articles.txt',
        'color': 'warning',
        'demo_articles': [
            {
                'url': 'https://www.foodme.asia/news/foodme-launches-ai-powered-restaurant-recommendations/',
                'title': 'FeedMe Launches AI-Powered Restaurant Recommendations',
                'publish_date': '2025-01-14T00:00:00',
                'category': 'AI Innovation',
                'description': 'New AI-driven recommendation engine for personalized dining experiences'
            },
            {
                'url': 'https://www.foodme.asia/news/foodme-introduces-premium-membership-program/',
                'title': 'FeedMe Introduces Premium Membership Program',
                'publish_date': '2025-01-12T00:00:00',
                'category': 'Product Launch',
                'description': 'New subscription service with exclusive restaurant access and benefits'
            },
            {
                'url': 'https://www.foodme.asia/news/foodme-expands-to-5-new-cities-in-southeast-asia/',
                'title': 'FeedMe Expands to 5 New Cities in Southeast Asia',
                'publish_date': '2025-01-09T00:00:00',
                'category': 'Expansion',
                'description': 'Market expansion into Thailand, Vietnam, and Philippines'
            },
            {
                'url': 'https://www.foodme.asia/news/foodme-partners-with-local-farmers-for-sustainable-dining/',
                'title': 'FeedMe Partners with Local Farmers for Sustainable Dining',
                'publish_date': '2025-01-06T00:00:00',
                'category': 'Sustainability',
                'description': 'Farm-to-table initiative supporting local agriculture'
            }
        ]
    },
    'square': {
        'name': 'Square POS',
        'base_url': 'https://squareup.com/us/en/press',
        'selector': 'a[href*="/press/"]',
        'cache_file': 'square_articles.txt',
        'color': 'info',
        'demo_articles': []  # No demo articles needed for live scraping
    }
}

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
    'article_metadata': {},  # Store article info by URL
    'selected_competitor': 'grab',  # Default competitor
    'available_competitors': list(COMPETITORS.keys())
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
    
    # Get current competitor information
    current_competitor = app_state.get('selected_competitor', 'grab')
    competitor_config = COMPETITORS.get(current_competitor, COMPETITORS['grab'])
    competitor_name = competitor_config['name']
    
    # Get article metadata (including original publish date)
    article_metadata = app_state.get('article_metadata', {}).get(url, {})
    original_publish_date = article_metadata.get('publish_date', '')
    
    result = {
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'original_publish_date': original_publish_date,  # Add original publish date
        'analysis': analysis_text,
        'title': article_metadata.get('title', 'Feature Analysis'),  # Use original title if available
        'summary': '',
        'is_new_feature': False,
        'category': article_metadata.get('category', 'Unknown'),  # Use original category if available
        'source': competitor_name,  # Dynamic source based on current competitor (maintain proper casing)
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
        
        # Note: Source is already dynamically set based on selected competitor above
        # This section is kept for any additional source-specific logic if needed
        
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
            
            # Get selected competitor configuration
            competitor_config = COMPETITORS[app_state['selected_competitor']]
            competitor_name = competitor_config['name']
            
            print(f"🔍 Getting article URL list for {competitor_name}...")
            
            # Try dynamic fetching for all competitors with real URLs, fallback to demo data
            if app_state['selected_competitor'] == 'grab':
                # Use Grab-specific function
                result = get_article_urls(competitor_config['base_url'], competitor_config['selector'])
                
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
                
            elif app_state['selected_competitor'] == 'square':
                # Use real-time scraping for Square POS
                print(f"🔍 Fetching real-time articles from {competitor_name}...")
                result = get_article_urls_generic(competitor_config['base_url'], competitor_config['selector'])
                
                if isinstance(result, tuple):
                    all_urls, articles = result
                    # Store article metadata
                    for article in articles:
                        app_state['article_metadata'][article['url']] = article
                else:
                    all_urls = result
                    articles = []
                
                print(f"✅ Found {len(all_urls)} real articles from {competitor_name}")
                
            else:
                # Use demo data for other competitors (FeedMe)
                demo_articles = competitor_config['demo_articles']
                all_urls = [article['url'] for article in demo_articles]
                for article in demo_articles:
                    app_state['article_metadata'][article['url']] = article
                articles = demo_articles
                print(f"Using demo data for {competitor_name} ({len(all_urls)} articles)")
            
            app_state['total_articles'] = len(all_urls)
            app_state['current_task'] = f'Found {len(all_urls)} articles from {competitor_name}'
            
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
                
                # Try mock content if real content failed (for demo purposes)
                if not article_text or len(article_text.strip()) < 100:
                    selected_competitor = app_state['selected_competitor']
                    mock_text = get_mock_content(selected_competitor, url)
                    if mock_text:
                        print(f"  📝 Using mock content for demo purposes")
                        article_text = mock_text
                
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
                        competitor_config = COMPETITORS[app_state['selected_competitor']]
                        save_processed_url(competitor_config['cache_file'], url)
                        print(f"  ✅ Article analysis completed and saved to cache")
                    else:
                        print(f"  ❌ AI analysis failed: {analysis}")
                else:
                    print(f"  ⚠️  No content available for analysis")
                
                # Update progress after processing each article
                app_state['processed_articles'] = i + 1  # Show completed articles (1-based)
                app_state['progress'] = int(((i + 1) / len(new_urls)) * 100)
                
                time.sleep(0.5)  # Small delay for demo effect
            
            # Accumulate results instead of overwriting
            if 'results' not in app_state:
                app_state['results'] = []
            app_state['results'].extend(results)
            
            app_state['processed_articles'] = len(new_urls)
            app_state['progress'] = 100
            app_state['status'] = 'completed'
            app_state['end_time'] = datetime.now()
            
            total_results = len(app_state['results'])
            print(f"\n🎉 Analysis completed! Processed {len(new_urls)} articles, found {len(results)} new analysis results")
            print(f"📊 Total accumulated results across all competitors: {total_results}")
            
    except Exception as e:
        app_state['status'] = 'error'
        app_state['current_task'] = f'Error: {str(e)}'
        app_state['end_time'] = datetime.now()
        print(f"❌ Error during analysis: {str(e)}")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', 
                         state=app_state, 
                         competitors=COMPETITORS,
                         selected_competitor=app_state['selected_competitor'])

@app.route('/select-competitor', methods=['POST'])
def select_competitor():
    """Select a competitor for analysis"""
    data = request.get_json()
    competitor_id = data.get('competitor')
    
    if competitor_id not in COMPETITORS:
        return jsonify({'error': 'Invalid competitor'}), 400
    
    app_state['selected_competitor'] = competitor_id
    return jsonify({'message': f'Selected {COMPETITORS[competitor_id]["name"]}'})

@app.route('/start', methods=['POST'])
def start_analysis():
    """Start analysis task"""
    if app_state['status'] in ['running']:
        return jsonify({'error': 'Analysis is already running'}), 400
    
    # Reset state (preserve existing results for accumulation)
    app_state.update({
        'status': 'ready',
        'progress': 0,
        'total_articles': 0,
        'processed_articles': 0,
        'current_task': '',
        'logs': [],
        'start_time': None,
        'end_time': None,
        'article_metadata': {}  # Clear previous article metadata
    })
    
    # Initialize results list if it doesn't exist, but don't clear existing results
    if 'results' not in app_state:
        app_state['results'] = []
    
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

@app.route('/clear-results', methods=['POST'])
def clear_results():
    """Clear all accumulated analysis results"""
    app_state['results'] = []
    return jsonify({'message': 'All analysis results cleared successfully'})

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

# Mock content for demo purposes when URLs fail
MOCK_CONTENT = {
    'foodme': {
        'https://www.foodme.asia/news/foodme-launches-ai-powered-restaurant-recommendations/': {
            'title': 'FeedMe Launches AI-Powered Restaurant Recommendations',
            'content': '''FeedMe today announced the launch of its revolutionary AI-powered restaurant recommendation system, designed to personalize dining experiences for users across Southeast Asia. 

The new feature leverages machine learning algorithms to analyze user preferences, dietary restrictions, past orders, and real-time data to suggest restaurants and dishes tailored to individual tastes.

Key features include:
- Smart dietary filtering for vegetarian, vegan, and allergen-free options
- Mood-based recommendations (comfort food, healthy options, celebration dining)
- Integration with local weather data to suggest appropriate cuisine
- Social dining suggestions for group orders
- Real-time availability and delivery time optimization

"This AI recommendation engine represents a significant leap forward in food delivery personalization," said CEO Jane Smith. "We're not just delivering food; we're delivering experiences that match each customer's unique preferences and lifestyle."

The feature will roll out gradually across all FeedMe markets, starting with Singapore and Malaysia in Q1 2025.'''
        },
        'https://www.foodme.asia/news/foodme-introduces-premium-membership-program/': {
            'title': 'FeedMe Introduces Premium Membership Program',
            'content': '''FeedMe has launched FeedMe Premium, a comprehensive membership program offering exclusive benefits and enhanced services for frequent users.

Premium members will enjoy:
- Zero delivery fees on all orders above $15
- Priority customer support with dedicated hotline
- Early access to new restaurant partnerships
- Exclusive discounts from premium restaurant partners
- Free monthly premium ingredients delivery box
- Advanced order scheduling up to 7 days in advance

The membership is priced at $9.99 per month with a special launch price of $5.99 for the first three months. Members can cancel anytime with no long-term commitments.

"FeedMe Premium is designed for our most loyal customers who value convenience and quality," said Product Manager Alex Wong. "We want to reward their loyalty while providing services that truly enhance their food delivery experience."

Beta testing showed 87% customer satisfaction rates, with average savings of $25 per month for active users.'''
        },
        'https://www.foodme.asia/news/foodme-expands-to-5-new-cities-in-southeast-asia/': {
            'title': 'FeedMe Expands to 5 New Cities in Southeast Asia',
            'content': '''FeedMe announced its ambitious expansion plan to enter five new major cities across Southeast Asia by the end of 2025, marking the company's largest geographic expansion to date.

The new markets include:
- Jakarta, Indonesia - Q2 2025
- Bangkok, Thailand - Q2 2025  
- Ho Chi Minh City, Vietnam - Q3 2025
- Manila, Philippines - Q4 2025
- Yangon, Myanmar - Q4 2025

Each market will launch with over 500 restaurant partners and dedicated local teams. FeedMe plans to invest $50 million in market entry, logistics infrastructure, and local partnerships.

"Southeast Asia represents an incredible opportunity for food delivery innovation," said Regional Director Maria Santos. "Each city has unique culinary traditions, and we're committed to supporting local restaurants while bringing our technology advantages to new customers."

The expansion will create approximately 1,200 new jobs across the region, including delivery partners, customer service representatives, and local management teams.

FeedMe currently operates in Singapore, Kuala Lumpur, and Penang, serving over 2 million active users.'''
        },
        'https://www.foodme.asia/news/foodme-partners-with-local-farmers-for-sustainable-dining/': {
            'title': 'FeedMe Partners with Local Farmers for Sustainable Dining',
            'content': '''FeedMe announced a groundbreaking partnership program with local farmers across Southeast Asia to promote sustainable dining and support agricultural communities.

The "Farm to App" initiative connects restaurants on the FeedMe platform directly with certified organic and sustainable farms, creating a transparent supply chain that benefits both farmers and consumers.

Program highlights:
- Direct farmer partnerships eliminating middleman costs
- Seasonal menu features highlighting local produce
- Carbon footprint tracking for farm-to-table deliveries
- Premium pricing tier for sustainably-sourced meals
- Educational content about ingredient origins and farming practices
- Monthly farmer spotlights in the app

"Sustainability isn't just about the environment; it's about creating economic opportunities for farming communities," said Sustainability Director Dr. Rachel Tan. "This program ensures fair prices for farmers while giving consumers access to the freshest, most responsibly-sourced ingredients."

The pilot program launches with 50 farms and 200 restaurants across Malaysia and Singapore, with plans to expand regionally based on initial success metrics.

Initial data shows 23% higher customer satisfaction for sustainably-sourced meals and 15% premium pricing acceptance among environmentally-conscious consumers.'''
        }
    },
    'square': {
        'https://www.squareup.com/us/en/press/square-launches-new-ai-powered-inventory-management': {
            'title': 'Square Launches New AI-Powered Inventory Management',
            'content': '''Square today announced the launch of its revolutionary AI-powered inventory management system, designed to help small and medium businesses optimize their stock levels and reduce waste through predictive analytics.

The new Square Inventory AI leverages machine learning algorithms to analyze sales patterns, seasonal trends, supplier data, and external factors to provide intelligent restocking recommendations and demand forecasting.

Key features include:
- Predictive restocking alerts based on historical sales data
- Seasonal demand forecasting with 94% accuracy
- Automatic supplier integration for seamless reordering
- Smart wastage reduction for perishable goods
- Integration with Square POS for real-time inventory tracking
- Customizable alerts for low stock and overstock situations

"Managing inventory has always been one of the biggest challenges for small businesses," said Square's VP of Product Innovation, Sarah Chen. "Our AI system takes the guesswork out of inventory management, helping merchants save time and money while ensuring they never run out of their best-selling items."

The feature is available as part of Square's Premium plan and will roll out to all U.S. merchants starting February 2025, with international expansion planned for Q3 2025.

Beta testing with 500 restaurants showed an average 30% reduction in food waste and 15% improvement in inventory turnover rates.'''
        },
        'https://www.squareup.com/us/en/press/square-introduces-contactless-payment-solutions-for-small-business': {
            'title': 'Square Introduces Enhanced Contactless Payment Solutions for Small Business',
            'content': '''Square has launched its next-generation contactless payment solutions, featuring advanced NFC technology and enhanced mobile payment capabilities specifically designed for small and medium businesses.

The new Square Contactless Pro includes:
- Universal NFC reader supporting all major digital wallets
- QR code payment integration for international customers
- Voice-activated payment confirmation for accessibility
- Lightning-fast 0.8-second transaction processing
- Enhanced encryption with military-grade security
- Offline payment processing during network outages
- Multi-language support for diverse customer bases

"Contactless payments are no longer just convenient - they're essential for modern businesses," said David Rodriguez, Square's Director of Payment Solutions. "Our new system ensures every small business can offer the same seamless payment experience as major retailers."

The solution integrates seamlessly with existing Square POS systems and requires no additional hardware for current Square customers. New merchants receive the upgraded reader at no extra cost.

Early adoption data shows 45% faster transaction times and 22% increase in customer satisfaction scores compared to traditional payment methods.

The system will be available nationwide starting January 2025, with special promotions for new Square merchants including zero transaction fees for the first month.'''
        },
        'https://www.squareup.com/us/en/press/square-expands-pos-system-with-advanced-analytics-dashboard': {
            'title': 'Square Expands POS System with Advanced Analytics Dashboard',
            'content': '''Square unveiled its comprehensive business intelligence platform, Square Analytics Pro, providing merchants with real-time insights and predictive analytics to drive business growth and operational efficiency.

The new analytics dashboard features:
- Real-time sales performance tracking across all channels
- Customer behavior analysis and segmentation
- Predictive revenue forecasting with 92% accuracy
- Automated reporting for taxes and accounting
- Comparative market analysis using anonymized data
- Staff performance metrics and scheduling optimization
- Social media integration for marketing campaign tracking

"Data-driven decision making shouldn't be exclusive to large corporations," explained Analytics Lead Jennifer Walsh. "Square Analytics Pro democratizes business intelligence, giving every merchant the tools to understand their business deeply and make informed decisions."

Key metrics available include:
- Peak sales hours and seasonal trends
- Most profitable items and customer preferences
- Inventory turnover rates and optimization suggestions
- Marketing ROI across different channels
- Staff efficiency and training recommendations

The platform also includes AI-powered insights that automatically identify growth opportunities and potential issues before they impact revenue.

Square Analytics Pro is included in the Square Plus plan at $25/month, with a 30-day free trial for existing merchants. The platform launches nationwide in February 2025.

Pilot merchants reported an average 18% increase in revenue within 60 days of implementation.'''
        },
        'https://www.squareup.com/us/en/press/square-partners-with-major-banks-for-instant-deposit-feature': {
            'title': 'Square Partners with Major Banks for Instant Deposit Feature',
            'content': '''Square announced strategic partnerships with major financial institutions to launch Square Instant Deposit, enabling merchants to access their sales revenue immediately rather than waiting for standard processing times.

Banking partners include:
- Bank of America - covering 40% of U.S. small businesses
- Wells Fargo - specialized small business banking
- Chase Bank - comprehensive commercial banking
- Capital One - technology-focused banking solutions
- Local credit unions - supporting community businesses

Square Instant Deposit features:
- Immediate fund transfers 24/7, including weekends and holidays
- No additional fees for transfers under $1,000
- Integration with existing business bank accounts
- Real-time transaction confirmation
- Enhanced fraud protection with biometric verification
- Support for both individual transactions and batch deposits

"Cash flow is the lifeblood of small businesses," said Square's Head of Financial Services, Michael Thompson. "By partnering with trusted banks, we're eliminating the traditional wait times that can create operational challenges for merchants."

The service addresses a critical pain point where 67% of small businesses report cash flow issues due to delayed payment processing. With instant deposits, merchants can:
- Pay suppliers immediately for better terms
- Take advantage of time-sensitive opportunities
- Manage unexpected expenses without borrowing
- Improve overall financial planning and stability

Square Instant Deposit will be available to all Square merchants starting March 2025, with early access for Premium plan subscribers beginning February 1st.

Initial testing showed 89% merchant satisfaction and 34% improvement in cash flow management scores.'''
        }
    }
}

def get_mock_content(competitor, url):
    """Get mock content for demo purposes"""
    if competitor in MOCK_CONTENT and url in MOCK_CONTENT[competitor]:
        mock_data = MOCK_CONTENT[competitor][url]
        return f"# {mock_data['title']}\n\n{mock_data['content']}"
    return None

def get_article_urls_generic(base_url, selector, limit=20):
    """
    Generic function to fetch article URLs from any website
    使用通用方法从任何网站获取文章链接
    """
    print(f"🔍 Fetching articles from: {base_url}")
    print(f"   Using selector: {selector}")
    print(f"   Limit: {limit} articles")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Successfully fetched page (Status: {response.status_code})")
        print(f"📄 Content length: {len(response.content)} bytes")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find article links using the provided selector
        links = soup.select(selector)
        print(f"🔍 Found {len(links)} potential article links")
        
        articles = []
        valid_articles = 0
        
        for i, link in enumerate(links[:limit * 2]):  # Get more than needed in case some are invalid
            try:
                # Extract URL
                url = link.get('href', '')
                
                # Make URL absolute if relative
                if url.startswith('/'):
                    from urllib.parse import urljoin
                    url = urljoin(base_url, url)
                elif not url.startswith('http'):
                    continue
                
                # Extract title
                title = link.get_text(strip=True) or link.get('title', '')
                if not title:
                    # Try to find title in parent elements
                    parent = link.parent
                    if parent:
                        title = parent.get_text(strip=True)
                
                # Skip if URL or title is empty
                if not url or not title:
                    continue
                
                # Try to extract publish date (this is site-specific)
                publish_date = datetime.now()  # Default to now
                original_date_text = "Today"
                
                # Look for date in nearby elements (common patterns)
                date_element = None
                for date_selector in ['.date', '.published', '.timestamp', 'time', '[datetime]']:
                    date_element = link.find_parent().find(date_selector) if link.find_parent() else None
                    if date_element:
                        break
                
                if date_element:
                    date_text = date_element.get_text(strip=True) or date_element.get('datetime', '')
                    if date_text:
                        original_date_text = date_text
                        # Try to parse the date (basic parsing)
                        try:
                            from dateutil import parser
                            publish_date = parser.parse(date_text)
                        except:
                            pass  # Keep default date if parsing fails
                
                article = {
                    'url': url,
                    'title': title,
                    'publish_date': publish_date,
                    'original_date_text': original_date_text,
                    'category': 'News',
                    'description': title,  # Use title as description fallback
                    'source': 'generic'
                }
                
                articles.append(article)
                valid_articles += 1
                print(f"  ✓ {valid_articles:2d}. {title[:60]}... ({original_date_text})")
                
                if valid_articles >= limit:
                    break
                    
            except Exception as e:
                print(f"  ❌ Error processing article link {i}: {e}")
                continue
        
        if articles:
            # Sort by publish date (newest first)
            articles.sort(key=lambda x: x['publish_date'], reverse=True)
            print(f"✅ Successfully fetched {len(articles)} articles, sorted by date (newest first)")
            return [article['url'] for article in articles], articles
        else:
            print("⚠️  No valid articles found")
            return [], []
            
    except Exception as e:
        print(f"❌ Failed to fetch articles from {base_url}: {e}")
        return [], []

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