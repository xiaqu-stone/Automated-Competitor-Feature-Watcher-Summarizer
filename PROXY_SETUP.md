# ACFWS 代理配置指南 / Proxy Setup Guide

## 概述 / Overview

由于访问 Gemini API 需要科学上网，ACFWS 提供了多种代理配置方式来确保正常访问。

Since accessing Gemini API requires proxy, ACFWS provides multiple proxy configuration methods.

## 🚀 快速启动 / Quick Start

### 方法 1: 使用启动脚本 (推荐)

```bash
# 使用默认代理 (127.0.0.1:7890)
./start_web.sh

# 使用自定义代理
./start_web.sh --proxy 127.0.0.1:1080

# 禁用代理
./start_web.sh --no-proxy

# 测试代理连接
./start_web.sh --test-proxy
```

### 方法 2: 环境变量启动

```bash
# 设置环境变量后启动
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
python web_app.py
```

### 方法 3: 自定义代理设置

```bash
# 通过环境变量自定义代理主机和端口
export PROXY_HOST=127.0.0.1
export PROXY_PORT=1080
python web_app.py
```

## 📋 常见代理端口 / Common Proxy Ports

| 软件/Software | 默认端口/Default Port | 说明/Description |
|---------------|----------------------|-----------------|
| Clash for Windows | 7890 | HTTP/HTTPS 代理端口 |
| V2Ray | 1080 | SOCKS5 代理端口 |
| Shadowsocks | 1080 | SOCKS5 代理端口 |
| Surge | 6152 | HTTP 代理端口 |
| Proxifier | 8080 | HTTP 代理端口 |

## 🔧 代理配置步骤 / Configuration Steps

### 1. 确认代理软件运行状态

确保你的代理软件（如 Clash、V2Ray、Shadowsocks 等）正在运行，并记下代理端口号。

### 2. 测试代理连接

```bash
# 测试代理是否可用
./start_web.sh --test-proxy

# 或者手动测试
curl -x http://127.0.0.1:7890 https://www.google.com
```

### 3. 启动 ACFWS

选择合适的启动方式：

```bash
# 最简单的方式：使用默认设置
./start_web.sh

# 如果默认端口不对，指定正确的端口
./start_web.sh --proxy 127.0.0.1:你的端口号
```

## 🐛 故障排除 / Troubleshooting

### 问题 1: 代理连接失败

```
❌ Proxy connection failed!
```

**解决方案:**
1. 确认代理软件正在运行
2. 检查代理端口号是否正确
3. 尝试不同的代理端口

### 问题 2: Gemini API 调用超时

```
Request timeout or connection error
```

**解决方案:**
1. 检查代理服务器是否稳定
2. 确认网络连接正常
3. 尝试重启代理软件

### 问题 3: 无法访问 Google 服务

**解决方案:**
1. 确认代理软件支持 HTTPS 代理
2. 检查代理规则配置
3. 尝试手动测试：`curl -x http://代理地址:端口 https://www.google.com`

## 📝 手动配置示例 / Manual Configuration Examples

### Clash for Windows 用户

```bash
# Clash 默认配置
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
python web_app.py
```

### V2Ray 用户

```bash
# V2Ray 默认配置
export HTTP_PROXY=http://127.0.0.1:1080
export HTTPS_PROXY=http://127.0.0.1:1080
python web_app.py
```

### 企业网络用户

```bash
# 企业代理示例
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
python web_app.py
```

## 🔍 验证配置 / Verify Configuration

启动后，检查控制台输出：

```
🌐 Proxy configured: http://127.0.0.1:7890
💡 You can customize proxy by setting PROXY_HOST and PROXY_PORT environment variables
🚀 Flask app running on http://0.0.0.0:8080
```

如果看到类似输出，说明代理配置成功！

## 💡 提示 / Tips

1. **推荐使用启动脚本**：`./start_web.sh` 是最方便的启动方式
2. **端口冲突**：如果 8080 端口被占用，应用会自动寻找其他可用端口
3. **测试优先**：在启动前可以使用 `--test-proxy` 参数测试代理连接
4. **环境变量持久化**：如果经常使用相同配置，可以将代理设置添加到 shell 配置文件中

## 🆘 获取帮助 / Get Help

如果遇到问题，请：
1. 检查代理软件日志
2. 使用 `./start_web.sh --help` 查看帮助
3. 测试基础网络连接：`ping google.com` 