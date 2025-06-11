#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def extract_grab_articles(limit=10):
    """提取Grab的最新文章信息"""
    
    url = 'https://www.grab.com/sg/press/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"正在获取Grab最新文章...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找文章容器
        articles = []
        
        # 根据之前分析，文章在panel-article类中
        article_panels = soup.find_all('article', class_=lambda x: x and 'panel-article' in x)
        
        print(f"找到 {len(article_panels)} 个文章面板")
        
        for panel in article_panels[:limit]:
            try:
                # 获取链接
                link_elem = panel.find_parent('a', class_='blogHyperlink')
                if not link_elem:
                    # 尝试其他方法获取链接
                    link_elem = panel.find('a', href=True)
                
                if link_elem:
                    article_url = link_elem.get('href')
                    if article_url and not article_url.startswith('http'):
                        article_url = 'https://www.grab.com' + article_url
                else:
                    continue
                
                # 获取标题
                title_elem = panel.find(['h1', 'h2', 'h3', 'h4', 'h5'], class_=lambda x: x and ('title' in str(x) or 'headline' in str(x)))
                if not title_elem:
                    title_elem = panel.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                # 获取发布日期
                date_elem = panel.find(class_=lambda x: x and 'post-date' in x)
                if not date_elem:
                    date_elem = panel.find('time')
                
                publish_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # 尝试解析日期格式 "June 11, 2025"
                    try:
                        publish_date = datetime.strptime(date_text, "%B %d, %Y").isoformat()
                    except:
                        # 如果解析失败，保留原始文本
                        publish_date = date_text
                
                # 获取摘要/描述
                desc_elem = panel.find(class_=lambda x: x and any(desc in str(x).lower() for desc in ['excerpt', 'summary', 'description']))
                if not desc_elem:
                    # 获取面板正文的第一段
                    body_elem = panel.find(class_='panel-body')
                    if body_elem:
                        desc_elem = body_elem.find('p')
                
                description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""
                
                # 获取分类
                category_elem = panel.find(class_=lambda x: x and 'category' in str(x))
                category = category_elem.get_text(strip=True) if category_elem else "Others"
                
                article_info = {
                    'url': article_url,
                    'title': title,
                    'publish_date': publish_date,
                    'description': description,
                    'category': category,
                    'source': 'grab'
                }
                
                articles.append(article_info)
                print(f"✓ {len(articles):2d}. {title[:60]}... ({publish_date})")
                
            except Exception as e:
                print(f"  ❌ 处理文章时出错: {e}")
                continue
        
        print(f"\n成功提取 {len(articles)} 篇文章信息")
        return articles
        
    except Exception as e:
        print(f"获取文章失败: {e}")
        return []

def test_article_extraction():
    """测试文章提取功能"""
    articles = extract_grab_articles(limit=10)
    
    if articles:
        print("\n=== 提取结果摘要 ===")
        for i, article in enumerate(articles, 1):
            print(f"{i:2d}. 标题: {article['title']}")
            print(f"    URL: {article['url']}")
            print(f"    日期: {article['publish_date']}")
            print(f"    分类: {article['category']}")
            print(f"    描述: {article['description'][:100]}...")
            print()
    else:
        print("❌ 未能提取到任何文章")

if __name__ == "__main__":
    test_article_extraction() 