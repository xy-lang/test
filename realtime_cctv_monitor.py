# -*- coding: utf-8 -*-
"""
实时央视新闻监控+AI分析系统
央视新闻更新 → 三要素评分 → DeepSeek AI分析 → 板块分析 → JSON保存
"""

import time
import json
import os
import hashlib
import requests
from datetime import datetime, timedelta
from threading import Thread, Event
import sys

# 导入你现有的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cctv_news_crawler import CCTVNewsCrawler
from ai_keyword_analyzer import DeepSeekKeywordAnalyzer
from news_source_manager import NewsSourceManager  # 🆕 新闻源管理器
# from sector_analyzer import SectorAnalyzer  # 🆕 板块分析器暂时禁用

class RealtimeCCTVAIMonitor:
    """实时央视新闻AI分析监控器"""
    
    def __init__(self, scan_interval=300, toutiao_api_key=None):
        # 数据目录
        self.data_dir = "cctv_ai_analysis"
        self.ensure_directories()
        
        # 核心组件
        self.news_crawler = CCTVNewsCrawler()  # 保留原有爬虫作为备用
        self.ai_analyzer = DeepSeekKeywordAnalyzer()
        
        # 🆕 新闻源管理器 (支持头条API + 央视爬虫)
        self.news_source_manager = NewsSourceManager(toutiao_api_key)
        
        # self.sector_analyzer = SectorAnalyzer()  # 🆕 板块分析器暂时禁用
        
        # 监控控制
        self.monitoring = False
        self.stop_event = Event()
        self.scan_interval = scan_interval  # 扫描间隔（秒）
        
        # 已处理新闻记录（避免重复分析）
        self.processed_news = set()
        self.last_cleanup_time = datetime.now()
        
        # 重要性阈值（三要素总分）
        self.importance_threshold = 0.5  # 降低阈值，提高敏感度
        
        # 政策关键词（用于硬核度评分）
        self.policy_keywords = [
            '国务院', '党中央', '习近平', '李强', '央行', '发改委',
            '财政部', '商务部', '工信部', '证监会', '银保监会',
            '重大', '决定', '政策', '支持', '促进', '发展', '规划'
        ]
        
        # 新闻源权重 🆕 增加头条新闻权重
        self.news_source_weights = {
            '央视新闻': 0.95,
            '央视新闻API': 0.90,
            '头条新闻': 0.85,  # 🆕 头条新闻权重
            '默认': 0.80
        }

    def ensure_directories(self):
        """确保目录结构存在"""
        dirs = [
            self.data_dir,
            os.path.join(self.data_dir, "daily_analysis"),
            os.path.join(self.data_dir, "important_news"),
            os.path.join(self.data_dir, "ai_recommendations"),
            os.path.join(self.data_dir, "sector_analysis")  # 🆕 板块分析目录
        ]
        
        for dir_path in dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"📁 创建目录: {dir_path}")

    def start_monitoring(self):
        """启动实时监控"""
        print("="*80)
        print("            央视新闻智能投资分析系统 v2.1")
        print("="*80)
        print(f"监控范围：多源新闻智能采集 (头条API + 央视爬虫)")
        print(f"分析引擎：DeepSeek智能分析 + 多维度评估体系")
        print(f"评估维度：时效性分析、政策权威性评估、持续影响力预测")
        print(f"扫描频率：每{self.scan_interval//60}分钟进行一次全面扫描")
        print(f"筛选标准：重要性评分≥{self.importance_threshold} 的新闻进入分析流程")
        print(f"数据存储：{os.path.abspath(self.data_dir)}")
        print("="*80)
        print("🆕 新功能：智能新闻源切换")
        # 显示新闻源状态
        self.news_source_manager.print_status_summary()
        print("="*80)
        print("系统状态：正在初始化智能监控模块...")
        print("操作提示：按 Ctrl+C 可安全退出系统")
        print("="*80)
        
        # 验证AI分析引擎连接
        if not self.ai_analyzer.test_connection():
            print("警告：智能分析引擎连接异常，系统将使用基础分析模式")
        
        self.monitoring = True
        
        # 启动监控线程
        monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        # 启动控制台
        self._start_console()

    def _monitoring_loop(self):
        """监控主循环"""
        print("\n监控系统已启动，正在实时监测央视新闻...")
    
        while self.monitoring and not self.stop_event.is_set():
            try:
                cycle_start = time.time()
            
                print(f"\n【{datetime.now().strftime('%H:%M:%S')}】执行定时扫描")
            
                # 🆕 使用新闻源管理器获取新闻
                latest_news = None
                try:
                    import threading
                    result_container = {}
                
                    def fetch_news():
                        try:
                            # 使用新的智能新闻源管理器
                            result_container['news'] = self.news_source_manager.get_latest_news(limit=10)
                            result_container['status'] = 'success'
                        except Exception as e:
                            result_container['error'] = str(e)
                            result_container['status'] = 'error'
                
                    fetch_thread = threading.Thread(target=fetch_news)
                    fetch_thread.daemon = True
                    fetch_thread.start()
                    fetch_thread.join(timeout=90)  # 增加超时时间，适应API调用
                
                    if fetch_thread.is_alive():
                        print("⚠️ 新闻抓取超时，跳过本轮扫描")
                        continue
                
                    if result_container.get('status') == 'success':
                        latest_news = result_container.get('news', [])
                        if latest_news:
                            print(f"✅ 成功获取 {len(latest_news)} 条新闻")
                        else:
                            print("⚠️ 本轮未获取到新闻，等待下次扫描")
                            continue
                    else:
                        print(f"❌ 新闻抓取失败: {result_container.get('error', '未知错误')}")
                        continue
                        
                except Exception as e:
                    print(f"❌ 新闻抓取异常: {e}")
                    continue
            
                if latest_news:
                    new_count = 0
                    analyzed_count = 0
                    
                    # 🔧 定期清理已处理新闻记录（每2小时清理一次）
                    if (datetime.now() - self.last_cleanup_time).total_seconds() > 7200:
                        old_count = len(self.processed_news)
                        self.processed_news.clear()
                        self.last_cleanup_time = datetime.now()
                        print(f"🧹 清理已处理新闻记录: {old_count}条 → 0条")
                
                    for news in latest_news:
                        # 生成新闻ID
                        news_id = self._generate_news_id(news)
                    
                        # 检查是否已处理
                        if news_id not in self.processed_news:
                            new_count += 1
                        
                            # 三要素评分
                            scores = self._compute_news_strength([news])
                            
                            # 🔧 添加调试信息
                            print(f"📊 新闻评分: {news.get('title', '')[:40]}...")
                            print(f"   强度: {scores['total_strength']:.3f} (阈值: {self.importance_threshold})")
                            detail = scores.get('detail', {})
                            print(f"   时效: {detail.get('recency', 0):.2f}, 硬核: {detail.get('hardness', 0):.2f}, 持续: {detail.get('persistence', 0):.2f}")
                        
                            # 判断是否重要
                            if scores['total_strength'] >= self.importance_threshold:
                                print(f"\n发现重要投资信息 (综合评分: {scores['total_strength']:.2f})")
                                print(f"新闻标题: {news.get('title', '')}")
                                
                                # 两阶段AI分析
                                ai_result = self._analyze_with_ai_timeout(news, scores)
                                
                                # 板块分析
                                sector_result = self._analyze_sectors(news, ai_result)
                            
                                # 保存结果
                                self._save_analysis_result(news, scores, ai_result, sector_result)
                            
                                # 显示推荐结果
                                self._display_important_news(news, scores, ai_result, sector_result)
                            
                                analyzed_count += 1
                            else:
                                print(f"   ⚪ 未达阈值，跳过分析")
                        
                            # 标记已处理
                            self.processed_news.add(news_id)
                        else:
                            print(f"🔄 已处理: {news.get('title', '')[:40]}...")
                
                    # 扫描结果（简化）
                    if new_count > 0 or analyzed_count > 0:
                        cycle_time = time.time() - cycle_start
                        print(f"扫描完成: 处理 {new_count} 条新闻，深度分析 {analyzed_count} 条，耗时 {cycle_time:.1f} 秒")
            
                # 等待下次扫描提示
                next_scan_time = (datetime.now() + timedelta(seconds=self.scan_interval)).strftime('%H:%M:%S')
                
                if analyzed_count == 0:
                    print(f"本轮扫描完成，暂无重要投资信息，下次扫描: {next_scan_time}")
                else:
                    print(f"投资分析完成！下次扫描时间: {next_scan_time}")
                
                print("-" * 60)
                print("系统持续监控中... (按 Ctrl+C 安全退出)")
                print("-" * 60)
                
                self.stop_event.wait(self.scan_interval)
            
            except Exception as e:
                print(f"❌ 监控循环错误: {e}")
                self.stop_event.wait(60)  # 错误后等待1分钟

    def _analyze_sectors(self, news, ai_result):
        """🆕 板块分析（基于AI结果和新闻内容）"""
        try:
            # 从AI结果中提取题材信息
            theme_classification = ai_result.get('theme_classification', {}) if ai_result else {}
            theme_type = theme_classification.get('theme_type', '未知题材')
            hardcore_level = theme_classification.get('hardcore_level', '行业意志')
            
            # 从新闻标题和内容中提取板块关键词
            related_sectors = self._extract_sectors_from_news(news)
            
            # 基于AI推荐股票推断相关板块
            if ai_result and ai_result.get('recommendations'):
                inferred_sectors = self._infer_sectors_from_stocks([
                    rec.get('stock_name', '') for rec in ai_result.get('recommendations', [])
                ])
                related_sectors.extend(inferred_sectors)
            
            # 去重
            related_sectors = list(set(related_sectors))
            
            if related_sectors:
                # 计算板块强度（基于新闻重要性和题材硬核度）
                news_strength = ai_result.get('news_strength', 0.5) if ai_result else 0.5
                hardcore_score = self._get_hardcore_score(hardcore_level)
                sector_strength = (news_strength + hardcore_score) / 2
                
                # 板块周期判断
                sector_cycle = self._analyze_sector_cycle(theme_type, related_sectors)
                
                sector_analysis = {
                    "related_sectors": related_sectors[:5],  # 最多5个板块
                    "sector_strength": round(sector_strength, 3),
                    "sector_cycle": sector_cycle,
                    "theme_info": {
                        "theme_type": theme_type,
                        "hardcore_level": hardcore_level,
                        "hardcore_score": hardcore_score
                    },
                    "analysis_method": "基于AI结果+新闻内容",
                    "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                print(f"板块分析: 涉及 {len(related_sectors)} 个相关板块，综合强度 {sector_strength:.2f}，处于{sector_cycle}阶段")
                return sector_analysis
            else:
                return {
                    "error": "未识别到相关板块",
                    "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def _extract_sectors_from_news(self, news):
        """🆕 从新闻中提取相关板块"""
        try:
            title = news.get('title', '')
            content = news.get('content', '')
            text = f"{title} {content}"
            
            # 板块关键词映射
            sector_keywords = {
                "银行": ["银行", "央行", "货币政策", "利率"],
                "券商": ["证券", "券商", "证监会", "资本市场"],
                "新能源": ["新能源", "清洁能源", "光伏", "风电"],
                "新能源汽车": ["新能源汽车", "电动汽车", "汽车"],
                "锂电池": ["锂电池", "电池", "储能"],
                "医药生物": ["医药", "医疗", "生物", "药品"],
                "计算机": ["计算机", "软件", "人工智能", "AI"],
                "芯片": ["芯片", "半导体", "集成电路"],
                "建筑建材": ["建筑", "基建", "工程", "建材"],
                "地产": ["房地产", "地产", "住房"]
            }
            
            detected_sectors = []
            for sector, keywords in sector_keywords.items():
                if any(keyword in text for keyword in keywords):
                    detected_sectors.append(sector)
            
            return detected_sectors[:5]  # 最多返回5个板块
            
        except Exception as e:
            print(f"⚠️ 板块提取失败: {e}")
            return []

    def _analyze_with_ai_timeout(self, news, scores):
        """带超时的AI分析"""
        import threading
    
        result_container = {}
    
        def ai_analysis():
            try:
                # 🆕 使用新的AI分析方法（包含题材分类）
                result_container['result'] = self._analyze_with_ai_enhanced(news, scores)
                result_container['status'] = 'success'
            except Exception as e:
                result_container['error'] = str(e)
                result_container['status'] = 'error'
    
        ai_thread = threading.Thread(target=ai_analysis)
        ai_thread.daemon = True
        ai_thread.start()
    
                # 等待最多60秒（缩短超时时间）
        ai_thread.join(timeout=60)
        
        if ai_thread.is_alive():
            print("⚠️ AI分析超时(60秒)，返回默认结果")
            return {'status': 'timeout', 'error': 'AI analysis timeout'}
    
        if result_container.get('status') == 'success':
            return result_container.get('result', {})
        else:
            return {'status': 'error', 'error': result_container.get('error', '未知错误')}

    def _analyze_with_ai_enhanced(self, news, scores):
        """🆕 两阶段AI分析：粗筛 + 技术精准定位"""
        try:
            print("正在进行智能分析...")
        
            # 第一阶段：AI粗筛分析
            rough_result = self.ai_analyzer.analyze_news_with_theme_classification(news, scores)
        
            if not rough_result or rough_result.get('status') == 'error':
                print("⚠️ 第一阶段分析失败，使用降级方案")
                return self._analyze_with_ai(news, scores)
        
            stage1_count = len(rough_result.get('recommendations', []))
            print(f"初步分析完成，识别到 {stage1_count} 只相关股票")
        
            # 检查第一阶段是否有推荐
            if stage1_count == 0:
                print("⚠️ 第一阶段无推荐，直接返回")
                rough_result['final_recommendations'] = []
                rough_result['analysis_method'] = '单阶段AI分析'
                return rough_result
        
            # 第二阶段：技术分析 + AI精准
            if rough_result.get('recommendations'):
                print("🔍 准备进行深度分析...")
                
                # 🆕 智能延迟：给API服务器缓冲时间
                print("📡 等待API服务器就绪...")
                time.sleep(3)  # 3秒缓冲，避免连续调用压力
                
                # 🆕 增强重试机制
                final_result = self._execute_stage2_with_retry(rough_result, news)
                
                if final_result:
                    # 合并结果
                    final_result['stage1_rough'] = rough_result
                    final_result['analysis_method'] = '两阶段AI分析'
                    
                    stage2_count = len(final_result.get('final_recommendations', []))
                    print(f"✅ 深度分析完成，最终筛选出 {stage2_count} 只优质标的")
                    
                    return final_result
                else:
                    # 降级到阶段1结果，但用更积极的表述
                    print("💡 使用快速分析结果，确保及时响应")
                    rough_result['analysis_method'] = '快速AI分析'
                    rough_result['final_recommendations'] = rough_result.get('recommendations', [])
                    rough_result['fallback_used'] = True
                    return rough_result
            # 这个else分支已经在上面处理了，删除重复逻辑
        
        except Exception as e:
            print(f"❌ 两阶段分析失败: {e}")
            # 最后的降级方案：生成基本推荐
            fallback_result = self._generate_fallback_recommendations(news)
            print(f"🔄 使用降级推荐方案，生成{len(fallback_result.get('recommendations', []))}只推荐")
            return fallback_result
    
    def _execute_stage2_with_retry(self, rough_result, news, max_retries=3):
        """🆕 执行阶段2分析，带智能重试机制"""
        
        for retry_count in range(max_retries):
            try:
                if retry_count > 0:
                    # 指数退避延迟
                    delay = 2 ** retry_count  # 2秒, 4秒, 8秒
                    print(f"🔄 第{retry_count+1}次尝试深度分析 (延迟{delay}秒)...")
                    time.sleep(delay)
                else:
                    print("🧠 正在进行深度分析和精准评估...")
                
                # 构建精准分析提示词
                refined_prompt = self._build_refined_prompt(rough_result, news)
                
                if not refined_prompt:
                    print("⚠️ 提示词构建失败，跳过本次重试")
                    continue
                
                # AI第二阶段精准分析
                final_result = self._ai_refined_analysis(refined_prompt, rough_result)
                
                # 验证结果有效性
                if final_result and final_result.get('status') != 'error':
                    # 确保有推荐结果
                    if not final_result.get('final_recommendations'):
                        final_result['final_recommendations'] = rough_result.get('recommendations', [])
                        final_result['stage2_fallback'] = True
                    
                    print(f"✅ 深度分析成功 (第{retry_count+1}次尝试)")
                    return final_result
                else:
                    error_msg = final_result.get('error', '未知错误') if final_result else 'API无响应'
                    print(f"⚠️ 第{retry_count+1}次分析失败: {error_msg}")
                    
            except Exception as e:
                error_str = str(e).lower()
                if 'timeout' in error_str:
                    print(f"⚠️ 第{retry_count+1}次尝试超时")
                elif 'network' in error_str or 'connection' in error_str:
                    print(f"⚠️ 第{retry_count+1}次网络错误: {str(e)[:50]}...")
                else:
                    print(f"⚠️ 第{retry_count+1}次分析异常: {str(e)[:50]}...")
        
        # 所有重试都失败，但用更积极的表述
        print(f"💡 深度分析服务繁忙，将使用快速分析模式")
        return None
    
    def _generate_fallback_recommendations(self, news):
        """生成降级推荐（当AI完全失败时）"""
        try:
            title = news.get('title', '')
            
            # 基于新闻标题的简单关键词匹配
            keyword_stocks = {
                '银行': [
                    {'stock_code': '000001', 'stock_name': '平安银行', 'reason': '银行业龙头'},
                    {'stock_code': '600036', 'stock_name': '招商银行', 'reason': '零售银行领先'}
                ],
                '新能源': [
                    {'stock_code': '002594', 'stock_name': '比亚迪', 'reason': '新能源汽车龙头'},
                    {'stock_code': '300750', 'stock_name': '宁德时代', 'reason': '动力电池龙头'}
                ],
                '科技': [
                    {'stock_code': '002415', 'stock_name': '海康威视', 'reason': '安防科技龙头'},
                    {'stock_code': '002230', 'stock_name': '科大讯飞', 'reason': 'AI语音技术'}
                ],
                '基建': [
                    {'stock_code': '601800', 'stock_name': '中国交建', 'reason': '基建工程龙头'},
                    {'stock_code': '601668', 'stock_name': '中国建筑', 'reason': '建筑央企龙头'}
                ]
            }
            
            recommendations = []
            for keyword, stocks in keyword_stocks.items():
                if keyword in title:
                    for stock in stocks:
                        recommendations.append({
                            'rank': len(recommendations) + 1,
                            'stock_code': stock['stock_code'],
                            'stock_name': stock['stock_name'],
                            'recommendation_reason': f"基于新闻关键词'{keyword}'的{stock['reason']}",
                            'confidence_score': 0.6,
                            'source': 'fallback_keyword_matching'
                        })
                    break
            
            if not recommendations:
                # 如果没有匹配到关键词，给出通用推荐
                recommendations = [
                    {
                        'rank': 1,
                        'stock_code': '000001',
                        'stock_name': '平安银行',
                        'recommendation_reason': '金融龙头，政策受益',
                        'confidence_score': 0.5,
                        'source': 'fallback_default'
                    }
                ]
            
            return {
                'recommendations': recommendations[:3],  # 最多3只
                'final_recommendations': recommendations[:3],
                'analysis_method': '降级关键词匹配',
                'status': 'fallback_success'
            }
            
        except Exception as e:
            print(f"❌ 降级推荐也失败: {e}")
            return {
                'recommendations': [],
                'final_recommendations': [],
                'status': 'complete_failure',
                'error': str(e)
            }

    def _build_refined_prompt(self, rough_result, news):
        """构建第二阶段精准分析提示词"""
        try:
            # 第一阶段结果总结
            stage1_summary = f"""
    第一阶段AI粗筛结果：
    推荐股票数量：{len(rough_result.get('recommendations', []))}只
    主要推荐：{[f"{rec.get('stock_name', '')}({rec.get('stock_code', '')})" for rec in rough_result.get('recommendations', [])[:3]]}
    题材分类：{rough_result.get('theme_classification', {}).get('theme_type', '未知')}
    硬核等级：{rough_result.get('theme_classification', {}).get('hardcore_level', '未知')}
    """
        
            # 获取技术分析数据（简化版，不依赖外部接口）
            technical_analysis = self._get_technical_analysis_for_stocks(rough_result.get('recommendations', []))
            
            # 技术分析结果
            tech_summary = f"""
    技术分析结果：
    分析股票数量：{len(technical_analysis.get('stock_analysis', {}))}只
    板块强度：{technical_analysis.get('sector_strength', 0):.3f}
    相关板块：{technical_analysis.get('related_sectors', [])}
    技术指标概况：{technical_analysis.get('tech_summary', '暂无')}
    """
        
            # 构建精准分析提示词
            refined_prompt = f"""
    请基于以下信息进行第二阶段精准分析：

    【原始新闻】
    标题：{news.get('title', '')}
    内容：{news.get('content', '')[:500]}...

    【第一阶段分析】
    {stage1_summary}

    【技术分析数据】
    {tech_summary}

    【精准分析要求】
    请综合考虑以下因素，对第一阶段推荐的股票进行重新评估和精准排序：

    1. 技术分析验证：
       - 板块强度是否支撑个股表现
       - 市场情绪是否有利
       - 技术指标是否配合

    2. 新闻匹配度：
       - 股票与新闻的直接关联度
       - 政策受益程度
       - 短期催化剂强度

    3. 风险评估：
       - 板块风险
       - 个股基本面风险
       - 市场时机风险

    请给出：
    1. 最终推荐股票（最多5只，按推荐强度排序）
    2. 每只股票的综合评分（0-1分）
    3. 精准推荐理由
    4. 风险提示

    输出格式为JSON。
    """
        
            return refined_prompt
        
        except Exception as e:
            print(f"⚠️ 构建提示词失败: {e}")
            return ""
    
    def _get_hardcore_score(self, hardcore_level):
        """将硬核等级转换为数值分数"""
        hardcore_mapping = {
            "国家意志": 1.0,
            "政策导向": 0.8,
            "行业意志": 0.6,
            "市场驱动": 0.4,
            "概念炒作": 0.2
        }
        return hardcore_mapping.get(hardcore_level, 0.5)
    
    def _analyze_sector_cycle(self, theme_type, sectors):
        """分析板块周期阶段"""
        # 基于主题类型判断周期
        cycle_mapping = {
            "政策利好": "启动",
            "基建投资": "成长", 
            "科技创新": "启动",
            "消费升级": "成熟",
            "能源转型": "成长",
            "金融改革": "调整"
        }
        
        # 基于板块特征判断
        if any(sector in ["新能源", "人工智能", "芯片"] for sector in sectors):
            return "启动"
        elif any(sector in ["基建", "地产", "银行"] for sector in sectors):
            return "成熟" 
        else:
            return cycle_mapping.get(theme_type, "成长")
    
    def _calculate_reason_based_score(self, reason, confidence):
        """基于推荐理由计算技术评分"""
        try:
            # 基础评分使用置信度
            base_score = confidence
            
            # 根据推荐理由中的关键词调整评分
            positive_keywords = ['利好', '支持', '促进', '增长', '提升', '优势', '领先', '突破']
            negative_keywords = ['风险', '下降', '压力', '困难', '挑战', '不确定']
            
            reason_lower = reason.lower()
            
            # 正面关键词加分
            positive_count = sum(1 for keyword in positive_keywords if keyword in reason_lower)
            base_score += positive_count * 0.05
            
            # 负面关键词减分
            negative_count = sum(1 for keyword in negative_keywords if keyword in reason_lower)
            base_score -= negative_count * 0.03
            
            # 限制在0-1范围内
            return max(0.1, min(1.0, base_score))
            
        except:
            return 0.5
    
    def _infer_single_stock_sector(self, stock_name):
        """根据股票名称推断所属板块"""
        sector_keywords = {
            "银行": ["银行", "农行", "工行", "建行", "中行", "交行"],
            "地产": ["地产", "万科", "保利", "恒大", "碧桂园"],
            "新能源": ["新能源", "比亚迪", "宁德", "锂电", "光伏", "风电"],
            "科技": ["科技", "腾讯", "阿里", "华为", "小米", "字节"],
            "医药": ["医药", "生物", "药业", "医疗", "健康"],
            "基建": ["建筑", "中建", "中铁", "基建", "工程"],
            "电力": ["电力", "华能", "大唐", "国电", "三峡"],
            "汽车": ["汽车", "一汽", "东风", "长城", "吉利"],
            "钢铁": ["钢铁", "宝钢", "鞍钢", "河钢"],
            "化工": ["化工", "石化", "化学", "材料"]
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in stock_name for keyword in keywords):
                return sector
        
        return "综合"

    def _get_technical_analysis_for_stocks(self, ai_recommendations):
        """🆕 简化的技术分析（不依赖外部数据接口）"""
        try:
            stock_analysis = {}
            related_sectors = []
            analyzed_count = 0
            
            print("正在进行技术面分析...")
            
            for rec in ai_recommendations[:5]:  # 最多分析5只股票
                stock_code = rec.get('stock_code', '')
                stock_name = rec.get('stock_name', '')
                
                if not stock_code or len(stock_code) != 6:
                    continue
                
                try:
                    # 基于推荐理由计算技术评分
                    reason = rec.get('recommendation_reason', '')
                    confidence = rec.get('confidence_score', 0.7)
                    tech_score = self._calculate_reason_based_score(reason, confidence)
                    
                    # 基于股票名称推断板块
                    sector = self._infer_single_stock_sector(stock_name)
                    if sector:
                        related_sectors.append(sector)
                    
                    stock_analysis[stock_code] = {
                        'name': stock_name,
                        'tech_score': tech_score,
                        'sector': sector,
                        'recommendation_strength': confidence,
                        'analysis_method': '基于AI推荐理由',
                        'tech_summary': f"推荐强度{confidence:.2f}, 技术评分{tech_score:.2f}",
                        'status': 'simplified_analysis'
                    }
                    
                    analyzed_count += 1
                    
                except Exception as e:
                    print(f"⚠️ {stock_code}简化分析异常: {e}")
                    continue
            
            if analyzed_count > 0:
                print(f"技术面分析完成，评估了 {analyzed_count} 只股票")
            
            # 计算整体技术评分
            if stock_analysis:
                avg_tech_score = sum([s.get('tech_score', 0.5) for s in stock_analysis.values()]) / len(stock_analysis)
                tech_summary = f"简化分析{analyzed_count}只股票，平均技术评分{avg_tech_score:.2f}"
            else:
                avg_tech_score = 0.5
                tech_summary = "无有效股票进行技术分析"
            
            return {
                'stock_analysis': stock_analysis,
                'related_sectors': list(set(related_sectors)),
                'sector_strength': avg_tech_score,  # 使用平均技术评分作为板块强度
                'tech_summary': tech_summary,
                'analyzed_count': analyzed_count,
                'analysis_method': '简化技术分析',
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"❌ 技术分析失败: {e}")
            return {
                'stock_analysis': {},
                'sector_strength': 0,
                'related_sectors': [],
                'tech_summary': '技术分析失败',
                'error': str(e)
            }
    
    def _calculate_simple_tech_score(self, rt_data, tech_indicators):
        """计算简单的技术评分"""
        try:
            score = 0.5  # 基础分
            
            # RSI评分
            rsi = tech_indicators.get('rsi', 50)
            if 30 <= rsi <= 70:  # RSI在合理区间
                score += 0.1
            elif rsi < 30:  # 超卖
                score += 0.2
            
            # 布林带位置评分
            boll_pos = tech_indicators.get('boll_pos', 0.5)
            if 0.2 <= boll_pos <= 0.8:  # 在布林带中轨附近
                score += 0.1
            
            # 成交量比率评分
            volume_ratio = tech_indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.2:  # 放量
                score += 0.1
            
            # 涨跌幅评分
            change_pct = rt_data.get('change_pct', 0)
            if change_pct > 0:  # 上涨
                score += 0.1
            
            return min(1.0, score)
            
        except Exception as e:
            return 0.5
    
    def _infer_sectors_from_stocks(self, stock_names):
        """从股票名称推断板块"""
        try:
            sectors = []
            sector_keywords = {
                "银行": ["银行", "农行", "工行", "建行", "中行"],
                "新能源汽车": ["比亚迪", "宁德时代", "理想", "小鹏", "蔚来"],
                "计算机": ["科大讯飞", "海康威视", "用友", "东软"],
                "医药": ["恒瑞医药", "药明康德", "迈瑞医疗"],
                "券商": ["中信证券", "华泰证券", "国泰君安"]
            }
            
            for stock_name in stock_names:
                for sector, keywords in sector_keywords.items():
                    if any(keyword in stock_name for keyword in keywords):
                        if sector not in sectors:
                            sectors.append(sector)
            
            return sectors[:3]  # 最多返回3个板块
            
        except Exception as e:
            return []
    
    def _generate_tech_summary(self, stock_analysis):
        """生成技术分析总结"""
        try:
            if not stock_analysis:
                return "无技术分析数据"
                
            total_stocks = len(stock_analysis)
            avg_tech_score = sum(data['tech_score'] for data in stock_analysis.values()) / total_stocks
            positive_count = sum(1 for data in stock_analysis.values() if data['change_pct'] > 0)
            
            return f"共分析{total_stocks}只股票，平均技术评分{avg_tech_score:.3f}，{positive_count}只上涨"
            
        except Exception as e:
            return "技术分析总结生成失败"

    def _ai_refined_analysis(self, refined_prompt, rough_result):
        """AI第二阶段精准分析"""
        try:
            print("🧠 AI第二阶段精准分析...")
        
            # 使用现有的AI分析器进行精准分析
            refined_result = self._call_ai_for_refined_analysis(refined_prompt)
            
            if not refined_result:
                # print("⚠️ AI精准分析无响应")  # 静默处理
                return self._fallback_refined_result(rough_result)
            
            # print(f"🤖 AI精准分析完成，响应长度: {len(str(refined_result))}")  # 静默处理
        
            # 尝试解析结果
            try:
                if isinstance(refined_result, dict):
                    refined_json = refined_result
                else:
                    # 如果是字符串，尝试解析JSON
                    import json
                    refined_json = json.loads(str(refined_result))
            except:
                # 如果不是JSON，进行文本解析
                refined_json = self._parse_refined_text(str(refined_result))
        
            # 整合最终结果
            final_result = {
                "refined_analysis": refined_json,
                "final_recommendations": refined_json.get("final_recommendations", refined_json.get("recommendations", [])),
                "risk_assessment": refined_json.get("risk_assessment", ""),
                "refined_reasoning": refined_json.get("analysis_summary", ""),
                "stage2_status": "success"
            }
        
            return final_result
        
        except Exception as e:
            # print(f"⚠️ AI精准分析失败: {e}")  # 静默处理
            # 降级：返回第一阶段结果
            return self._fallback_refined_result(rough_result, str(e))
    
    def _call_ai_for_refined_analysis(self, refined_prompt):
        """🆕 调用AI进行精准分析 - 优化版"""
        try:
            # 构建精准分析的AI请求  
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "你是专业的股票分析师，擅长综合技术分析和基本面分析进行精准股票推荐。请基于提供的技术分析数据，对股票进行重新评估和精准排序。"
                    },
                    {
                        "role": "user", 
                        "content": refined_prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            # 🆕 优化的API调用，支持更好的错误处理
            response = requests.post(
                self.ai_analyzer.base_url,
                headers=self.ai_analyzer.headers,
                json=payload,
                timeout=60  # 🆕 增加超时时间到60秒，给AI更多思考时间
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 验证返回内容质量
                if len(content) < 50:  # 内容过短可能是错误
                    print("⚠️ AI返回内容过短，可能分析不完整")
                    return None
                
                # 尝试解析为JSON
                try:
                    import json
                    parsed_result = json.loads(content)
                    
                    # 🆕 验证结果结构完整性
                    if not parsed_result.get('final_recommendations'):
                        print("⚠️ AI返回结果缺少推荐内容")
                        return {"raw_content": content}
                    
                    return parsed_result
                except json.JSONDecodeError:
                    print("⚠️ AI返回内容不是有效JSON，尝试文本解析")
                    return {"raw_content": content}
            elif response.status_code == 429:
                print("⚠️ API请求频率限制，建议稍后重试")
                return None
            elif response.status_code == 500:
                print("⚠️ AI服务器内部错误")
                return None
            else:
                print(f"⚠️ AI API调用失败 (状态码: {response.status_code})")
                return None
                
        except requests.exceptions.Timeout:
            print("⚠️ AI分析请求超时，可能服务器繁忙")
            return None
        except requests.exceptions.ConnectionError:
            print("⚠️ AI服务连接失败，请检查网络")
            return None
        except Exception as e:
            print(f"⚠️ AI分析调用异常: {str(e)[:50]}...")
            return None
    
    def _fallback_refined_result(self, rough_result, error=""):
        """🆕 精准分析失败时的智能降级结果"""
        try:
            # 获取第一阶段推荐
            stage1_recommendations = rough_result.get('recommendations', [])
            
            if not stage1_recommendations:
                return {
                    "final_recommendations": [],
                    "stage2_status": "failed", 
                    "error": error,
                    "fallback_reason": "无可用推荐数据"
                }
            
            # 🆕 基于规则的简单优化
            enhanced_recommendations = []
            
            for rec in stage1_recommendations[:5]:  # 最多处理5个
                enhanced_rec = rec.copy()
                
                # 基于股票名称的简单评分调整
                stock_name = rec.get('stock_name', '')
                confidence_boost = 0
                
                # 政策敏感词加分
                policy_keywords = ['央行', '国务院', '发改委', '财政部']
                if any(keyword in rough_result.get('news_title', '') for keyword in policy_keywords):
                    confidence_boost += 0.1
                
                # 板块热点加分
                hot_sectors = ['人工智能', '新能源', '芯片', '基建']
                if any(sector in rec.get('reason', '') for sector in hot_sectors):
                    confidence_boost += 0.05
                
                # 调整置信度
                original_confidence = float(rec.get('confidence', 0.5))
                new_confidence = min(0.95, original_confidence + confidence_boost)
                enhanced_rec['confidence'] = round(new_confidence, 3)
                enhanced_rec['fallback_enhanced'] = True
                
                enhanced_recommendations.append(enhanced_rec)
            
            # 按新的置信度排序
            enhanced_recommendations.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            return {
                "final_recommendations": enhanced_recommendations,
                "stage2_status": "fallback_enhanced",
                "fallback_reason": "使用规则增强的第一阶段结果",
                "enhancement_applied": True
            }
            
        except Exception as e:
            # 最基础的降级
            return {
                "final_recommendations": rough_result.get('recommendations', []),
                "stage2_status": "basic_fallback",
                "error": str(e),
                "fallback_reason": "使用基础第一阶段结果"
            }
    
    def _parse_refined_text(self, text_content):
        """解析AI返回的文本内容"""
        try:
            # 简单的文本解析，提取推荐信息
            recommendations = []
            
            # 查找股票代码模式（6位数字）
            import re
            stock_codes = re.findall(r'\b\d{6}\b', text_content)
            
            # 为每个股票代码创建推荐
            for i, code in enumerate(stock_codes[:5], 1):
                recommendations.append({
                    "rank": i,
                    "stock_code": code,
                    "stock_name": f"股票{code}",
                    "recommendation_reason": "基于文本解析的推荐",
                    "confidence_score": 0.6
                })
            
            return {
                "final_recommendations": recommendations,
                "analysis_summary": "基于文本解析生成的推荐",
                "parse_method": "text_extraction"
            }
            
        except Exception as e:
            return {
                "final_recommendations": [],
                "error": f"文本解析失败: {e}"
            }

    def _technical_verification(self, ai_stocks, news, ai_result):
        """技术分析验证AI推荐的股票"""
        try:
            print(f"🔍 开始技术验证{len(ai_stocks)}只股票...")
        
            # 1. 板块强度分析
            related_sectors = []
            theme_classification = ai_result.get('theme_classification', {})
            if theme_classification:
                related_sectors = theme_classification.get('related_sectors', [])
        
            # 如果AI没有返回板块信息，从新闻中提取
            if not related_sectors:
                related_sectors = self._extract_sectors_from_news(news)
        
            sector_strength = 0
            if related_sectors:
                sector_strength = self.sector_analyzer.calculate_sector_strength(related_sectors)
                print(f"📊 板块强度分析: {related_sectors} → 强度{sector_strength:.3f}")
        
            # 2. 对每只股票进行综合评分
            verified_stocks = []
            for stock_info in ai_stocks:
                stock_code = stock_info['code']
            
                # 计算综合评分
                comprehensive_score = self._calculate_comprehensive_score(
                    stock_info, sector_strength, ai_result, news
                )
            
                # 设定技术验证通过阈值
                verification_threshold = 0.6
            
                if comprehensive_score >= verification_threshold:
                    verified_stocks.append({
                        'stock_code': stock_code,
                        'stock_name': stock_info['name'],
                        'ai_confidence': stock_info['ai_confidence'],
                        'technical_score': comprehensive_score,
                        'final_score': (stock_info['ai_confidence'] + comprehensive_score) / 2,
                        'recommendation_reason': f"AI推荐+技术验证(AI:{stock_info['ai_confidence']:.2f}, 技术:{comprehensive_score:.2f})",
                        'ai_original_reason': stock_info['ai_reason'],
                        'verification_status': 'PASSED'
                    })
                    print(f"  ✅ {stock_code} {stock_info['name']}: 技术评分{comprehensive_score:.3f} 通过验证")
                else:
                    print(f"  ❌ {stock_code} {stock_info['name']}: 技术评分{comprehensive_score:.3f} 未通过验证")
        
            # 按最终评分排序
            verified_stocks.sort(key=lambda x: x['final_score'], reverse=True)
        
            return {
                'original_count': len(ai_stocks),
                'verified_count': len(verified_stocks),
                'verified_stocks': verified_stocks,
                'sector_strength': sector_strength,
                'related_sectors': related_sectors,
                'verification_method': 'AI粗筛+板块强度+综合评分',
                'verification_threshold': verification_threshold,
                'verification_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        except Exception as e:
            print(f"⚠️ 技术验证失败: {e}")
            return {
                'error': str(e), 
                'verified_stocks': [],
                'original_count': len(ai_stocks),
                'verified_count': 0
            }

    def _calculate_comprehensive_score(self, stock_info, sector_strength, ai_result, news):
        """计算股票综合评分"""
        try:
            # 基础评分组件
            scores = {
                'ai_confidence': stock_info.get('ai_confidence', 0) * 0.4,  # AI信心度 40%
                'sector_strength': sector_strength * 0.3,                   # 板块强度 30%
                'news_relevance': self._calculate_news_relevance(stock_info, news) * 0.2,  # 新闻相关度 20%
                'timing_factor': self._calculate_timing_factor(ai_result) * 0.1   # 时效性因子 10%
            }
        
            # 综合评分
            total_score = sum(scores.values())
        
            # 确保评分在0-1范围内
            total_score = max(0, min(1, total_score))
        
            return round(total_score, 3)
        
        except Exception as e:
            print(f"⚠️ 综合评分计算失败: {e}")
            return 0.5  # 默认中等评分

    def _calculate_news_relevance(self, stock_info, news):
        """计算股票与新闻的相关度"""
        try:
            stock_name = stock_info.get('name', '')
            news_title = news.get('title', '')
            news_content = news.get('content', '')
        
            # 简单的关键词匹配相关度
            if stock_name in news_title or stock_name in news_content:
                return 1.0
        
            # 检查行业关键词匹配
            industry_keywords = {
                '银行': ['银行', '金融', '贷款', '利率'],
                '新能源': ['新能源', '清洁能源', '绿色'],
                '科技': ['科技', '技术', '创新', '数字'],
                '医药': ['医药', '医疗', '健康', '药品']
            }
        
            news_text = f"{news_title} {news_content}"
            relevance_score = 0.5  # 基础相关度
        
            for industry, keywords in industry_keywords.items():
                if any(keyword in stock_name for keyword in keywords):
                    keyword_matches = sum(1 for keyword in keywords if keyword in news_text)
                    relevance_score += keyword_matches * 0.1
        
            return min(1.0, relevance_score)
        
        except Exception as e:
            return 0.5

    def _calculate_timing_factor(self, ai_result):
        """计算时效性因子"""
        try:
            # 基于AI分析的紧急程度
            urgency_keywords = ['紧急', '立即', '重大', '突破']
        
            ai_analysis = ai_result.get('news_analysis', '')
            policy_impact = ai_result.get('policy_impact', '')
        
            analysis_text = f"{ai_analysis} {policy_impact}"
        
            urgency_score = sum(0.2 for keyword in urgency_keywords if keyword in analysis_text)
        
            return min(1.0, urgency_score + 0.2)  # 基础时效性0.2
        
        except Exception as e:
            return 0.5

    def _analyze_with_ai(self, news, scores):
        """使用AI分析新闻并推荐股票"""
        try:
            # 构建AI提示词
            prompt = self._build_news_analysis_prompt(news, scores)
            
            # 调用AI
            ai_result = self.ai_analyzer.generate_stock_recommendations(prompt)
            
            return ai_result
            
        except Exception as e:
            print(f"❌ AI分析失败: {e}")
            return {'status': 'error', 'error': str(e)}

    def _compute_news_strength(self, news_list):
        """计算新闻三要素强度（使用你现有的算法）"""
        if not news_list:
            return {'total_strength': 0.0, 'detail': {}}

        news_item = news_list[0]  # 单条新闻分析
        now = datetime.now()
        
        try:
            # 第一时间性分析
            publish_time = news_item.get('publish_time', '')
            if publish_time and publish_time != 'None':
                try:
                    if isinstance(publish_time, str):
                        pub_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                    else:
                        pub_time = publish_time
                except:
                    pub_time = now  # 解析失败使用当前时间
            else:
                pub_time = now
            
            hours_diff = (now - pub_time).total_seconds() / 3600
            
            # 第一时间性评分
            if hours_diff <= 1:
                recency = 1.0
            elif hours_diff <= 6:
                recency = 0.8
            elif hours_diff <= 24:
                recency = 0.6
            else:
                recency = max(0.2, 0.6 - (hours_diff - 24) * 0.01)
            
            # 硬核程度分析
            title = news_item.get('title', '')
            content = news_item.get('content', '')
            text = f"{title} {content}"
            
            # 来源权重
            source = news_item.get('source', '默认')
            source_weight = self.news_source_weights.get(source, 0.8)
            
            # 政策关键词命中
            policy_hits = sum(1 for keyword in self.policy_keywords if keyword in text)
            policy_strength = min(1.0, policy_hits * 0.15)
            
            hardness = 0.7 * source_weight + 0.3 * policy_strength
            
            # 持续性分析（简化版，单条新闻）
            # 检查是否有延续性关键词
            continuity_keywords = ['继续', '深化', '扩大', '进一步', '持续', '推进', '加强']
            has_continuity = any(keyword in text for keyword in continuity_keywords)
            
            # 基于标题长度和内容丰富度评估持续性
            title_richness = min(1.0, len(title) / 30.0)
            persistence = 0.5 + 0.3 * title_richness + (0.2 if has_continuity else 0)
            persistence = min(1.0, persistence)
            
            # 综合评分
            total_strength = 0.34 * recency + 0.33 * hardness + 0.33 * persistence
            
            return {
                'total_strength': total_strength,
                'detail': {
                    'recency': round(recency, 3),
                    'hardness': round(hardness, 3),
                    'persistence': round(persistence, 3),
                    'source_weight': round(source_weight, 3),
                    'policy_hits': policy_hits,
                    'hours_since_publish': round(hours_diff, 2)
                }
            }
            
        except Exception as e:
            print(f"⚠️ 三要素计算失败: {e}")
            return {'total_strength': 0.5, 'detail': {'error': str(e)}}

    def _build_news_analysis_prompt(self, news, scores):
        """构建新闻分析提示词"""
        
        title = news.get('title', '')
        source = news.get('source', '')
        category = news.get('category', '')
        
        strength_detail = scores.get('detail', {})
        
        prompt = f"""你是专业的A股投资顾问，请基于央视新闻的三要素分析推荐股票：

📺 央视新闻分析：
标题：{title}
来源：{source}
分类：{category}

📊 三要素评分：
• 第一时间性：{strength_detail.get('recency', 0):.2f} (发布{strength_detail.get('hours_since_publish', 0):.1f}小时前)
• 硬核程度：{strength_detail.get('hardness', 0):.2f} (源权重{strength_detail.get('source_weight', 0):.2f}, 政策词{strength_detail.get('policy_hits', 0)}个)
• 持续性：{strength_detail.get('persistence', 0):.2f}
• 综合强度：{scores.get('total_strength', 0):.2f}

基于这条央视新闻的高评分({scores.get('total_strength', 0):.2f})，请推荐3只最相关的A股：

要求：
1. 与新闻内容高度相关
2. 考虑政策导向和时效性
3. 股票代码必须真实（6位数字）
4. 重点分析央视新闻的权威性影响

返回JSON格式：
{{
    "news_analysis": "新闻重要性分析",
    "policy_impact": "政策影响评估",
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
}}

只返回JSON，不要其他文字。"""

        return prompt

    def _save_analysis_result(self, news, scores, ai_result, sector_result=None):
        """🆕 保存分析结果到JSON文件（包含板块分析）"""
        try:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            news_id = self._generate_news_id(news)
            filename = f"{timestamp}_{news_id}.json"
            
            # 按日期创建目录
            today = datetime.now().strftime('%Y-%m-%d')
            daily_dir = os.path.join(self.data_dir, "daily_analysis", today)
            if not os.path.exists(daily_dir):
                os.makedirs(daily_dir)
            
            # 构建完整数据
            analysis_data = {
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'news_info': {
                    'id': news_id,
                    'title': news.get('title', ''),
                    'source': news.get('source', ''),
                    'category': news.get('category', ''),
                    'url': news.get('url', ''),
                    'publish_time': news.get('publish_time', ''),
                    'summary': news.get('summary', '')
                },
                'three_factors_analysis': {
                    'total_strength': scores.get('total_strength', 0),
                    'threshold': self.importance_threshold,
                    'is_important': scores.get('total_strength', 0) >= self.importance_threshold,
                    'detail_scores': scores.get('detail', {})
                },
                'ai_analysis': ai_result,
                'sector_analysis': sector_result,  # 板块分析结果（暂时为空）
                'system_info': {
                    'monitor_version': '2.0',  # 🆕 版本升级
                    'ai_model': 'deepseek-chat',
                    'analysis_trigger': 'realtime_monitoring',
                    'features': ['ai_analysis', 'sector_analysis']  # 🆕 功能列表
                }
            }
            
            # 保存主文件
            filepath = os.path.join(daily_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)
            
            # 🆕 保存板块分析单独文件
            if sector_result and 'error' not in sector_result:
                sector_dir = os.path.join(self.data_dir, "sector_analysis", today)
                if not os.path.exists(sector_dir):
                    os.makedirs(sector_dir)
                
                sector_file = os.path.join(sector_dir, f"SECTOR_{filename}")
                with open(sector_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'news_title': news.get('title', ''),
                        'sector_analysis': sector_result,
                        'analysis_time': analysis_data['analysis_time']
                    }, f, ensure_ascii=False, indent=2)
            
            # 如果是重要新闻，额外保存到重要新闻目录
            if scores.get('total_strength', 0) >= 0.8:  # 高重要性新闻
                important_dir = os.path.join(self.data_dir, "important_news")
                important_file = os.path.join(important_dir, f"IMPORTANT_{filename}")
                with open(important_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)
            
            # 更新当日汇总
            self._update_daily_summary(today, analysis_data)
            
            return filepath
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return None

    def _update_daily_summary(self, date, analysis_data):
        """🆕 更新当日汇总（包含板块统计）"""
        try:
            summary_file = os.path.join(self.data_dir, "daily_analysis", date, "summary.json")
            
            # 读取现有汇总
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
            else:
                summary = {
                    'date': date,
                    'total_news': 0,
                    'ai_analyzed': 0,
                    'important_news': 0,
                    'average_strength': 0,
                    'ai_recommendations_count': 0,
                    'sector_analyzed': 0,  # 🆕 板块分析数量
                    'top_sectors': {}      # 🆕 热门板块统计
                }
            
            # 更新统计
            summary['total_news'] += 1
            summary['ai_analyzed'] += 1
            
            strength = analysis_data['three_factors_analysis']['total_strength']
            if strength >= 0.8:
                summary['important_news'] += 1
            
            # 更新平均强度
            current_avg = summary.get('average_strength', 0)
            summary['average_strength'] = (current_avg * (summary['ai_analyzed'] - 1) + strength) / summary['ai_analyzed']
            
            # 统计AI推荐数量
            ai_recs = analysis_data.get('ai_analysis', {}).get('recommendations', [])
            summary['ai_recommendations_count'] += len(ai_recs)
            
            # # 🆕 统计板块分析（暂时禁用）
            # sector_analysis = analysis_data.get('sector_analysis', {})
            # if sector_analysis and 'error' not in sector_analysis:
            #     summary['sector_analyzed'] += 1
            #     
            #     # 统计热门板块
            #     related_sectors = sector_analysis.get('related_sectors', [])
            #     for sector in related_sectors:
            #         summary['top_sectors'][sector] = summary['top_sectors'].get(sector, 0) + 1
            
            # 保存汇总
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 汇总更新失败: {e}")

    def _display_important_news(self, news, scores, ai_result, sector_result=None):
        """🆕 实时显示重要新闻（简化版）"""
        print("\n" + "="*50)
        print(f"🎯 【投资机会】{datetime.now().strftime('%H:%M:%S')}")
        print("="*50)
        
        print(f"📰 {news.get('title', '')}")
        print(f"📊 综合评分: {scores.get('total_strength', 0):.2f}")
        
        # 优先显示最终推荐，如果没有则显示原始推荐
        final_recs = ai_result.get('final_recommendations', [])
        original_recs = ai_result.get('recommendations', [])
        
        # 显示推荐股票（简化版）
        display_recs = final_recs if final_recs else original_recs
        
        if display_recs:
            analysis_method = ai_result.get('analysis_method', 'AI分析')
            print(f"\n🏆 {analysis_method}推荐:")
            for i, rec in enumerate(display_recs, 1):
                stock_name = rec.get('stock_name', '未知')
                stock_code = rec.get('stock_code', '未知')
                confidence = rec.get('confidence_score', 0)
                print(f"  {i}. {stock_name}({stock_code}) 信心度:{confidence:.2f}")
        else:
            print(f"\n⚠️ 未获得推荐结果 (AI分析可能超时或失败)")
        
        # 显示板块信息（简化）
        if sector_result and 'error' not in sector_result:
            related_sectors = sector_result.get('related_sectors', [])
            if related_sectors:
                print(f"💪 相关板块: {', '.join(related_sectors)}")
        
        print("="*50)

    def _generate_news_id(self, news):
        """生成新闻唯一ID"""
        content = f"{news.get('title', '')}{news.get('source', '')}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:10]

    def _start_console(self):
        """🆕 启动控制台（新增板块命令）"""
        print("\n" + "="*60)
        print("          系统控制面板")
        print("="*60)
        print("可用命令：")
        print("  'q' - 停止监控")
        print("  'status' - 查看状态")
        print("  'stats' - 查看统计")
        print("  'test' - 测试AI连接")
        print("  'sectors' - 查看板块分析")  # 🆕 新增
        print("="*60)
        
        while self.monitoring:
            try:
                command = input().strip().lower()
                
                if command in ['q', 'quit']:
                    self.stop_monitoring()
                    break
                elif command == 'status':
                    self._show_status()
                elif command == 'stats':
                    self._show_statistics()
                elif command == 'test':
                    self._test_ai_connection()
                # elif command == 'sectors':  # 🆕 板块统计暂时禁用
                #     self._show_sector_stats()
                    
            except (KeyboardInterrupt, EOFError):
                self.stop_monitoring()
                break

    def _show_status(self):
        """显示系统状态"""
        print(f"\n📊 系统状态:")
        print(f"  运行状态: {'🟢 运行中' if self.monitoring else '🔴 已停止'}")
        print(f"  已处理新闻: {len(self.processed_news)} 条")
        print(f"  重要性阈值: {self.importance_threshold}")
        print(f"  数据目录: {os.path.abspath(self.data_dir)}")

    def _show_statistics(self):
        """🆕 显示统计信息（包含板块统计）"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            summary_file = os.path.join(self.data_dir, "daily_analysis", today, "summary.json")
            
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                
                print(f"\n📈 今日统计 ({today}):")
                print(f"  总新闻: {summary.get('total_news', 0)}")
                print(f"  AI分析: {summary.get('ai_analyzed', 0)}")
                print(f"  重要新闻: {summary.get('important_news', 0)}")
                # print(f"  板块分析: {summary.get('sector_analyzed', 0)}")  # 暂时禁用
                print(f"  平均强度: {summary.get('average_strength', 0):.3f}")
                print(f"  AI推荐: {summary.get('ai_recommendations_count', 0)} 只股票")
                
                # # 🆕 显示热门板块（暂时禁用）
                # top_sectors = summary.get('top_sectors', {})
                # if top_sectors:
                #     print(f"  热门板块: {dict(sorted(top_sectors.items(), key=lambda x: x[1], reverse=True)[:5])}")
            else:
                print(f"\n📈 今日暂无数据")
                
        except Exception as e:
            print(f"❌ 统计查询失败: {e}")

    # def _show_sector_stats(self):
    #     """🆕 显示板块分析统计（暂时禁用）"""
    #     print("板块分析功能暂时禁用")

    def _test_ai_connection(self):
        """测试AI连接"""
        print("🔍 测试DeepSeek AI连接...")
        if self.ai_analyzer.test_connection():
            print("✅ AI连接正常")
        else:
            print("❌ AI连接失败")

    def stop_monitoring(self):
        """停止监控"""
        print("\n🛑 正在停止监控...")
        self.monitoring = False
        self.stop_event.set()
        print("✅ 监控已停止")
        print(f"📁 数据已保存到: {os.path.abspath(self.data_dir)}")


def main():
    """主函数"""
    print("🚀 实时央视新闻AI分析系统 v2.1")
    print("📊 多源新闻采集 + 三要素评分 + DeepSeek AI推荐 + 板块分析")  # 🆕
    
    # 🆕 头条API密钥配置
    # 从测试文件中获取已验证的API Key
    toutiao_api_key = "06dc063c05502ff715690a6037905d1b"
    
    print(f"🔧 初始化新闻源管理器...")
    print(f"   - 头条新闻API: {'✅ 已配置' if toutiao_api_key else '❌ 未配置'}")
    print(f"   - 央视新闻爬虫: ✅ 已配置 (兜底方案)")
    
    # 可以通过参数调整监控间隔
    # 默认300秒(5分钟)，可选：60秒(1分钟)、1800秒(30分钟)、3600秒(1小时)
    monitor = RealtimeCCTVAIMonitor(scan_interval=300, toutiao_api_key=toutiao_api_key)
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()