# modules/ai_keyword_analyzer.py
"""
基于DeepSeek AI的关键词分析模块
"""

import requests
import json
import sys
import os
from datetime import datetime
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging

logger = logging.getLogger(__name__)

class DeepSeekKeywordAnalyzer:
    """基于DeepSeek AI的关键词分析器"""
    def __init__(self):
       # 直接硬编码API Key
        self.api_key = "sk-0b74a7d83cfd49e99aff6dd2c66a020e"
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.enabled = bool(self.api_key)

        self.fallback_dict = {
            "人工智能": ["AI", "深度学习", "机器学习", "神经网络", "算法", "芯片", "自动驾驶"],
            "新能源汽车": ["电动汽车", "锂电池", "充电桩", "比亚迪", "宁德时代", "特斯拉"],
            "雅鲁藏布江": ["水电", "水利工程", "抽水蓄能", "清洁能源", "基建", "特高压", "西藏"]
        }
        
        # 新增：板块映射字典
        self.sector_mapping = {
            "央行": ["银行", "券商", "保险", "地产"],
            "新能源": ["新能源汽车", "锂电池", "光伏", "风电", "储能"],
            "人工智能": ["计算机", "电子", "软件服务", "芯片"],
            "基建": ["建筑建材", "工程机械", "钢铁", "水泥"],
            "医疗": ["医药生物", "医疗器械", "化学制药"],
            "消费": ["食品饮料", "家用电器", "纺织服装"],
            "科技": ["通信", "电子", "计算机", "传媒"]
        }

    def expand_keywords_with_ai(self, original_keyword):
        logger.info(f"🤖 使用DeepSeek AI分析关键词: {original_keyword}")
    
        # 未配置 API Key，走备用
        if not self.enabled:
            logger.warning("⚠️ 未配置DEEPSEEK_API_KEY，使用备用关键词扩展")
            return self._fallback_analysis_simple(original_keyword)

        # 已配置，调用大模型
        prompt = self._build_investment_prompt(original_keyword)
        ai_text = self._call_deepseek_ai(prompt)
        if not ai_text:
            logger.warning("⚠️ DeepSeek 响应为空，使用备用关键词扩展")
            return self._fallback_analysis_simple(original_keyword)

        result = self._parse_ai_response(ai_text, original_keyword)
        # 🔧 返回简单的关键词列表
        return result.get('expanded_keywords', [original_keyword])

    def _fallback_analysis_simple(self, original_keyword):
        """简化的备用分析 - 只返回关键词列表"""
        fallback_keywords = self.fallback_dict.get(original_keyword, [original_keyword, "行业发展", "投资机会"])
        return fallback_keywords
    
    def _build_investment_prompt(self, keyword):
        """构建专业的投资分析提示词"""
        
        prompt = f"""你是一位专业的股票投资分析师和关键词分析专家。请分析关键词"{keyword}"在投资和股票市场中的相关性。

请按照以下JSON格式返回分析结果：

{{
    "expanded_keywords": ["关键词1", "关键词2", "关键词3"],
    "related_industries": ["相关行业1", "相关行业2"],
    "investment_concepts": ["投资概念1", "投资概念2"],
    "related_companies": ["相关公司1", "相关公司2"],
    "investment_relevance": "high",
    "market_sentiment": "positive",
    "analysis_summary": "简要分析总结"
}}

分析要求：
1. expanded_keywords: 扩展出8-12个投资相关的关键词
2. related_industries: 相关的行业板块
3. investment_concepts: 相关的投资概念
4. related_companies: 可能相关的知名上市公司或行业龙头
5. investment_relevance: 评估投资相关性等级
6. market_sentiment: 当前市场对该领域的情绪倾向
7. analysis_summary: 100字以内的投资角度分析总结

现在请分析关键词：{keyword}"""

        return prompt
    
    def _call_deepseek_ai(self, prompt):
        """调用DeepSeek AI API"""
        
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            logger.info("📡 正在调用DeepSeek AI...")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_content = result['choices'][0]['message']['content']
                logger.info(f"✅ DeepSeek AI响应成功，内容长度: {len(ai_content)}")
                return ai_content
            else:
                logger.error(f"❌ DeepSeek AI调用失败，状态码: {response.status_code}")
                logger.error(f"错误详情: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("❌ DeepSeek AI调用超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ DeepSeek AI网络请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ DeepSeek AI调用异常: {e}")
            return None
    
    def _parse_ai_response(self, ai_response, original_keyword):
        """解析AI返回的JSON结果"""
        
        try:
            # 尝试提取JSON内容
            import re
            
            # 查找JSON代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # 查找大括号内容
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(0)
                else:
                    json_content = ai_response
            
            # 解析JSON
            parsed_result = json.loads(json_content)
            
            # 验证和标准化结果
            analysis_result = {
                'original_keyword': original_keyword,
                'expanded_keywords': self._validate_keywords(parsed_result.get('expanded_keywords', []), original_keyword),
                'related_industries': parsed_result.get('related_industries', []),
                'investment_concepts': parsed_result.get('investment_concepts', []),
                'related_companies': parsed_result.get('related_companies', []),
                'investment_relevance': parsed_result.get('investment_relevance', 'medium'),
                'market_sentiment': parsed_result.get('market_sentiment', 'neutral'),
                'analysis_summary': parsed_result.get('analysis_summary', ''),
                'ai_analysis_time': datetime.now().isoformat(),
                'analysis_source': 'DeepSeek AI'
            }
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ AI响应JSON解析失败: {e}")
            logger.debug(f"原始响应: {ai_response}")
            return self._extract_keywords_from_text(ai_response, original_keyword)
        except Exception as e:
            logger.error(f"❌ AI响应处理异常: {e}")
            return self._fallback_analysis(original_keyword)
    
    def _extract_keywords_from_text(self, text, original_keyword):
        """从文本中提取关键词（当JSON解析失败时）"""
        
        logger.info("🔧 尝试从文本中提取关键词...")
        
        # 简单的关键词提取
        import re
        
        # 查找中文词汇和英文词汇
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
        english_words = re.findall(r'[A-Za-z]{2,10}', text)
        
        # 合并并去重
        extracted_keywords = list(set(chinese_words + english_words))
        
        # 过滤常见停用词
        stop_words = ['的', '和', '或', '与', '及', '等', '有', '是', '在', '了', '从', '为', '到', '将', '可以', '可能', '需要', '应该']
        filtered_keywords = [kw for kw in extracted_keywords if kw not in stop_words and len(kw) > 1]
        
        return {
            'original_keyword': original_keyword,
            'expanded_keywords': [original_keyword] + filtered_keywords[:10],
            'related_industries': [],
            'investment_concepts': [],
            'related_companies': [],
            'investment_relevance': 'medium',
            'market_sentiment': 'neutral',
            'analysis_summary': '基于文本提取的关键词分析',
            'ai_analysis_time': datetime.now().isoformat(),
            'analysis_source': 'Text Extraction'
        }
    
    def _validate_keywords(self, keywords, original_keyword):
        """验证和清理关键词列表"""
        
        if not keywords:
            return [original_keyword]
        
        # 确保原关键词在列表中
        if original_keyword not in keywords:
            keywords.insert(0, original_keyword)
        
        # 去重和过滤
        validated = []
        for kw in keywords:
            if isinstance(kw, str) and len(kw.strip()) > 0 and kw.strip() not in validated:
                validated.append(kw.strip())
        
        return validated[:15]  # 限制数量
    
    def _fallback_analysis(self, original_keyword):
        """备用分析方案"""
        
        fallback_keywords = self.fallback_dict.get(original_keyword, [original_keyword, "行业发展", "投资机会"])
        
        return {
            'original_keyword': original_keyword,
            'expanded_keywords': fallback_keywords,
            'related_industries': ["待分析"],
            'investment_concepts': ["投资机会"],
            'related_companies': [],
            'investment_relevance': 'medium',
            'market_sentiment': 'neutral',
            'analysis_summary': '使用备用分析方案',
            'ai_analysis_time': datetime.now().isoformat(),
            'analysis_source': 'Fallback Analysis'
        }
    
    def test_connection(self):
        """测试DeepSeek AI连接"""
        if not self.enabled:
            logger.warning("⚠️ 未配置DEEPSEEK_API_KEY，跳过AI连接测试")
            return False
        logger.info("🔍 测试DeepSeek AI连接...")
        try:
            ai_text = self._call_deepseek_ai("只需回复 OK")
            if ai_text and "OK" in ai_text:
                logger.info("✅ DeepSeek AI连接测试成功")
                return True
            logger.error("❌ DeepSeek AI连接测试失败")
            return False
        except Exception as e:
            logger.error(f"❌ DeepSeek AI连接测试异常: {e}")
            return False

    def generate_stock_recommendations(self, prompt):
        """基于综合分析生成股票推荐"""
        try:
            print("🤖 正在调用AI生成投资建议...")
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "你是一位专业的量化投资顾问，擅长综合多维度数据进行股票投资分析。请基于提供的技术分析和情感分析数据，给出专业的投资建议。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("✅ AI推荐生成完成")
                
                import json
                import re
                
                # 提取JSON部分
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON解析错误: {e}")
                        return {"status": "parse_error", "content": content}
                else:
                    try:
                        return json.loads(content)
                    except:
                        return {
                            "status": "text_format",
                            "content": content,
                            "error": "JSON解析失败，返回原始文本"
                        }
            else:
                print(f"❌ AI调用失败，状态码: {response.status_code}")
                return {
                    "status": "error",
                    "error": f"API调用失败: {response.status_code}"
                }
                
        except Exception as e:
            print(f"❌ AI推荐生成失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def build_recommendation_prompt(self, keyword, news_analysis, hmm_results, ai_expansion):
        """构建AI推荐的完整提示词"""
    
        # 新闻情感分析摘要
        news_summary = {
            'sentiment': news_analysis.get('overall_sentiment', 'neutral'),
            'score': news_analysis.get('sentiment_score', 0.5),
            'strength': news_analysis.get('news_strength', 0.5),
            'key_themes': news_analysis.get('key_themes', []),
            'news_count': len(news_analysis.get('news_list', []))
        }
    
        # HMM预测结果摘要
        hmm_summary = []
        for pred in hmm_results[:10]:
            hmm_summary.append({
                'code': pred['code'],
                'name': pred['name'],
                'bull_prob': pred.get('investment_prediction', {}).get('bull_prob', 0),
                'bear_prob': pred.get('risk_prediction', {}).get('bear_prob', 0),
                'neutral_prob': pred.get('investment_prediction', {}).get('neutral_prob', 0),
                'final_score': pred.get('prediction_score', 0),
                'price': pred.get('price', 0),
                'change_pct': pred.get('change_pct', 0)
            })
    
        # 相关概念
        related_concepts = []
        if isinstance(ai_expansion, dict):
            related_concepts = ai_expansion.get('expanded_keywords', [])
        elif isinstance(ai_expansion, list):
            related_concepts = ai_expansion
    
        # 🔧 修复：简化提示词，确保JSON格式正确
        prompt = f"""你是专业投资顾问，请基于以下数据推荐3只股票：

    关键词：{keyword}
    新闻情感：{news_summary['sentiment']} (分数: {news_summary['score']:.2f})
    技术分析股票：

    {self._format_hmm_results_for_prompt(hmm_summary)}

    请返回JSON格式：
    {{
        "top_recommendations": [
            {{
                "rank": 1,
                "stock_code": "股票代码",
                "stock_name": "股票名称", 
                "recommendation_reason": "推荐理由",
                "target_price": "目标价位",
                "risk_level": "风险等级"
            }}
        ]
    }}

    只返回JSON，不要其他文字。"""
    
        return prompt

    def _format_hmm_results_for_prompt(self, hmm_summary):
        """格式化HMM结果用于提示词"""
        formatted = []
        for i, stock in enumerate(hmm_summary, 1):
            stock_info = [
                f"**{i}. {stock['name']} ({stock['code']})**",
                f"- 当前价格: {stock['price']:.2f}元 ({stock['change_pct']:.2f}%)",
                f"- 牛市概率: {stock['bull_prob']:.3f}",
                f"- 熊市概率: {stock['bear_prob']:.3f}",
                f"- 中性概率: {stock['neutral_prob']:.3f}",
                f"- 综合评分: {stock['final_score']:.3f}"
            ]
            formatted.append('\n'.join(stock_info))
        
        return '\n\n'.join(formatted)

    def _build_news_analysis_prompt(self, news, scores):
        """构建新闻分析提示词"""
        
        prompt = f"""你是专业的投资分析师，请分析央视新闻的投资价值：

新闻内容：{news}

评分情况：
- 第一时间性: {scores.get('timeliness', 0)}/10
- 硬核程度: {scores.get('hardcore', 0)}/10  
- 持续性: {scores.get('sustainability', 0)}/10

请分析这条央视新闻的投资机会，推荐3只相关股票。

要求：
1. 与新闻内容高度相关
2. 考虑政策导向和时效性
3. 股票代码必须真实（6位数字）
4. 重点分析央视新闻的权威性影响
5. 预测相关板块和题材持续性

返回JSON格式：
{{
    "news_analysis": "新闻重要性分析",
    "policy_impact": "政策影响评估",
    "theme_classification": {{
        "theme_type": "题材类型",
        "hardcore_level": "硬核等级(国家意志/行业意志/个股意志)",
        "sustainability_score": 8,
        "related_sectors": ["相关板块1", "相关板块2"]
    }},
    "recommendations": [
        {{
            "rank": 1,
            "stock_code": "000001",
            "stock_name": "公司名称",
            "recommendation_reason": "基于央视新闻的推荐理由",
            "policy_relevance": "与新闻政策的关联度",
            "urgency_level": "投资紧急程度",
            "confidence_score": 0.85
        }}
    ]
}}"""

        return prompt

    def analyze_news_with_theme_classification(self, news, scores):
        """新增：新闻题材分类和板块预测"""
        try:
            # 使用新的提示词构建方法
            prompt = self._build_news_analysis_prompt(news, scores)
            
            # 调用AI
            ai_result = self.generate_stock_recommendations(prompt)
            
            # 检查是否包含新的题材分类信息
            if 'theme_classification' in ai_result:
                print("✅ 新增题材分类分析成功")
                theme_info = ai_result['theme_classification']
                print(f"题材类型: {theme_info.get('theme_type', '未知')}")
                print(f"硬核等级: {theme_info.get('hardcore_level', '未知')}")
                print(f"持续性评分: {theme_info.get('sustainability_score', 0)}")
                print(f"相关板块: {theme_info.get('related_sectors', [])}")
            
            return ai_result
            
        except Exception as e:
            print(f"❌ 题材分析失败: {e}")
            return {'status': 'error', 'error': str(e)}

# 测试函数
def test_deepseek_analyzer():
    """测试DeepSeek关键词分析器"""
    
    analyzer = DeepSeekKeywordAnalyzer()
    
    # 测试连接
    if not analyzer.test_connection():
        print("❌ DeepSeek AI连接失败")
        return
    
    # 测试关键词分析
    test_keywords = ["人工智能", "新能源汽车", "雅鲁藏布江"]
    
    for keyword in test_keywords:
        print(f"\n🧪 测试关键词: {keyword}")
        result = analyzer.expand_keywords_with_ai(keyword)
        
        if isinstance(result, dict):
            print(f"📊 分析结果:")
            print(f"  • 扩展关键词: {result['expanded_keywords']}")
            print(f"  • 相关行业: {result['related_industries']}")
            print(f"  • 投资概念: {result['investment_concepts']}")
            print(f"  • 相关公司: {result['related_companies']}")
            print(f"  • 投资相关性: {result['investment_relevance']}")
            print(f"  • 市场情绪: {result['market_sentiment']}")
            print(f"  • 分析总结: {result['analysis_summary']}")
        else:
            print(f"📊 扩展关键词: {result}")

if __name__ == "__main__":
    test_deepseek_analyzer()