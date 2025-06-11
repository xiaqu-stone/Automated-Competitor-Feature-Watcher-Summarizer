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

# Import our existing MVP logic
from mvp_demo import (
    load_processed_urls, save_processed_url, get_article_urls,
    get_article_text, analyze_text, display_results
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
    
    def write(self, text):
        if text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {text.strip()}"
            self.logs.append(log_entry)
            log_queue.put(log_entry)
            # Also print to console for debugging
            print(text, end='')
    
    def flush(self):
        pass

def run_analysis_task():
    """Background task to run the ACFWS analysis"""
    global app_state
    
    try:
        app_state['status'] = 'running'
        app_state['start_time'] = datetime.now()
        app_state['current_task'] = '初始化分析任务...'
        
        # Capture stdout to get script output
        log_capture = LogCapture()
        
        with redirect_stdout(log_capture):
            print("🚀 开始分析竞品功能...")
            
            # Load processed URLs
            print("📂 加载已处理的文章缓存...")
            processed_urls = load_processed_urls()
            app_state['current_task'] = '加载缓存完成'
            
            # Get article URLs
            print("🔍 获取文章URL列表...")
            all_urls = get_article_urls()
            app_state['total_articles'] = len(all_urls)
            app_state['current_task'] = f'发现 {len(all_urls)} 篇文章'
            
            # Filter new URLs
            new_urls = [url for url in all_urls if url not in processed_urls]
            print(f"📊 发现 {len(new_urls)} 篇新文章需要分析")
            
            if not new_urls:
                print("✅ 所有文章都已分析过，无需重复处理")
                app_state['status'] = 'completed'
                app_state['end_time'] = datetime.now()
                return
            
            # Process each new article
            results = []
            for i, url in enumerate(new_urls):
                app_state['processed_articles'] = i
                app_state['progress'] = int((i / len(new_urls)) * 100)
                app_state['current_task'] = f'分析文章 {i+1}/{len(new_urls)}'
                
                print(f"\n📖 正在处理文章 {i+1}/{len(new_urls)}: {url}")
                
                # Get article content
                print("  🔄 获取文章内容...")
                article_text = get_article_text(url)
                
                if article_text and len(article_text.strip()) > 100:
                    print("  🤖 使用AI分析内容...")
                    analysis = analyze_text(article_text)
                    
                    if analysis:
                        result = {
                            'url': url,
                            'analysis': analysis,
                            'timestamp': datetime.now().isoformat(),
                            'article_preview': article_text[:200] + "..." if len(article_text) > 200 else article_text
                        }
                        results.append(result)
                        
                        # Display results (this will be captured in logs)
                        display_results(analysis)
                        
                        # Save to cache
                        save_processed_url(url)
                        print(f"  ✅ 文章分析完成并保存到缓存")
                    else:
                        print(f"  ❌ AI分析失败")
                else:
                    print(f"  ⚠️  文章内容获取失败或内容过短")
                
                time.sleep(0.5)  # Small delay for demo effect
            
            app_state['results'] = results
            app_state['processed_articles'] = len(new_urls)
            app_state['progress'] = 100
            app_state['status'] = 'completed'
            app_state['end_time'] = datetime.now()
            
            print(f"\n🎉 分析完成! 共处理 {len(new_urls)} 篇文章，发现 {len(results)} 个分析结果")
            
    except Exception as e:
        app_state['status'] = 'error'
        app_state['current_task'] = f'错误: {str(e)}'
        app_state['end_time'] = datetime.now()
        print(f"❌ 分析过程中出现错误: {str(e)}")

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', state=app_state)

@app.route('/start', methods=['POST'])
def start_analysis():
    """启动分析任务"""
    if app_state['status'] in ['running']:
        return jsonify({'error': '分析正在进行中'}), 400
    
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
    
    return jsonify({'message': '分析任务已启动'})

@app.route('/status')
def get_status():
    """获取当前状态"""
    return jsonify(app_state)

@app.route('/logs')
def stream_logs():
    """实时日志流"""
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
    """监控页面"""
    return render_template('monitor.html', state=app_state)

@app.route('/results')
def results():
    """结果页面"""
    return render_template('results.html', state=app_state)

if __name__ == '__main__':
    print("🚀 ACFWS Web演示启动中...")
    print("📱 请在浏览器中访问: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 