# 环境变量配置指南

## 快速设置

在项目根目录创建 `.env` 文件，内容如下：

```env
# ACFWS Environment Variables Configuration
GEMINI_API_KEY=your_gemini_api_key_here
```

## 获取Gemini API密钥

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 登录您的Google账户
3. 点击 "Create API Key" 
4. 复制生成的API密钥
5. 将密钥粘贴到`.env`文件中替换`your_gemini_api_key_here`

## 可选配置

您还可以在`.env`文件中添加以下可选配置：

```env
# 脚本超时时间（秒）
SCRIPT_TIMEOUT=300

# 最大文章处理数量
MAX_ARTICLES=10

# 缓存文件名
CACHE_FILE=grab_articles.txt
```

## 测试配置

设置完成后，运行以下命令测试：

```bash
python web_app.py
```

然后在浏览器中访问 `http://localhost:5000` 进行测试。 