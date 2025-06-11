from flask import Flask, jsonify
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Global state
app_state = {
    'status': 'ready',
    'message': 'System ready'
}

def simple_task():
    """最简单的后台任务"""
    global app_state
    try:
        app_state['status'] = 'running'
        app_state['message'] = 'Task started'
        
        print("Task starting...")
        time.sleep(3)
        print("Task completed")
        
        app_state['status'] = 'completed'
        app_state['message'] = 'Task completed successfully'
        
    except Exception as e:
        app_state['status'] = 'error'
        app_state['message'] = f'Error: {str(e)}'
        print(f"Error: {e}")

@app.route('/')
def index():
    """主页"""
    return f"<h1>ACFWS Test</h1><p>Status: {app_state['status']}</p><p>Message: {app_state['message']}</p><br><a href='/start'>Start Task</a>"

@app.route('/start')
def start_task():
    """启动任务"""
    if app_state['status'] == 'running':
        return jsonify({'error': 'Task already running'})
    
    # Reset state
    app_state['status'] = 'ready'
    app_state['message'] = 'Starting task...'
    
    # Start background thread
    thread = threading.Thread(target=simple_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Task started successfully'})

@app.route('/status')
def get_status():
    """获取状态"""
    return jsonify(app_state)

if __name__ == '__main__':
    print("🚀 Starting minimal test server...")
    app.run(debug=False, host='0.0.0.0', port=8090) 