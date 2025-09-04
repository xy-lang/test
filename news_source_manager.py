# -*- coding: utf-8 -*-
"""
新闻源管理器 - 统一数据接口
支持头条API + 央视爬虫的智能切换策略
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

# 导入现有模块
from cctv_news_crawler import CCTVNewsCrawler


class NewsSourceInterface(ABC):
    """新闻源统一接口"""
    
    @abstractmethod
    def get_latest_news(self, limit=10):
        """获取最新新闻 - 统一返回格式"""
        pass
    
    @abstractmethod
    def get_source_name(self):
        """获取数据源名称"""
        pass


class ToutiaoNewsAdapter(NewsSourceInterface):
    """头条新闻API适配器"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.daily_call_count = 0
        self.daily_limit = 50
        self.last_reset_date = datetime.now().date()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # API配置
        self.api_config = {
            "url": "https://v.juhe.cn/toutiao/index",
            "params": {"type": "", "key": self.api_key}
        }
        
        # 加载每日调用计数
        self._load_daily_count()
    
    def _load_daily_count(self):
        """加载今日API调用计数"""
        count_file = "toutiao_api_count.json"
        try:
            if os.path.exists(count_file):
                with open(count_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                saved_date = datetime.strptime(data.get('date', ''), '%Y-%m-%d').date()
                if saved_date == datetime.now().date():
                    self.daily_call_count = data.get('count', 0)
                else:
                    # 新的一天，重置计数
                    self.daily_call_count = 0
                    self._save_daily_count()
        except Exception:
            self.daily_call_count = 0
    
    def _save_daily_count(self):
        """保存今日API调用计数"""
        count_file = "toutiao_api_count.json"
        try:
            data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'count': self.daily_call_count
            }
            with open(count_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存API计数失败: {e}")
    
    def is_quota_available(self):
        """检查API配额是否可用"""
        # 检查是否需要重置计数（新的一天）
        if datetime.now().date() != self.last_reset_date:
            self.daily_call_count = 0
            self.last_reset_date = datetime.now().date()
            self._save_daily_count()
        
        return self.daily_call_count < self.daily_limit
    
    def get_remaining_quota(self):
        """获取剩余配额"""
        return max(0, self.daily_limit - self.daily_call_count)
    
    def get_latest_news(self, limit=10):
        """获取头条最新新闻"""
        if not self.is_quota_available():
            print(f"📊 头条API今日配额已用完 ({self.daily_call_count}/{self.daily_limit})")
            return None
        
        try:
            print(f"📡 正在调用头条API... (剩余配额: {self.get_remaining_quota()})")
            
            response = requests.get(
                self.api_config['url'],
                params=self.api_config['params'],
                headers=self.headers,
                timeout=10
            )
            
            # 增加调用计数
            self.daily_call_count += 1
            self._save_daily_count()
            
            if response.status_code != 200:
                print(f"❌ 头条API请求失败: HTTP {response.status_code}")
                return None
            
            data = response.json()
            news_data = self._extract_news_from_response(data)
            
            if news_data:
                # 转换为统一格式
                standardized_news = []
                for item in news_data[:limit]:
                    standardized_item = self._standardize_news_format(item)
                    if standardized_item:
                        standardized_news.append(standardized_item)
                
                print(f"✅ 头条API获取成功: {len(standardized_news)} 条新闻")
                return standardized_news
            else:
                print("❌ 头条API响应中未找到新闻数据")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ 头条API请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 头条API网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 头条API解析错误: {e}")
            return None
    
    def _extract_news_from_response(self, data):
        """从API响应中提取新闻数据"""
        if not isinstance(data, dict):
            return None
        
        # 常见的新闻数据字段路径
        possible_paths = [
            ['result', 'data'],
            ['data', 'result'],
            ['data'],
            ['result']
        ]
        
        for path in possible_paths:
            try:
                current = data
                for key in path:
                    current = current[key]
                
                if isinstance(current, list) and len(current) > 0:
                    first_item = current[0]
                    if isinstance(first_item, dict) and any(
                        field in first_item for field in ['title', 'headline', 'subject']
                    ):
                        return current
            except (KeyError, TypeError, IndexError):
                continue
        
        return None
    
    def _standardize_news_format(self, raw_news):
        """将头条新闻转换为标准格式"""
        try:
            # 字段映射
            title = raw_news.get('title') or raw_news.get('headline') or raw_news.get('subject', '')
            url = raw_news.get('url') or raw_news.get('link') or raw_news.get('href', '')
            source = raw_news.get('source') or raw_news.get('author', '头条新闻')
            
            # 时间处理
            publish_time = raw_news.get('date') or raw_news.get('time') or raw_news.get('publish_time')
            if not publish_time:
                publish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 内容摘要
            summary = raw_news.get('content') or raw_news.get('summary') or raw_news.get('description', '')
            if not summary and title:
                summary = title[:50] + "..." if len(title) > 50 else title
            
            return {
                'title': title,
                'url': url,
                'source': f"头条新闻-{source}",
                'publish_time': publish_time,
                'summary': summary,
                'category': '时政要闻'
            }
        except Exception as e:
            print(f"⚠️ 新闻格式转换失败: {e}")
            return None
    
    def get_source_name(self):
        """获取数据源名称"""
        return "头条新闻API"


class CCTVNewsAdapter(NewsSourceInterface):
    """央视新闻爬虫适配器"""
    
    def __init__(self):
        self.crawler = CCTVNewsCrawler()
    
    def get_latest_news(self, limit=10):
        """获取央视最新新闻"""
        try:
            print("🔍 正在启动央视新闻爬虫...")
            news_list = self.crawler.get_latest_news(limit)
            
            if news_list:
                print(f"✅ 央视爬虫获取成功: {len(news_list)} 条新闻")
                return news_list
            else:
                print("❌ 央视爬虫未获取到新闻")
                return None
        except Exception as e:
            print(f"❌ 央视爬虫异常: {e}")
            return None
    
    def get_source_name(self):
        """获取数据源名称"""
        return "央视新闻爬虫"


class NewsSourceManager:
    """新闻源管理器 - 智能切换策略"""
    
    def __init__(self, toutiao_api_key=None):
        # 初始化各种新闻源
        self.sources = []
        
        # 优先级1: 头条API（如果有API key）
        if toutiao_api_key:
            self.toutiao_adapter = ToutiaoNewsAdapter(toutiao_api_key)
            self.sources.append(self.toutiao_adapter)
            print(f"📱 头条API已初始化 (剩余配额: {self.toutiao_adapter.get_remaining_quota()})")
        
        # 优先级2: 央视爬虫（兜底方案）
        self.cctv_adapter = CCTVNewsAdapter()
        self.sources.append(self.cctv_adapter)
        print("🔍 央视爬虫已初始化 (无限制)")
        
        self.current_source_index = 0
    
    def get_latest_news(self, limit=10):
        """获取最新新闻 - 智能源切换"""
        print(f"\n{'='*60}")
        print(f"📺 开始获取最新新闻 (需要{limit}条)")
        print(f"{'='*60}")
        
        # 尝试各个新闻源
        for i, source in enumerate(self.sources):
            try:
                print(f"\n🎯 尝试数据源 [{i+1}/{len(self.sources)}]: {source.get_source_name()}")
                
                # 特殊处理头条API配额检查
                if isinstance(source, ToutiaoNewsAdapter):
                    if not source.is_quota_available():
                        print(f"💡 {source.get_source_name()} 配额已用完，切换到下一个源...")
                        continue
                
                # 获取新闻
                news_list = source.get_latest_news(limit)
                
                if news_list and len(news_list) > 0:
                    print(f"✅ 成功获取 {len(news_list)} 条新闻")
                    print(f"📊 当前使用数据源: {source.get_source_name()}")
                    
                    # 显示切换信息
                    if i > 0:
                        print(f"🔄 已自动切换数据源 (原因: 前序源不可用)")
                    
                    return news_list
                else:
                    print(f"⚠️ {source.get_source_name()} 未返回有效数据，尝试下一个源...")
                    
            except Exception as e:
                print(f"❌ {source.get_source_name()} 异常: {e}")
                continue
        
        # 所有源都失败
        print(f"\n{'='*60}")
        print("❌ 所有新闻源都不可用")
        print("💡 建议检查:")
        print("   1. 网络连接是否正常")
        print("   2. API配额是否已恢复") 
        print("   3. 央视网站是否可访问")
        print(f"{'='*60}")
        
        return []
    
    def get_status_info(self):
        """获取各个源的状态信息"""
        status_info = {
            'total_sources': len(self.sources),
            'sources': []
        }
        
        for source in self.sources:
            source_info = {
                'name': source.get_source_name(),
                'available': True
            }
            
            # 头条API特殊状态
            if isinstance(source, ToutiaoNewsAdapter):
                source_info.update({
                    'quota_used': source.daily_call_count,
                    'quota_total': source.daily_limit,
                    'quota_remaining': source.get_remaining_quota(),
                    'quota_available': source.is_quota_available()
                })
            
            status_info['sources'].append(source_info)
        
        return status_info
    
    def print_status_summary(self):
        """打印状态摘要"""
        print(f"\n📊 新闻源状态摘要:")
        print(f"{'='*40}")
        
        status = self.get_status_info()
        for i, source_info in enumerate(status['sources'], 1):
            print(f"{i}. {source_info['name']}")
            
            if 'quota_remaining' in source_info:
                quota_status = "✅ 可用" if source_info['quota_available'] else "❌ 已用完"
                print(f"   配额: {source_info['quota_used']}/{source_info['quota_total']} ({quota_status})")
            else:
                print(f"   状态: ✅ 无限制")
        
        print(f"{'='*40}")
