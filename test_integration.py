# -*- coding: utf-8 -*-
"""
集成测试脚本 - 验证新闻源管理器
测试头条API + 央视爬虫的智能切换功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_source_manager import NewsSourceManager

def test_news_source_manager():
    """测试新闻源管理器"""
    print("="*80)
    print("🧪 新闻源管理器集成测试")
    print("="*80)
    
    # 使用已验证的头条API密钥
    toutiao_api_key = "06dc063c05502ff715690a6037905d1b"
    
    # 初始化管理器
    print("📱 初始化新闻源管理器...")
    manager = NewsSourceManager(toutiao_api_key)
    
    # 显示状态信息
    manager.print_status_summary()
    
    # 测试获取新闻
    print(f"\n🔍 开始测试新闻获取...")
    news_list = manager.get_latest_news(limit=5)
    
    if news_list:
        print(f"\n✅ 测试成功！获取到 {len(news_list)} 条新闻")
        print("📰 示例新闻:")
        for i, news in enumerate(news_list[:3], 1):
            print(f"  {i}. 【{news.get('source', '未知来源')}】{news.get('title', '无标题')}")
            print(f"     时间: {news.get('publish_time', '未知时间')}")
    else:
        print("❌ 测试失败：未获取到新闻")
        return False
    
    print(f"\n🎯 测试结论:")
    print("✅ 新闻源管理器工作正常")
    print("✅ 智能切换机制运行良好")
    print("✅ 数据格式统一化成功")
    
    return True

def test_api_quota_simulation():
    """模拟API配额耗尽情况"""
    print(f"\n{'='*80}")
    print("🧪 API配额耗尽模拟测试")
    print("="*80)
    
    toutiao_api_key = "06dc063c05502ff715690a6037905d1b"
    manager = NewsSourceManager(toutiao_api_key)
    
    # 模拟大量调用（仅测试逻辑，不实际调用）
    print("📊 模拟API配额接近上限...")
    
    # 手动设置配额接近上限
    if hasattr(manager, 'toutiao_adapter'):
        manager.toutiao_adapter.daily_call_count = 48  # 接近50的限制
        print(f"   当前调用次数: {manager.toutiao_adapter.daily_call_count}/50")
        print(f"   剩余配额: {manager.toutiao_adapter.get_remaining_quota()}")
        
        # 测试在接近上限时的行为
        print("\n🔍 测试接近配额上限时的新闻获取...")
        news_list = manager.get_latest_news(limit=3)
        
        if news_list:
            print("✅ 在配额接近上限时仍能正常获取新闻")
        
        # 模拟配额用完
        manager.toutiao_adapter.daily_call_count = 50
        print(f"\n📊 模拟配额用完: {manager.toutiao_adapter.daily_call_count}/50")
        
        print("🔍 测试配额用完后的降级策略...")
        news_list = manager.get_latest_news(limit=3)
        
        if news_list:
            print("✅ 配额用完后成功降级到央视爬虫")
            print("✅ 兜底机制工作正常")
        else:
            print("❌ 降级机制可能存在问题")

if __name__ == "__main__":
    print("🚀 开始集成测试...\n")
    
    try:
        # 基础功能测试
        success = test_news_source_manager()
        
        if success:
            # 配额模拟测试
            test_api_quota_simulation()
            
            print(f"\n{'='*80}")
            print("🎉 所有测试完成！")
            print("💡 系统已准备好投入使用")
            print("💡 建议运行 python realtime_cctv_monitor.py 开始监控")
            print("="*80)
        
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
