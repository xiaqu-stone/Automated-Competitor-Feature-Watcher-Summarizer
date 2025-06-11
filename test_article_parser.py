#!/usr/bin/env python3

from bs4 import BeautifulSoup
from datetime import datetime
import re

def parse_local_grab_page(limit=10):
    """从本地保存的HTML文件解析文章信息"""
    
    try:
        with open('grab_press_page.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找文章容器
        articles = []
        
        # 查找所有文章链接（blogHyperlink）
        blog_links = soup.find_all('a', class_='blogHyperlink')
        
        print(f"找到 {len(blog_links)} 个文章链接")
        
        for link in blog_links[:limit]:
            try:
                # 获取URL
                article_url = link.get('href')
                if not article_url:
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
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # 解析日期格式 "11 Jun 2025" 或其他格式
                    try:
                        # 尝试多种日期格式
                        for fmt in ["%d %b %Y", "%B %d, %Y", "%d %B %Y"]:
                            try:
                                publish_date = datetime.strptime(date_text, fmt).isoformat()
                                break
                            except:
                                continue
                        
                        if not publish_date:
                            publish_date = date_text  # 保留原始格式
                    except:
                        publish_date = date_text
                
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
                    'description': description,
                    'category': category,
                    'source': 'grab'
                }
                
                articles.append(article_info)
                print(f"✓ {len(articles):2d}. {title[:60]}... ({publish_date})")
                
            except Exception as e:
                print(f"  ❌ 处理文章时出错: {e}")
                continue
        
        print(f"\n成功解析 {len(articles)} 篇文章信息")
        return articles
        
    except Exception as e:
        print(f"解析失败: {e}")
        return []

def test_local_parsing():
    """测试本地文件解析"""
    articles = parse_local_grab_page(limit=10)
    
    if articles:
        print("\n=== 解析结果 ===")
        for i, article in enumerate(articles, 1):
            print(f"{i:2d}. 标题: {article['title']}")
            print(f"    URL: {article['url']}")
            print(f"    日期: {article['publish_date']}")
            print(f"    分类: {article['category']}")
            print(f"    描述: {article['description'][:100]}...")
            print()
    else:
        print("❌ 未能解析到任何文章")

if __name__ == "__main__":
    test_local_parsing() 