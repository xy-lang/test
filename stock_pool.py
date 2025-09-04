# modules/stock_pool.py
"""
股票池管理模块
"""

import akshare as ak
import json
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time
import re

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import STOCK_POOL_PATH, STOCK_FILTER, CACHE_DIR, REQUEST_DELAY
import logging

logger = logging.getLogger(__name__)

class StockPoolManager:
    """股票池管理器"""
    
    def __init__(self):
        self.stock_pool = {}
        self.last_update = None
        self.load_stock_pool()
    
    def build_stock_pool(self):
        """构建基础股票池"""
        logger.info("🏗️ 开始构建股票池...")
        
        try:
            # 获取A股基本信息
            logger.info("📡 获取A股基本信息...")
            stock_info = ak.stock_info_a_code_name()
            time.sleep(REQUEST_DELAY)
            
            # 获取概念板块
            logger.info("📊 获取概念板块信息...")
            try:
                concept_boards = ak.stock_board_concept_name_em()
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.warning(f"获取概念板块失败: {e}")
                concept_boards = pd.DataFrame()
            
            # 构建股票池结构
            self.stock_pool = {
                "基础信息": {
                    "总股票数": len(stock_info),
                    "更新时间": datetime.now().isoformat(),
                    "筛选条件": STOCK_FILTER
                },
                "全部股票": {},
                "概念板块": {},
                "行业分类": {},
                "热门关键词": {}
            }
            
            # 处理股票基本信息
            for _, row in stock_info.iterrows():
                code = row['code']
                name = row['name']
                
                # 基本筛选
                if self._should_exclude_stock(code, name):
                    continue
                
                self.stock_pool["全部股票"][code] = {
                    "name": name,
                    "code": code,
                    "add_time": datetime.now().isoformat()
                }
            
            # 构建概念板块映射
            self._build_concept_mapping()
            
            # 构建关键词映射
            self._build_keyword_mapping()
            
            # 保存股票池
            self.save_stock_pool()
            
            logger.info(f"✅ 股票池构建完成，共 {len(self.stock_pool['全部股票'])} 只股票")
            
        except Exception as e:
            logger.error(f"❌ 构建股票池失败: {e}")
            self._create_fallback_pool()
    
    def _should_exclude_stock(self, code, name):
        """判断是否应该排除某只股票"""
        
        # 排除ST股票
        if STOCK_FILTER['exclude_st'] and ('ST' in name or 'st' in name):
            return True
        
        # 排除特殊股票代码
        if code.startswith('4') or code.startswith('8'):  # 新三板
            return True
        
        return False
    
    def _build_concept_mapping(self):
        """构建概念板块映射"""
        logger.info("🔗 构建概念板块映射...")

        # 手动构建主要概念板块（确保稳定性）
        concept_mapping = {
            "新能源汽车": ["比亚迪", "宁德时代", "理想汽车", "小鹏汽车", "蔚来", "长城汽车", "长安汽车"],
            "锂电池": ["宁德时代", "比亚迪", "天齐锂业", "赣锋锂业", "恩捷股份", "璞泰来", "当升科技"],
            "芯片半导体": ["中芯国际", "韦尔股份", "兆易创新", "紫光国微", "汇顶科技", "卓胜微", "北方华创"],
            "人工智能": ["科大讯飞", "海康威视", "大华股份", "四维图新", "虹软科技", "佳都科技", "浪潮信息"],
            "新能源": ["隆基绿能", "通威股份", "阳光电源", "金风科技", "东方电缆", "特变电工", "正泰电器"],
            "医药生物": ["恒瑞医药", "药明康德", "迈瑞医疗", "爱尔眼科", "泰格医药", "智飞生物", "长春高新"],
            "5G通信": ["中兴通讯", "烽火通信", "信维通信", "立讯精密", "沪电股份", "深南电路", "生益科技"],
            "军工": ["中航光电", "航发动力", "中直股份", "洪都航空", "中航飞机", "中船防务", "航天发展"],
            "白酒食品": ["贵州茅台", "五粮液", "泸州老窖", "剑南春", "海天味业", "伊利股份", "双汇发展"],
            "银行": ["招商银行", "平安银行", "兴业银行", "民生银行", "浦发银行", "中信银行", "光大银行"]
        }

        # 将概念映射转换为代码映射
        for concept, stock_names in concept_mapping.items():
            self.stock_pool["概念板块"][concept] = []
            for stock_name in stock_names:
                for code, info in self.stock_pool["全部股票"].items():
                    if stock_name in info["name"] or info["name"] in stock_name:
                        self.stock_pool["概念板块"][concept].append({
                            "code": code,
                            "name": info["name"]
                        })
                        break

        # —— 新增：基于名称自动构建“水电水利”概念（不引入外部数据）——
        try:
            logger.info("💧 自动构建『水电水利』概念...")
            self.stock_pool["概念板块"].setdefault("水电水利", [])
            existed = set(x["code"] for x in self.stock_pool["概念板块"]["水电水利"])

            hydro_keywords = ["水电", "水利", "抽水", "蓄能", "西藏"]
            for code, info in self.stock_pool["全部股票"].items():
                name = info["name"]
                if any(k in name for k in hydro_keywords):
                    if code not in existed:
                        self.stock_pool["概念板块"]["水电水利"].append({"code": code, "name": name})
            logger.info(f"✅ 『水电水利』收录 {len(self.stock_pool['概念板块']['水电水利'])} 只股票")
        except Exception as e:
            logger.warning(f"⚠️ 自动构建『水电水利』失败: {e}")
    
    def _build_keyword_mapping(self):
        """构建关键词映射"""
        logger.info("🏷️ 构建关键词映射...")

        keyword_mapping = {
            # 新能源汽车相关
            "新能源汽车": ["概念板块", "新能源汽车"],
            "新能源": ["概念板块", "新能源汽车"],
            "汽车": ["概念板块", "新能源汽车"],
            "电动汽车": ["概念板块", "新能源汽车"],
            "比亚迪": ["概念板块", "新能源汽车"],
            "蔚来": ["概念板块", "新能源汽车"],
            "理想": ["概念板块", "新能源汽车"],
    
            # 电池相关
            "电池": ["概念板块", "锂电池"],
            "锂电池": ["概念板块", "锂电池"],
            "宁德时代": ["概念板块", "锂电池"],
            "锂": ["概念板块", "锂电池"],
    
            # 芯片半导体
            "芯片": ["概念板块", "芯片半导体"],
            "半导体": ["概念板块", "芯片半导体"],
            "集成电路": ["概念板块", "芯片半导体"],
    
            # AI人工智能
            "AI": ["概念板块", "人工智能"],
            "人工智能": ["概念板块", "人工智能"],
            "智能": ["概念板块", "人工智能"],
    
            # 🔧 新增：水电水利相关
            "雅鲁藏布江": ["概念板块", "水电水利"],
            "雅鲁藏布": ["概念板块", "水电水利"],
            "水电站": ["概念板块", "水电水利"],
            "水电": ["概念板块", "水电水利"],
            "水利": ["概念板块", "水电水利"],
            "抽水蓄能": ["概念板块", "水电水利"],
            "水力发电": ["概念板块", "水电水利"],
            "大坝": ["概念板块", "水电水利"],
            "西藏": ["概念板块", "水电水利"],
            "水库": ["概念板块", "水电水利"],
        
            # 新能源发电
            "太阳能": ["概念板块", "新能源"],
            "风电": ["概念板块", "新能源"],
            "光伏": ["概念板块", "新能源"],
    
            # 医药生物
            "医药": ["概念板块", "医药生物"],
            "生物": ["概念板块", "医药生物"],
            "疫苗": ["概念板块", "医药生物"],
    
            # 通信5G
            "5G": ["概念板块", "5G通信"],
            "通信": ["概念板块", "5G通信"],
    
            # 军工国防
            "军工": ["概念板块", "军工"],
            "国防": ["概念板块", "军工"],
    
            # 市场相关
            "A股": ["概念板块", "新能源汽车"],
            "股市": ["概念板块", "新能源汽车"],
            "市场": ["概念板块", "新能源汽车"],
            "大盘": ["概念板块", "新能源汽车"]
        }

        self.stock_pool["热门关键词"] = keyword_mapping
    
    # modules/stock_pool_manager.py
    def find_related_stocks(self, keyword, max_results=10):
        """查找相关股票 - 增强版"""
        try:
            related_stocks = []
            keyword_lower = keyword.lower()
        
            # 获取股票数据
            all_stocks = self.stock_pool.get("全部股票", {})
            if not all_stocks:
                logger.warning("股票池为空")
                return []
        
            # 1. 直接关键词匹配
            keyword_mapping = self.stock_pool.get("热门关键词", {})
            matched_concepts = []
        
            # 🔧 支持模糊匹配
            for key, concept_path in keyword_mapping.items():
                if key in keyword_lower or keyword_lower in key:
                    matched_concepts.append(concept_path)
        
            # 添加概念板块的股票
            for concept_path in matched_concepts:
                if len(concept_path) == 2 and concept_path[0] == "概念板块":
                    concept_name = concept_path[1]
                    concept_stocks = self.stock_pool.get("概念板块", {}).get(concept_name, [])
                    for stock_info in concept_stocks:
                        if isinstance(stock_info, dict) and 'code' in stock_info:
                            related_stocks.append({
                                'code': stock_info['code'],
                                'name': stock_info['name'],
                                'industry': concept_name,
                                'concept': [concept_name],
                                'market_cap': 0,
                                'pe_ratio': 0,
                                'pb_ratio': 0,
                                'match_score': 3.0,
                                'match_reason': f'概念板块匹配: {concept_name}'
                            })
        
            # 2. 从全部股票中按名称匹配
            for stock_code, stock_info in all_stocks.items():
                if not isinstance(stock_info, dict):
                    continue
                
                match_score = 0
                match_reasons = []
            
                # 公司名称匹配
                name = stock_info.get('name', '').lower()
                if keyword_lower in name:
                    match_score += 2
                    match_reasons.append('公司名称匹配')
            
                # 🔧 新增：关键词相关性匹配
                water_keywords = ['水电', '水利', '水务', '大坝', '电力', '能源', '西藏', '四川']
                if any(kw in name for kw in water_keywords):
                    if '雅鲁藏布' in keyword_lower or '水电' in keyword_lower:
                        match_score += 1.5
                        match_reasons.append('水电相关匹配')
            
                if match_score > 0:
                    # 避免重复
                    if not any(s['code'] == stock_code for s in related_stocks):
                        stock_result = {
                            'code': stock_code,
                            'name': stock_info.get('name', f'股票{stock_code}'),
                            'industry': '未知行业',
                            'concept': [],
                            'market_cap': 0,
                            'pe_ratio': 0,
                            'pb_ratio': 0,
                            'match_score': match_score,
                            'match_reason': '; '.join(match_reasons)
                        }
                        related_stocks.append(stock_result)
        
            # 3. 如果还是没找到，从概念板块模糊匹配
            if not related_stocks:
                concept_boards = self.stock_pool.get("概念板块", {})
                search_concepts = ['水电水利', '新能源', '电力设备']
            
                if '水电' in keyword_lower or '雅鲁藏布' in keyword_lower:
                    for concept_name in search_concepts:
                        stocks_list = concept_boards.get(concept_name, [])
                        for stock_info in stocks_list[:5]:  # 每个概念最多取5只
                            if isinstance(stock_info, dict) and 'code' in stock_info:
                                related_stocks.append({
                                    'code': stock_info['code'],
                                    'name': stock_info['name'],
                                    'industry': concept_name,
                                    'concept': [concept_name],
                                    'market_cap': 0,
                                    'pe_ratio': 0,
                                    'pb_ratio': 0,
                                    'match_score': 1.5,
                                    'match_reason': f'概念相关: {concept_name}'
                                })
        
            # 按匹配分数排序
            related_stocks.sort(key=lambda x: x['match_score'], reverse=True)
            result = related_stocks[:max_results]
        
            logger.info(f"找到 {len(result)} 只相关股票")
            return result
        
        except Exception as e:
            logger.error(f"查找相关股票失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_stock_info(self, stock_code):
        """获取股票基本信息"""
        return self.stock_pool.get("全部股票", {}).get(stock_code, {})

    def save_stock_pool(self):
        """保存股票池到文件"""
        try:
            with open(STOCK_POOL_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.stock_pool, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 股票池已保存到: {STOCK_POOL_PATH}")
        except Exception as e:
            logger.error(f"❌ 保存股票池失败: {e}")
    
    def load_stock_pool(self):
        """从文件加载股票池"""
        try:
            if os.path.exists(STOCK_POOL_PATH):
                with open(STOCK_POOL_PATH, 'r', encoding='utf-8') as f:
                    self.stock_pool = json.load(f)
                logger.info("✅ 股票池加载成功")
            else:
                logger.info("📝 股票池文件不存在，将创建新的股票池")
                self.build_stock_pool()
        except Exception as e:
            logger.error(f"❌ 加载股票池失败: {e}")
            self.build_stock_pool()
    
    def _create_fallback_pool(self):
        """创建备用股票池"""
        logger.info("🔄 创建备用股票池...")
        
        fallback_stocks = {
            "000001": {"name": "平安银行", "code": "000001"},
            "000002": {"name": "万科A", "code": "000002"},
            "000858": {"name": "五粮液", "code": "000858"},
            "002594": {"name": "比亚迪", "code": "002594"},
            "300750": {"name": "宁德时代", "code": "300750"}
        }
        
        self.stock_pool = {
            "基础信息": {
                "总股票数": len(fallback_stocks),
                "更新时间": datetime.now().isoformat(),
                "备注": "备用股票池"
            },
            "全部股票": fallback_stocks,
            "概念板块": {
                "新能源汽车": [
                    {"code": "002594", "name": "比亚迪"},
                    {"code": "300750", "name": "宁德时代"}
                ]
            },
            "热门关键词": {
                "新能源": ["概念板块", "新能源汽车"],
                "汽车": ["概念板块", "新能源汽车"]
            }
        }
        
        self.save_stock_pool()
    
    def update_daily_data(self):
        """每日更新股票数据"""
        logger.info("📈 开始每日数据更新...")
        
        # 这里可以添加每日价格、成交量等数据的更新
        # 由于akshare有访问频率限制，建议分批处理
        
        self.last_update = datetime.now()
        logger.info("✅ 每日数据更新完成")