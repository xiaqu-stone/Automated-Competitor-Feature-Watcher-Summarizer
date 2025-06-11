# ACFWS - 6小时高速MVP任务追踪器

**目标：** 创建一个名为 `mvp_demo.py` 的单一Python脚本，抓取Grab新闻发布区，使用Gemini 2.5 Pro分析新文章，并将功能发布信息打印到控制台。

---

### ☐ **第1小时：环境设置与基础抓取**
- [ ] **任务1.1:** 创建 `mvp_demo.py` 文件和 `requirements.txt` 文件。
- [ ] **任务1.2:** 在 `requirements.txt` 中添加 `requests`, `beautifulsoup4`, `google-generativeai`。
- [ ] **任务1.3:** 编写函数，使用`requests`和`BeautifulSoup`抓取 [Grab Newsroom](https://www.grab.com/sg/newsroom/) 页面。
- [ ] **任务1.4:** 编写函数，从页面中提取所有指向单独文章的URL链接。
- [ ] **任务1.5:** 打印URL列表以验证抓取和解析是否成功。

### ☐ **第2小时：内容提取与缓存逻辑**
- [ ] **任务2.1:** 编写函数，接收一个文章URL，抓取并返回其主要文本内容。
- [ ] **任务2.2:** 实现基于文件的缓存逻辑：
    - [ ] 编写函数 `load_processed_urls()` 从 `processed_urls.txt` 读取URL到集合(set)中。
    - [ ] 编写函数 `save_processed_url()` 将新的URL追加到 `processed_urls.txt`。
- [ ] **任务2.3:** 在主流程中集成缓存，确保只处理新的、未见过的文章URL。

### ☐ **第3小时：集成Gemini API**
- [ ] **任务3.1:** 编写一个函数或类来封装Gemini API的调用。
- [ ] **任务3.2:** 该函数应能从环境变量 `GEMINI_API_KEY` 中安全地读取API密钥。
- [ ] **任务3.3:** 将核心分析提示（Prompt）定义为一个多行字符串常量，硬编码在脚本中。
- [ ] **任务3.4:** 创建一个 `analyze_text(text)` 函数，它接收文章文本，调用Gemini API，并返回解析后的JSON响应。

### ☐ **第4小时：主逻辑与端到端流程**
- [ ] **任务4.1:** 在 `if __name__ == "__main__":` 保护下编写主执行逻辑。
- [ ] **任务4.2:** 编排端到端流程：
    1.  调用 `load_processed_urls()` 加载缓存。
    2.  调用抓取函数获取所有文章URL。
    3.  筛选出未被处理的新URL。
    4.  遍历每一个新URL：
        - 调用内容提取函数。
        - 调用 `analyze_text()` 函数进行分析。
        - 调用 `save_processed_url()` 保存已处理的URL。

### ☐ **第5小时：输出格式化与完善**
- [ ] **任务5.1:** 编写函数 `display_results(analysis_json)`。
- [ ] **任务5.2:** 在主流程中，调用此函数来处理Gemini的返回结果。
- [ ] **任务5.3:** 如果分析结果表明这是一个功能发布 (`is_feature_announcement: true`)，则在控制台清晰地打印出格式化的信息（例如：`✨ 发现新功能: [功能名称] - [摘要]`）。

### ☐ **第6小时：测试、清理与文档**
- [ ] **任务6.1:** 为关键函数（如网络请求、文件操作）添加 `try-except` 异常处理模块，增强脚本的健壮性。
- [ ] **任务6.2:** 通读代码，添加必要的注释，提高可读性。
- [ ] **任务6.3:** 创建一个简单的 `README.md` 文件，包含以下内容：
    - [ ] 项目简介。
    - [ ] 如何安装依赖 (`pip install -r requirements.txt`)。
    - [ ] 如何设置环境变量 (`export GEMINI_API_KEY="..."`)。
    - [ ] 如何运行脚本 (`python mvp_demo.py`)。
- [ ] **任务6.4:** 进行最终的端到端测试。 