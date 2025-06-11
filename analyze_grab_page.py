#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def analyze_grab_press_page():
    """分析Grab press页面的结构"""
    
    url = 'https://www.grab.com/sg/press/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"正在分析: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找所有可能的文章链接
        print("\n=== 查找文章链接 ===")
        
        # 查找所有包含press的链接
        all_links = soup.find_all('a', href=True)
        press_links = []
        
        for link in all_links:
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href and href != url:
                # 检查是否是文章链接
                if any(pattern in href for pattern in ['/press/', '/newsroom/', '/news/']):
                    if href.startswith('/'):
                        href = 'https://www.grab.com' + href
                    
                    # 排除非文章页面
                    if not any(exclude in href for exclude in ['#', 'javascript:', 'mailto:', 'page/']):
                        if href not in press_links:
                            press_links.append((href, text))
        
        print(f"找到 {len(press_links)} 个可能的press链接:")
        for i, (link, text) in enumerate(press_links[:10]):
            print(f"{i+1:2d}. {text[:50]}... -> {link}")
        
        # 查找文章容器
        print("\n=== 查找文章容器结构 ===")
        
        # 常见的文章容器class名称
        article_selectors = [
            'article', '.post', '.news-item', '.press-item', 
            '.card', '.content-item', '[class*="article"]',
            '[class*="post"]', '[class*="news"]', '[class*="press"]'
        ]
        
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"找到 {len(elements)} 个 '{selector}' 元素")
                if len(elements) > 0:
                    first_elem = elements[0]
                    print(f"  第一个元素的class: {first_elem.get('class', [])}")
                    print(f"  内容预览: {first_elem.get_text(strip=True)[:100]}...")
        
        # 查找时间元素
        print("\n=== 查找时间信息 ===")
        time_selectors = [
            'time', '.date', '.published', '.post-date',
            '[datetime]', '[class*="date"]', '[class*="time"]'
        ]
        
        for selector in time_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"找到 {len(elements)} 个时间元素 '{selector}':")
                for elem in elements[:3]:
                    print(f"  - {elem.get_text(strip=True)} (attrs: {elem.attrs})")
        
        # 保存页面内容到文件用于进一步分析
        with open('grab_press_page.html', 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        print(f"\n页面内容已保存到 grab_press_page.html")
        
        return press_links
        
    except Exception as e:
        print(f"分析失败: {e}")
        return []

if __name__ == "__main__":
    analyze_grab_press_page() 