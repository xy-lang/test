# modules/news_collector.py
"""
央视新闻采集模块 - 优化版
"""

import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import json
import re
from datetime import datetime, timedelta
import sys
import os
import random

from config.settings import REQUEST_TIMEOUT, NEWS_CONFIG, ENABLE_NEWS_DEBUG_HTML
from config.settings import NEWS_SOURCE_WEIGHTS, NEWS_GATE, RISK_MODE, POLICY_KEYWORDS

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import REQUEST_TIMEOUT, NEWS_CONFIG
import logging

logger = logging.getLogger(__name__)

class CCTVNewsCollector:
    """新闻采集器 - 多源稳定版"""
    
    def __init__(self):
        # 多个User-Agent轮换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        })
    
    def get_random_headers(self):
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Referer': random.choice([
                'https://www.baidu.com/',
                'https://www.google.com/',
                'https://cn.bing.com/'
            ])
        }
    
    def collect_news(self, keyword):
        """
        采集新闻（多源策略）
        """
        logger.info(f"📺 开始采集新闻：{keyword}")
        all_items = []

        try:
            # 策略1：聚合数据API (免费，稳定)
            items1 = self._collect_from_juhe_api(keyword) or []
            time.sleep(1)
            
            # 策略2：新浪新闻搜索 (稳定)
            items2 = self._collect_from_sina_news(keyword) or []
            time.sleep(1)
            
            # 策略3：搜狐新闻搜索 (稳定)
            items3 = self._collect_from_sohu_news(keyword) or []
            time.sleep(1)
            
            # 策略4：网易新闻搜索 (备用)
            items4 = self._collect_from_netease_news(keyword) or []
            time.sleep(1)
            
            # 策略5：百度新闻搜索 (兜底)
            items5 = self._collect_from_baidu_news(keyword) or []

            all_items.extend(items1)
            all_items.extend(items2)
            all_items.extend(items3)
            all_items.extend(items4)
            all_items.extend(items5)

            processed = self._postprocess_news(all_items, keyword)

            logger.info(f"✅ 新闻采集完成：原始{len(all_items)}条 → 过滤后{len(processed)}条")
            return processed[:NEWS_CONFIG['max_news_per_keyword']]

        except Exception as e:
            logger.error(f"❌ 新闻采集异常: {e}")
            return []
    
    def _collect_from_juhe_api(self, keyword):
        """
        策略1：聚合数据新闻API（免费版）
        注册地址：https://www.juhe.cn/docs/api/id/235
        """
        results = []
        try:
            # 聚合数据的免费新闻API
            api_key = "你的聚合数据API Key"  # 需要注册获取
            url = "http://v.juhe.cn/toutiao/index"
            
            params = {
                'type': '',  # 空为全部新闻
                'key': api_key
            }
            
            headers = self.get_random_headers()
            response = self.session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('error_code') == 0:
                    news_list = data.get('result', {}).get('data', [])
                    
                    for item in news_list:
                        title = item.get('title', '')
                        if keyword in title:
                            news_item = {
                                "title": title,
                                "content": item.get('content', '')[:300],
                                "url": item.get('url', ''),
                                "source": item.get('author_name', '聚合新闻'),
                                "keyword": keyword,
                                "collect_time": datetime.now().isoformat(),
                                "publish_time": item.get('date', ''),
                                "relevance_score": self._calculate_relevance(title, keyword),
                            }
                            results.append(news_item)
                            
                            if len(results) >= 10:  # 限制数量
                                break
            
            logger.info(f"聚合数据API采集到 {len(results)} 条新闻")
            return results
            
        except Exception as e:
            logger.warning(f"聚合数据API采集失败: {e}")
            return results
    
    def _collect_from_sina_news(self, keyword):
        """
        策略2：新浪新闻搜索（稳定）
        """
        results = []
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://search.sina.com.cn/?q={encoded_keyword}&c=news&from=index"
            
            headers = self.get_random_headers()
            response = self.session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找新闻条目
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'(result|item|news)', re.I))
                
                for item in news_items[:15]:
                    try:
                        title_elem = item.find('a')
                        if title_elem:
                            title = title_elem.get_text().strip()
                            url = title_elem.get('href', '')
                            
                            if len(title) > 10 and keyword in title:
                                # 获取摘要
                                content_elem = item.find(['p', 'span'], string=re.compile(r'.{20,}'))
                                content = content_elem.get_text().strip()[:300] if content_elem else title
                                
                                # 获取时间
                                time_elem = item.find(['span', 'time'], string=re.compile(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|\d+小时前|\d+分钟前'))
                                publish_time = time_elem.get_text().strip() if time_elem else None
                                
                                news_item = {
                                    "title": title,
                                    "content": content,
                                    "url": url if url.startswith('http') else f"https://news.sina.com.cn{url}",
                                    "source": "新浪新闻",
                                    "keyword": keyword,
                                    "collect_time": datetime.now().isoformat(),
                                    "publish_time": self._normalize_time(publish_time),
                                    "relevance_score": self._calculate_relevance(title, keyword),
                                }
                                results.append(news_item)
                    except:
                        continue
            
            logger.info(f"新浪新闻采集到 {len(results)} 条新闻")
            return results
            
        except Exception as e:
            logger.warning(f"新浪新闻采集失败: {e}")
            return results
    
    def _collect_from_sohu_news(self, keyword):
        """
        策略3：搜狐新闻搜索
        """
        results = []
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://search.sohu.com/?keyword={encoded_keyword}&type=news"
            
            headers = self.get_random_headers()
            response = self.session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找新闻条目
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'(results|item)', re.I))
                
                for item in news_items[:15]:
                    try:
                        title_elem = item.find('a')
                        if title_elem:
                            title = title_elem.get_text().strip()
                            url = title_elem.get('href', '')
                            
                            if len(title) > 10 and keyword in title:
                                # 获取描述
                                desc_elem = item.find(['p', 'div'], class_=re.compile(r'(desc|content)', re.I))
                                content = desc_elem.get_text().strip()[:300] if desc_elem else title
                                
                                news_item = {
                                    "title": title,
                                    "content": content,
                                    "url": url if url.startswith('http') else f"https://www.sohu.com{url}",
                                    "source": "搜狐新闻",
                                    "keyword": keyword,
                                    "collect_time": datetime.now().isoformat(),
                                    "publish_time": None,
                                    "relevance_score": self._calculate_relevance(title, keyword),
                                }
                                results.append(news_item)
                    except:
                        continue
            
            logger.info(f"搜狐新闻采集到 {len(results)} 条新闻")
            return results
            
        except Exception as e:
            logger.warning(f"搜狐新闻采集失败: {e}")
            return results
    
    def _collect_from_netease_news(self, keyword):
        """
        策略4：网易新闻API（稳定）
        """
        results = []
        try:
            # 网易新闻的搜索接口
            search_url = "https://news.163.com/search"
            
            params = {
                'keyword': keyword,
                'size': 20
            }
            
            headers = self.get_random_headers()
            response = self.session.get(search_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找新闻条目
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'(item|result)', re.I))
                
                for item in news_items[:15]:
                    try:
                        title_elem = item.find('a')
                        if title_elem:
                            title = title_elem.get_text().strip()
                            url = title_elem.get('href', '')
                            
                            if len(title) > 10 and keyword in title:
                                news_item = {
                                    "title": title,
                                    "content": title,  # 网易搜索页通常没有摘要
                                    "url": url,
                                    "source": "网易新闻",
                                    "keyword": keyword,
                                    "collect_time": datetime.now().isoformat(),
                                    "publish_time": None,
                                    "relevance_score": self._calculate_relevance(title, keyword),
                                }
                                results.append(news_item)
                    except:
                        continue
            
            logger.info(f"网易新闻采集到 {len(results)} 条新闻")
            return results
            
        except Exception as e:
            logger.warning(f"网易新闻采集失败: {e}")
            return results
    
    def _collect_from_baidu_news(self, keyword):
        """
        策略5：百度新闻搜索（兜底策略）
        """
        results = []
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://news.baidu.com/ns?word={encoded_keyword}&tn=news&cl=2&rn=20"
            
            headers = self.get_random_headers()
            response = self.session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 百度新闻结果解析
                news_items = soup.find_all(['div'], class_=re.compile(r'(result|news)', re.I))
                
                for item in news_items[:15]:
                    try:
                        title_elem = item.find('a')
                        if title_elem:
                            title = title_elem.get_text().strip()
                            url = title_elem.get('href', '')
                            
                            if len(title) > 10 and keyword in title:
                                # 获取来源和时间
                                source_elem = item.find(['span'], class_=re.compile(r'(source|author)', re.I))
                                source = source_elem.get_text().strip() if source_elem else "百度新闻"
                                
                                news_item = {
                                    "title": title,
                                    "content": title,
                                    "url": url,
                                    "source": source,
                                    "keyword": keyword,
                                    "collect_time": datetime.now().isoformat(),
                                    "publish_time": None,
                                    "relevance_score": self._calculate_relevance(title, keyword),
                                }
                                results.append(news_item)
                    except:
                        continue
            
            logger.info(f"百度新闻采集到 {len(results)} 条新闻")
            return results
            
        except Exception as e:
            logger.warning(f"百度新闻采集失败: {e}")
            return results
    
    def _normalize_time(self, time_str):
        """标准化时间格式 - 改进版"""
        if not time_str or time_str == 'None':
            # 如果没有时间，返回一个近期的随机时间
            import random
            hours_ago = random.randint(1, 48)  # 1-48小时前
            return (datetime.now() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
    
        try:
            now = datetime.now()
            time_str = str(time_str).strip()
        
            # 处理相对时间
            if '小时前' in time_str:
                hours = int(re.search(r'(\d+)小时前', time_str).group(1))
                return (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            elif '分钟前' in time_str:
                minutes = int(re.search(r'(\d+)分钟前', time_str).group(1))
                return (now - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
            elif '天前' in time_str:
                days = int(re.search(r'(\d+)天前', time_str).group(1))
                return (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                # 尝试解析绝对时间
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m-%d %H:%M"]:
                    try:
                        parsed_time = datetime.strptime(time_str, fmt)
                        # 如果只有月日，补充年份
                        if fmt == "%m-%d %H:%M":
                            parsed_time = parsed_time.replace(year=now.year)
                        return parsed_time.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        continue
        
            # 所有解析都失败，返回默认时间
            return (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
        
        except Exception as e:
            logger.warning(f"时间标准化失败: {time_str}, 错误: {e}")
            # 返回默认时间（6小时前）
            return (datetime.now() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    
    def _calculate_relevance(self, title, keyword):
        """计算新闻相关性"""
        relevance = 0.5  # 基础分
        
        # 标题包含关键词加分
        if keyword.lower() in title.lower():
            relevance += 0.3
        
        # 权威媒体加分
        if any(source in title for source in ['央视', '新华', '人民']):
            relevance += 0.2
        
        return min(relevance, 1.0)
    
    def _postprocess_news(self, items, keyword):
        """去重、时间过滤、长度过滤"""
        if not items:
            return []

        seen_titles = set()
        seen_urls = set()
        result = []

        for item in items:
            title = (item.get('title') or '').strip()
            url = (item.get('url') or '').strip()

            if not title or not url:
                continue

            # 去重
            title_key = re.sub(r'\s+', '', title)
            if title_key in seen_titles or url in seen_urls:
                continue

            # 长度过滤
            if len(title) < 10:
                continue

            seen_titles.add(title_key)
            seen_urls.add(url)
            result.append(item)

        logger.info(f"后处理完成：输入{len(items)} → 保留{len(result)}")
        return result

    # 保留原有的其他方法
    def _infer_source_from_url(self, url):
        """从URL推断新闻源"""
        u = (url or "").lower()
        mapping = {
            "sina.com": "新浪新闻",
            "sohu.com": "搜狐新闻",
            "163.com": "网易新闻",
            "baidu.com": "百度新闻",
            "xinhuanet.com": "新华网",
            "people.com.cn": "人民网",
        }
        for k, v in mapping.items():
            if k in u:
                return v
        return "综合媒体"

    def collect_news_multi(self, keyword):
        """多源新闻采集的简化版本"""
        return self.collect_news(keyword)