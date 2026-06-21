"""
Crawler 请求调度器模块
模拟 Scrapy 的 Engine + Scheduler 调度流程：
1. 调度请求（先历史记录，再搜索结果）
2. 保存页面 HTML 源码到 raw_html/
3. 调用 Parser 解析字段
4. 调用 Pipeline 清洗保存
"""
import os
import time

from .parser import HistoryParser, SearchParser
from .pipeline import HistoryPipeline, SearchPipeline


class CrawlerScheduler:
    """
    采集调度器
    负责协调请求调度、HTML 保存、字段解析、数据清洗全流程
    """

    def __init__(self, driver):
        self.driver = driver
        self.history_parser = HistoryParser(driver)
        self.search_parser = SearchParser(driver)
        self.history_pipeline = HistoryPipeline()
        self.search_pipeline = SearchPipeline()

    def run_task1_history(self) -> list:
        """
        任务一：个人历史记录采集
        流程：访问页面 → 滚动加载 → 解析字段 → 保存 HTML → 清洗 → 保存
        """
        print("\n" + "=" * 50)
        print("  [Crawler] 任务一：个人浏览历史记录采集")
        print("=" * 50)

        # 1. 解析字段（内部会导航到历史页面并滚动加载）
        raw_items = self.history_parser.parse()

        # 2. 保存原始 HTML 源码（在 parse 之后，此时已滚动加载完毕）
        os.makedirs("raw_html", exist_ok=True)
        html_path = os.path.join("raw_html", "bilibili_history.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"[Crawler] HTML 源码已保存: {html_path}")

        # 3. 保存原始解析数据
        self._save_raw_json("history_raw.json", raw_items)

        # 4. 清洗
        cleaned_items = self.history_pipeline.process(raw_items)

        # 5. 保存
        self.history_pipeline.save(cleaned_items, "history_last_week")

        return cleaned_items

    def run_task2_search(self) -> list:
        """
        任务二：VibeCoding 搜索结果采集
        流程：搜索 → 滚动加载 → 解析字段 → 保存 HTML → 清洗 → 保存
        """
        print("\n" + "=" * 50)
        print("  [Crawler] 任务二：VibeCoding 搜索结果采集")
        print("=" * 50)

        # 1. 解析字段（内部会搜索并滚动加载）
        raw_items = self.search_parser.parse()

        # 2. 保存原始 HTML 源码（在 parse 之后，此时已滚动加载完毕）
        os.makedirs("raw_html", exist_ok=True)
        html_path = os.path.join("raw_html", "bilibili_search_vibecoding.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"[Crawler] HTML 源码已保存: {html_path}")

        # 3. 保存原始解析数据
        self._save_raw_json("search_raw.json", raw_items)

        # 4. 清洗
        cleaned_items = self.search_pipeline.process(raw_items)

        # 5. 保存
        self.search_pipeline.save(cleaned_items, "search")

        return cleaned_items

    def _save_raw_json(self, filename: str, items: list):
        """保存原始解析数据到 results/ 目录"""
        import json
        os.makedirs("results", exist_ok=True)
        path = os.path.join("results", filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in items], f, ensure_ascii=False, indent=2)
        print(f"[Crawler] 原始数据已保存: {path}")
