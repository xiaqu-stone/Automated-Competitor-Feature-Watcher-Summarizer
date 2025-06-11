# 🎯 ACFWS Multi-Competitor Demo Guide
> Automated Competitor Feature Watcher & Summarizer - 竞争对手特性监控与分析系统

## 🚀 快速启动

### 1. 启动应用
```bash
cd /Users/qq/git/storehub/hackthon/ACFWS
python web_app.py
```

### 2. 访问界面
- **主页:** http://localhost:8080
- **监控页面:** http://localhost:8080/monitor
- **结果页面:** http://localhost:8080/results

## 🏢 支持的竞争对手

### Grab (实时数据)
- **数据源:** https://www.grab.com/sg/press/
- **特性:** 实时网页抓取 + 演示数据后备
- **文章数量:** 8+ 篇最新文章
- **更新频率:** 实时

### FeedMe (演示数据)
- **数据源:** 演示文章缓存
- **特性:** 完整的模拟内容系统
- **文章数量:** 4 篇特色文章
- **内容类型:** AI推荐、会员计划、市场扩张、农业合作

## 🎮 Demo 操作流程

### Step 1: 选择竞争对手
1. 访问主页 http://localhost:8080
2. 在"Competitor Selection"区域看到两个卡片
3. 点击选择 **Grab** 或 **FeedMe**
4. 观察卡片高亮和"Selected"标签

### Step 2: 启动分析
1. 点击 **"Start Analysis"** 按钮
2. 系统自动跳转到监控页面
3. 观察实时进度更新

### Step 3: 监控分析过程
在监控页面观察：
- ✅ **进度条:** 0% → 25% → 50% → 75% → 100%
- ✅ **文章计数:** 1/4 → 2/4 → 3/4 → 4/4
- ✅ **运行时间:** 实时显示 "15s", "20s" 等
- ✅ **当前任务:** 显示正在处理的具体步骤

### Step 4: 查看分析结果
1. 分析完成后点击 **"View Results"**
2. 查看AI生成的竞争特性分析
3. 观察特性卡片、相关性评分、分类标签

## 🔄 切换竞争对手演示

### Grab → FeedMe 切换
```bash
# 在新终端中执行
curl -X POST -H "Content-Type: application/json" \
     -d '{"competitor": "foodme"}' \
     http://localhost:8080/select-competitor
```

### 验证当前选择
```bash
curl -s http://localhost:8080/status | jq '.selected_competitor'
```

## 🧪 技术特性展示

### 1. 实时网页抓取 (Grab)
- BeautifulSoup HTML解析
- 文章元数据提取 (标题、日期、分类)
- 自动排序 (最新优先)
- 错误处理与后备机制

### 2. AI特性分析
- Google Gemini AI集成
- 特性检测与分类
- 相关性评分 (1-10分)
- 结构化数据提取

### 3. 实时监控系统
- WebSocket-style进度更新
- 动态运行时计算
- 状态管理与可视化
- 响应式界面设计

### 4. 多竞争对手架构
- 插件化竞争对手配置
- 运行时切换支持
- 独立缓存管理
- 统一API接口

## 🎨 界面特性

### 主页设计
- 🏢 **竞争对手卡片:** 互动选择界面
- 📊 **状态仪表板:** 实时分析状态
- 🎯 **操作按钮:** 一键启动分析

### 监控页面
- 📈 **进度可视化:** 动态进度条和百分比
- ⏱️ **实时时间:** 运行时间和状态更新
- 📝 **任务日志:** 详细处理步骤显示

### 结果页面
- 🎴 **特性卡片:** 结构化分析结果
- 🏷️ **智能标签:** 自动分类和评分
- 📊 **元数据显示:** 发布日期和来源信息

## 🔧 故障排除

### 端口占用
```bash
# 查看端口使用
lsof -i :8080

# 终止进程
pkill -f "python web_app.py"
```

### 依赖检查
```bash
# 安装依赖
pip install flask beautifulsoup4 requests google-generativeai

# 验证模块
python -c "import flask, bs4, requests; print('All modules available')"
```

## 📋 演示检查清单

- [ ] ✅ 应用成功启动在端口8080
- [ ] ✅ 主页显示两个竞争对手选项
- [ ] ✅ 点击选择工作，卡片高亮正常
- [ ] ✅ 启动分析按钮响应
- [ ] ✅ 监控页面显示实时进度
- [ ] ✅ 分析完成，状态变为"completed"
- [ ] ✅ 结果页面显示结构化数据
- [ ] ✅ 竞争对手切换功能正常
- [ ] ✅ 错误处理和后备机制工作

## 🎪 展示亮点

1. **🔄 实时动态:** 无刷新竞争对手切换
2. **🤖 AI智能:** Gemini驱动的特性识别
3. **📱 响应式:** 适配不同屏幕尺寸
4. **🎨 专业UI:** 现代卡片式设计
5. **⚡ 高性能:** 并行处理和缓存优化
6. **🛡️ 健壮性:** 全面错误处理和后备方案

---

**开发完成时间:** 2025年1月
**技术栈:** Python Flask + BeautifulSoup + Google Gemini AI + Bootstrap + JavaScript
**代码规模:** 700+ 行Python，完整前端界面，多文件架构 