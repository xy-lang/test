# toutiao_api_test.py
"""
测试头条新闻API可用性
"""

import requests
import json
import time
from datetime import datetime

class ToutiaoAPITester:
    """头条API测试器"""
    
    def __init__(self):
        # 你的API Key
        self.api_key = "06dc063c05502ff715690a6037905d1b"
        
        # 常见的头条新闻API地址（聚合数据）
        self.possible_apis = [
            {
                "name": "聚合数据-头条新闻",
                "url": "http://v.juhe.cn/toutiao/index",
                "params": {"type": "", "key": self.api_key}
            },
            {
                "name": "聚合数据-新闻头条",
                "url": "https://v.juhe.cn/toutiao/index",
                "params": {"type": "", "key": self.api_key}
            },
            {
                "name": "聚合数据-实时新闻",
                "url": "http://v.juhe.cn/toutiao/index",
                "params": {"type": "top", "key": self.api_key}
            }
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def test_all_apis(self):
        """测试所有可能的API接口"""
        print("="*60)
        print("🧪 头条新闻API测试开始")
        print(f"📱 API Key: {self.api_key}")
        print("="*60)
        
        success_apis = []
        
        for i, api_config in enumerate(self.possible_apis, 1):
            print(f"\n【测试 {i}】{api_config['name']}")
            print(f"🔗 URL: {api_config['url']}")
            
            result = self._test_single_api(api_config)
            
            if result['success']:
                success_apis.append({**api_config, **result})
                print(f"✅ 测试成功！获取到 {result['news_count']} 条新闻")
                
                # 显示示例新闻
                if result.get('sample_news'):
                    print("📰 示例新闻:")
                    for j, news in enumerate(result['sample_news'][:3], 1):
                        print(f"  {j}. {news.get('title', '无标题')}")
            else:
                print(f"❌ 测试失败: {result['error']}")
            
            time.sleep(1)  # 避免请求过快
        
        print("\n" + "="*60)
        print("🎯 测试总结")
        print("="*60)
        
        if success_apis:
            print(f"✅ 发现 {len(success_apis)} 个可用API")
            
            # 选择最佳API
            best_api = max(success_apis, key=lambda x: x['news_count'])
            print(f"🏆 推荐使用: {best_api['name']}")
            print(f"📊 新闻数量: {best_api['news_count']} 条")
            print(f"🔗 API地址: {best_api['url']}")
            
            # 生成配置代码
            self._generate_config_code(best_api)
            
            return best_api
        else:
            print("❌ 所有API都不可用")
            print("💡 建议检查:")
            print("  1. API Key是否正确")
            print("  2. 网络连接是否正常") 
            print("  3. API服务是否还在运行")
            return None
    
    def _test_single_api(self, api_config):
        """测试单个API"""
        try:
            # 测试基础请求
            response = requests.get(
                api_config['url'],
                params=api_config['params'],
                headers=self.headers,
                timeout=10
            )
            
            print(f"📡 HTTP状态: {response.status_code}")
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'HTTP错误: {response.status_code}'
                }
            
            # 尝试解析JSON
            try:
                data = response.json()
                print(f"📄 响应格式: JSON ✅")
            except:
                return {
                    'success': False,
                    'error': '响应不是有效的JSON格式'
                }
            
            # 检查API响应结构
            print(f"🔍 响应字段: {list(data.keys()) if isinstance(data, dict) else '非字典格式'}")
            
            # 查找新闻数据
            news_data = self._extract_news_from_response(data)
            
            if news_data:
                return {
                    'success': True,
                    'news_count': len(news_data),
                    'sample_news': news_data[:5],
                    'data_structure': self._analyze_data_structure(news_data[0]) if news_data else None
                }
            else:
                return {
                    'success': False,
                    'error': '未找到新闻数据字段',
                    'response_preview': str(data)[:200] + "..." if data else "空响应"
                }
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'网络错误: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'未知错误: {e}'}
    
    def _extract_news_from_response(self, data):
        """从API响应中提取新闻数据"""
        if not isinstance(data, dict):
            return None
        
        # 常见的新闻数据字段路径
        possible_paths = [
            ['result', 'data'],
            ['data', 'result'],
            ['data'],
            ['result'],
            ['news'],
            ['articles'],
            ['items'],
            ['list']
        ]
        
        for path in possible_paths:
            try:
                current = data
                for key in path:
                    current = current[key]
                
                if isinstance(current, list) and len(current) > 0:
                    # 检查第一个元素是否包含新闻字段
                    first_item = current[0]
                    if isinstance(first_item, dict) and any(
                        field in first_item for field in ['title', 'headline', 'subject', 'content']
                    ):
                        print(f"📦 找到新闻数据路径: {' -> '.join(path)}")
                        return current
            except (KeyError, TypeError, IndexError):
                continue
        
        return None
    
    def _analyze_data_structure(self, sample_news):
        """分析新闻数据结构"""
        if not isinstance(sample_news, dict):
            return None
        
        structure = {}
        for key, value in sample_news.items():
            structure[key] = type(value).__name__
        
        return structure
    
    def _generate_config_code(self, best_api):
        """生成配置代码"""
        print(f"\n💻 生成的配置代码:")
        print("-" * 40)
        
        code = f'''
# 头条API配置
TOUTIAO_API_CONFIG = {{
    "api_key": "{self.api_key}",
    "url": "{best_api['url']}",
    "params": {best_api['params']},
    "daily_limit": 50,
    "news_count_per_call": {best_api['news_count']}
}}

# 数据结构示例:
# {json.dumps(best_api.get('data_structure', {}), indent=2, ensure_ascii=False)}
'''
        print(code)
    
    def test_data_format(self, api_config):
        """详细测试数据格式"""
        print(f"\n🔬 详细数据格式分析: {api_config['name']}")
        
        try:
            response = requests.get(
                api_config['url'],
                params=api_config['params'],
                headers=self.headers,
                timeout=10
            )
            
            data = response.json()
            news_data = self._extract_news_from_response(data)
            
            if news_data and len(news_data) > 0:
                sample = news_data[0]
                print("📋 第一条新闻的完整字段:")
                for key, value in sample.items():
                    print(f"  {key}: {type(value).__name__} = {str(value)[:100]}...")
                
                # 字段映射建议
                print("\n🔧 字段映射建议:")
                mapping = self._suggest_field_mapping(sample)
                for target_field, source_field in mapping.items():
                    print(f"  {target_field} <- {source_field}")
                    
                return mapping
            
        except Exception as e:
            print(f"❌ 详细分析失败: {e}")
            return None
    
    def _suggest_field_mapping(self, sample_news):
        """建议字段映射"""
        mapping = {}
        
        # 标题字段
        for title_field in ['title', 'headline', 'subject', 'name']:
            if title_field in sample_news:
                mapping['title'] = title_field
                break
        
        # 时间字段
        for time_field in ['date', 'time', 'publish_time', 'created_at', 'updated_at']:
            if time_field in sample_news:
                mapping['publish_time'] = time_field
                break
        
        # URL字段
        for url_field in ['url', 'link', 'href', 'detail_url']:
            if url_field in sample_news:
                mapping['url'] = url_field
                break
        
        # 来源字段
        for source_field in ['source', 'author', 'site', 'from']:
            if source_field in sample_news:
                mapping['source'] = source_field
                break
        
        # 内容字段
        for content_field in ['content', 'summary', 'description', 'abstract']:
            if content_field in sample_news:
                mapping['content'] = content_field
                break
        
        return mapping


def main():
    """主测试函数"""
    tester = ToutiaoAPITester()
    
    # 基础API测试
    best_api = tester.test_all_apis()
    
    if best_api:
        # 详细数据格式分析
        field_mapping = tester.test_data_format(best_api)
        
        if field_mapping:
            print("\n🎉 API测试完成！可以开始集成到你的系统中。")
        else:
            print("\n⚠️  API可用但数据格式需要进一步调整。")
    else:
        print("\n😔 很遗憾，当前API配置不可用。")
        print("💡 你可以:")
        print("  1. 检查API Key是否正确")
        print("  2. 联系聚合数据客服确认API接口地址")
        print("  3. 先使用央视爬虫，等API问题解决后再集成")


if __name__ == "__main__":
    main()