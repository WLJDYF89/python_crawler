"""
主入口程序
串联：登录 → 请求调度 → 字段解析 → 数据清洗 → 保存输出
模拟 Scrapy 框架的完整处理链
"""
import sys
import os
import time

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from src.middleware import LoginStateMiddleware
from src.login import BilibiliLogin
from src.crawler import CrawlerScheduler


def main():
    print("=" * 60)
    print("  Bilibili 登录态数据采集系统")
    print("  基于 Selenium + Scrapy 架构思想")
    print("=" * 60)
    print("  任务一：个人浏览历史记录采集")
    print("  任务二：VibeCoding 搜索结果采集")
    print("=" * 60)

# ...
# 爬虫

    driver = None

    try:
        # ========== 阶段1：初始化浏览器 ==========
        print("\n[Main] 阶段1：初始化浏览器驱动...")
        driver = webdriver.Chrome()
        print("[Main] Chrome 浏览器已启动")

        # ========== 阶段2：登录态中间件初始化 ==========
        mw = LoginStateMiddleware(driver)
        mw.inject_request_headers()

        # ========== 阶段3：登录态处理 ==========
        print("\n[Main] 阶段2：登录态处理...")

        # 尝试 Cookie 恢复
        logged_in = False
        if mw.load_cookies():
            if mw.check_login():
                print("[Main] Cookie 有效，已恢复登录状态")
                logged_in = True
            else:
                print("[Main] Cookie 已过期，需要重新登录")

        # Cookie 无效则自动登录
        if not logged_in:
            login_handler = BilibiliLogin(driver)
            logged_in = login_handler.simulated_click()
            # logged_in = login_handler.login()

            if not logged_in:
                print("\n[Main] 自动登录失败，尝试手动登录...")
                print("请在浏览器中完成登录（扫码或其他方式），等待 120 秒...")
                driver.get("https://passport.bilibili.com/login")

                start = time.time()
                while time.time() - start < 120:
                    if mw.check_login():
                        logged_in = True
                        break
                    time.sleep(2)
                if not logged_in:
                    raise RuntimeError("登录超时，请重试")
            mw.save_cookies()

        print("[Main] 登录状态确认成功！")

        time.sleep(3)

        # ========== 阶段4：请求调度与采集 ==========
        print("\n[Main] 阶段3：开始数据采集...")
        scheduler = CrawlerScheduler(driver)

        # 任务一：历史记录
        history_items = scheduler.run_task1_history()

        # 任务二：搜索结果
        search_items = scheduler.run_task2_search()

        # ========== 阶段5：输出汇总 ==========
        print("\n" + "=" * 60)
        print("  全部任务完成！")
        print("=" * 60)
        print(f"  历史记录（近一周）: {len(history_items)} 条")
        print(f"  搜索结果（vibecoding）: {len(search_items)} 条")
        print()
        print("  输出文件：")
        print("    raw_html/bilibili_history.html")
        print("    raw_html/bilibili_search_vibecoding.html")
        print("    results/history_raw.json")
        print("    results/history_last_week_cleaned.csv")
        print("    results/search_raw.json")
        print("    results/search_cleaned.csv")
        print("=" * 60)

    except Exception as e:
        print(f"\n[Main] 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if driver:
            driver.quit()
            print("[Main] 浏览器已关闭")


if __name__ == "__main__":
    main()
