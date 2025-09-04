# modules/data_fetcher.py - 集成版
"""
股票数据获取模块 - 基于 test.py 的稳定版本
"""

import requests
import akshare as ak
import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import REQUEST_TIMEOUT, REQUEST_DELAY

logger = logging.getLogger(__name__)

class StockDataFetcher:
    """股票数据获取器 - 多源稳定版"""
    
    def __init__(self):
        self.cache = {}
        self.last_fetch_time = {}
        self.cache_duration = timedelta(minutes=5)  # 缓存5分钟

    def _prefix(self, code: str) -> str:
        """A股代码转交易所前缀：sh/sz（含科创板）"""
        code = str(code)
        if code.startswith(("5", "6", "9", "688")):
            return "sh"
        return "sz"

    def _fetch_rt_sina(self, code: str) -> dict:
        """新浪实时接口（优先）"""
        url = f"https://hq.sinajs.cn/list={self._prefix(code)}{code}"
        headers = {"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.encoding = "gbk"
            text = r.text
            if "=" not in text:
                return {}
            data = text.split('="')[-1].strip('";\n')
            if not data:
                return {}
            arr = data.split(",")
            if len(arr) < 32:
                return {}
                
            def f(i, default=np.nan):
                try:
                    return float(arr[i])
                except Exception:
                    return default
                    
            price = f(3)
            pre_close = f(2)
            change_pct = ((price / pre_close - 1) * 100.0) if pre_close and not np.isnan(pre_close) and pre_close != 0 else np.nan
            
            return {
                "code": code,
                "name": arr[0],
                "price": price,
                "change_pct": change_pct,
                "volume": f(8),      # 股
                "turnover": f(9),    # 元
                "open": f(1),
                "high": f(4),
                "low": f(5),
                "pre_close": pre_close,
                "update_time": f"{arr[30]} {arr[31]}",
            }
        except Exception as e:
            logger.warning(f"新浪实时数据获取失败 {code}: {e}")
            return {}

    def _fetch_rt_tencent(self, code: str) -> dict:
        """腾讯实时接口（备选）"""
        url = f"http://qt.gtimg.cn/q={self._prefix(code)}{code}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.encoding = "gbk"
            text = r.text
            if "=" not in text:
                return {}
            payload = text.split('="')[-1].strip('";\n')
            arr = payload.split("~")
            if len(arr) < 32:
                return {}
                
            def f(idx, default=np.nan):
                try:
                    return float(arr[idx])
                except Exception:
                    return default
                    
            name = arr[1]
            price = f(3)
            pre_close = f(4)
            open_ = f(5)
            vol_hand = f(36 if len(arr) > 36 else 8)
            amt = f(37 if len(arr) > 37 else 9)
            date = arr[30] if len(arr) > 31 else ""
            tm = arr[31] if len(arr) > 31 else ""
            
            change_pct = ((price / pre_close - 1) * 100.0) if pre_close and not np.isnan(pre_close) and pre_close != 0 else np.nan
            
            return {
                "code": code,
                "name": name,
                "price": price,
                "change_pct": change_pct,
                "volume": vol_hand * 100.0 if not np.isnan(vol_hand) else np.nan,  # 手->股
                "turnover": amt,
                "open": open_,
                "high": f(33 if len(arr) > 33 else 41, np.nan),
                "low": f(34 if len(arr) > 34 else 42, np.nan),
                "pre_close": pre_close,
                "update_time": f"{date} {tm}".strip(),
            }
        except Exception as e:
            logger.warning(f"腾讯实时数据获取失败 {code}: {e}")
            return {}

    def get_real_time_data(self, stock_code):
        """
        获取实时股票数据 - 多源策略
        """
        try:
            logger.info(f"⚡ 获取实时数据: {stock_code}")
            
            # 检查缓存
            cache_key = f"rt_{stock_code}"
            if self._check_cache(cache_key):
                return self.cache[cache_key]
            
            # 策略1：新浪实时
            rt = self._fetch_rt_sina(stock_code)
            if rt and rt.get('price') and not np.isnan(rt.get('price')):
                self.cache[cache_key] = rt
                self.last_fetch_time[cache_key] = datetime.now()
                logger.info(f"✅ 新浪实时数据: {rt['name']} {rt['price']}")
                return rt
            
            time.sleep(REQUEST_DELAY)
            
            # 策略2：腾讯实时
            rt = self._fetch_rt_tencent(stock_code)
            if rt and rt.get('price') and not np.isnan(rt.get('price')):
                self.cache[cache_key] = rt
                self.last_fetch_time[cache_key] = datetime.now()
                logger.info(f"✅ 腾讯实时数据: {rt['name']} {rt['price']}")
                return rt
            
            time.sleep(REQUEST_DELAY)
            
            # 策略3：akshare（最后回退）
            try:
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == stock_code]
                if not row.empty:
                    r = row.iloc[0]
                    rt = {
                        "code": stock_code,
                        "name": str(r.get("名称", "")),
                        "price": float(r.get("最新价", 0)),
                        "change_pct": float(r.get("涨跌幅", 0)),
                        "volume": float(r.get("成交量", 0)),
                        "turnover": float(r.get("成交额", 0)),
                        "open": float(r.get("今开", 0)),
                        "high": float(r.get("最高", 0)),
                        "low": float(r.get("最低", 0)),
                        "pre_close": float(r.get("昨收", 0)),
                        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    self.cache[cache_key] = rt
                    self.last_fetch_time[cache_key] = datetime.now()
                    logger.info(f"✅ akshare实时数据: {rt['name']} {rt['price']}")
                    return rt
            except Exception as e:
                logger.warning(f"akshare实时数据获取失败: {e}")
            
            # 如果都失败，返回空字典
            logger.error(f"❌ 所有实时数据源都失败: {stock_code}")
            return {}
                
        except Exception as e:
            logger.error(f"❌ 获取实时数据异常 {stock_code}: {e}")
            return {}

    def get_stock_data(self, stock_code, period="daily", count=30):
        """
        获取股票历史数据
        """
        try:
            logger.info(f"📊 获取股票历史数据: {stock_code}")
            
            # 检查缓存
            cache_key = f"hist_{stock_code}_{period}_{count}"
            if self._check_cache(cache_key):
                return self.cache[cache_key]
            
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=count * 2)).strftime("%Y%m%d")
            
            try:
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"  # 前复权
                )
                
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df = df.tail(count).copy()
                    # 数据类型转换
                    for c in ["开盘", "收盘", "最高", "最低", "成交量", "成交额"]:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                    
                    self.cache[cache_key] = df
                    self.last_fetch_time[cache_key] = datetime.now()
                    logger.info(f"✅ 成功获取 {len(df)} 条历史数据")
                    return df
                
            except Exception as e:
                logger.warning(f"历史数据获取失败: {e}")
            
            logger.warning(f"⚠️ 未获取到历史数据: {stock_code}")
            return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ 获取历史数据失败 {stock_code}: {e}")
            return pd.DataFrame()

    def calculate_technical_indicators(self, df):
        """
        计算技术指标 - 集成你的 test.py 逻辑
        """
        if df.empty or len(df) < 20:
            return {}
            
        try:
            close = df["收盘"].astype(float)
            high = df["最高"].astype(float)
            low = df["最低"].astype(float)
            vol = df["成交量"].astype(float)

            indicators = {}
            
            # 移动平均
            indicators["ma5"] = float(close.rolling(5).mean().iloc[-1])
            indicators["ma20"] = float(close.rolling(20).mean().iloc[-1])

            # RSI
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            indicators["rsi"] = float((100 - 100 / (1 + rs)).iloc[-1])

            # 布林带
            ma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            upper = ma20 + 2 * std20
            lower = ma20 - 2 * std20
            indicators["boll_upper"] = float(upper.iloc[-1])
            indicators["boll_mid"] = float(ma20.iloc[-1])
            indicators["boll_lower"] = float(lower.iloc[-1])
            
            denom = (upper - lower).iloc[-1]
            indicators["boll_pos"] = float((close.iloc[-1] - lower.iloc[-1]) / denom) if denom and not np.isnan(denom) else 0.5

            # 动量和波动率
            indicators["momentum_5"] = float(close.iloc[-1] / close.iloc[-6] - 1) if len(close) > 5 else 0.0
            ret = close.pct_change().dropna()
            indicators["volatility"] = float(ret.std() * np.sqrt(252)) if len(ret) > 2 else 0.0

            # 量比
            vol_ma20 = vol.rolling(20).mean().iloc[-1]
            indicators["volume_ratio"] = float(vol.iloc[-1] / vol_ma20) if vol_ma20 and not np.isnan(vol_ma20) else 1.0
            
            return indicators
            
        except Exception as e:
            logger.error(f"技术指标计算失败: {e}")
            return {}

    def _check_cache(self, cache_key):
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False
        
        if cache_key not in self.last_fetch_time:
            return False
        
        if datetime.now() - self.last_fetch_time[cache_key] > self.cache_duration:
            return False
        
        return True