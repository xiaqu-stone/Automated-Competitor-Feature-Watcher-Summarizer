#!/bin/bash

# ACFWS Web App 启动脚本
# ACFWS Web App Startup Script

echo "🎯 ACFWS Web Application Startup Script"
echo "========================================"

# 函数：显示帮助信息
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --proxy HOST:PORT    Set proxy server (default: 127.0.0.1:7890)"
    echo "  --no-proxy           Disable proxy"
    echo "  --test-proxy         Test proxy connection"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Use default proxy (127.0.0.1:7890)"
    echo "  $0 --proxy 127.0.0.1:1080  # Use custom proxy"
    echo "  $0 --no-proxy              # Disable proxy"
    echo "  $0 --test-proxy             # Test proxy connection"
    echo ""
}

# 函数：设置代理
setup_proxy() {
    local proxy_url="$1"
    
    if [[ -z "$proxy_url" ]]; then
        proxy_url="127.0.0.1:7890"
    fi
    
    export HTTP_PROXY="http://$proxy_url"
    export HTTPS_PROXY="http://$proxy_url"
    export http_proxy="http://$proxy_url"
    export https_proxy="http://$proxy_url"
    
    echo "🌐 Proxy configured: http://$proxy_url"
}

# 函数：测试代理连接
test_proxy() {
    echo "🧪 Testing proxy connection..."
    if curl -x "$HTTP_PROXY" --connect-timeout 10 -s https://www.google.com > /dev/null; then
        echo "✅ Proxy connection successful!"
        return 0
    else
        echo "❌ Proxy connection failed!"
        return 1
    fi
}

# 函数：启动Web应用
start_web_app() {
    echo ""
    echo "🚀 Starting ACFWS Web Application..."
    echo "📱 The web interface will be available at: http://localhost:8080+"
    echo "⭐ Use Ctrl+C to stop the service"
    echo ""
    
    python web_app.py
}

# 解析命令行参数
USE_PROXY=true
PROXY_URL="127.0.0.1:7890"
TEST_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --proxy)
            PROXY_URL="$2"
            shift 2
            ;;
        --no-proxy)
            USE_PROXY=false
            shift
            ;;
        --test-proxy)
            TEST_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# 执行逻辑
if [[ "$USE_PROXY" == true ]]; then
    setup_proxy "$PROXY_URL"
    
    if [[ "$TEST_ONLY" == true ]]; then
        test_proxy
        exit $?
    fi
else
    echo "🚫 Proxy disabled"
    unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
fi

# 启动Web应用
start_web_app 