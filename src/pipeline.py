"""
Pipeline 数据清洗管道
负责数据去重、空值处理、中文数字单位转换、时间规范化、排序、热度指标计算
以及 CSV / JSON 双格式输出
"""
import os
import csv
import re
from datetime import datetime, timedelta


class BasePipeline:
    """Pipeline 基类"""

    @staticmethod
    def _convert_chinese_number(text: str) -> int:
        """
        转换中文数字单位：
        36.2万 → 362000
        1.5亿 → 150000000
        1234 → 1234
        """
        if not text:
            return 0
        text = text.strip().replace(",", "").replace(" ", "").replace("\u3000", "")

        # 提取数字部分
        match = re.search(r"([\d.]+)\s*([万亿])?", text)
        if not match:
            # 纯数字
            try:
                return int(float(text))
            except ValueError:
                return 0

        num = float(match.group(1))
        unit = match.group(2) or ""

        if unit == "亿":
            return int(num * 100000000)
        if unit == "万":
            return int(num * 10000)
        return int(num)

    @staticmethod
    def _normalize_time(text: str) -> str:
        """
        规范化时间字段
        将相对时间转换为标准格式 YYYY-MM-DD HH:MM
        """
        if not text:
            return ""
        text = text.strip()
        now = datetime.now()

        # 今天 HH:MM
        m = re.search(r"今天\s*(\d{1,2}:\d{2})", text)
        if m:
            return now.strftime("%Y-%m-%d ") + m.group(1)

        # 昨天 HH:MM
        m = re.search(r"昨天\s*(\d{1,2}:\d{2})", text)
        if m:
            return (now - timedelta(days=1)).strftime("%Y-%m-%d ") + m.group(1)

        # 昨天（不带时间）
        if text.strip() == "昨天":
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")

        # 前天（不带时间）
        if text.strip() == "前天":
            return (now - timedelta(days=2)).strftime("%Y-%m-%d")

        # X分钟前
        m = re.search(r"(\d+)\s*分钟前", text)
        if m:
            return (now - timedelta(minutes=int(m.group(1)))).strftime("%Y-%m-%d %H:%M")

        # X小时前
        m = re.search(r"(\d+)\s*小时前", text)
        if m:
            return (now - timedelta(hours=int(m.group(1)))).strftime("%Y-%m-%d %H:%M")

        # X天前
        m = re.search(r"(\d+)\s*天前", text)
        if m:
            return (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

        # 刚刚
        if "刚刚" in text:
            return now.strftime("%Y-%m-%d %H:%M")

        # YYYY-MM-DD
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if m:
            return m.group(1)

        # YYYY-MM-DD HH:MM
        m = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})", text)
        if m:
            return m.group(1)

        # M-D 格式（如 1-15）
        m = re.search(r"(\d{1,2})-(\d{1,2})", text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = now.year
            # 如果月份大于当前月份，说明是去年
            if month > now.month:
                year -= 1
            return f"{year}-{month:02d}-{day:02d}"

        return text


class HistoryPipeline(BasePipeline):
    """历史记录数据清洗管道"""

    def process(self, items: list) -> list:
        """
        清洗历史记录数据：
        1. 去重
        2. 空值处理
        3. 规范化观看时间
        4. 按观看时间排序
        """
        if not items:
            print("[Pipeline] 历史记录数据为空")
            return []

        # 1. 去重（按标题 + UP 主）
        seen = set()
        unique = []
        for item in items:
            key = (item.title, item.author)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        print(f"[Pipeline] 历史记录去重：{len(items)} → {len(unique)}")

        # 2. 空值处理
        for item in unique:
            item.title = item.title or "未知标题"
            item.author = item.author or "未知UP主"
            item.url = item.url or ""
            item.section_date = item.section_date or "未知"
            item.display_watch_time = item.display_watch_time or ""
            item.watch_progress = item.watch_progress or ""
            item.video_duration = item.video_duration or ""

        # 3. 规范化观看时间
        for item in unique:
            item.normalized_watch_time = self._normalize_time(item.display_watch_time)

        # 4. 按观看时间排序（规范化后的时间逆序）
        def sort_key(item):
            t = item.normalized_watch_time
            if t:
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(t, fmt)
                    except ValueError:
                        continue
            # 未识别时间的排在最后
            return datetime.min

        unique.sort(key=sort_key, reverse=True)

        print(f"[Pipeline] 历史记录清洗完成，共 {len(unique)} 条")
        return unique

    def save(self, items: list, prefix: str = "history_last_week"):
        """保存清洗后的历史记录到 CSV 和 JSON"""
        os.makedirs("results", exist_ok=True)

        # 保存 CSV
        csv_path = f"results/{prefix}_cleaned.csv"
        if items:
            fieldnames = [
                "视频标题", "UP主", "详情页URL", "所属时间区块",
                "页面展示观看时间", "规范化观看时间", "观看进度", "视频总时长"
            ]
            field_keys = [
                "title", "author", "url", "section_date",
                "display_watch_time", "normalized_watch_time", "watch_progress", "video_duration"
            ]
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for item in items:
                    d = item.to_dict()
                    writer.writerow([d.get(k, "") for k in field_keys])
            print(f"[Pipeline] 已保存: {csv_path}")
        return csv_path


class SearchPipeline(BasePipeline):
    """搜索结果数据清洗管道"""

    def process(self, items: list) -> list:
        """
        清洗搜索结果数据：
        1. 去重
        2. 空值处理
        3. 中文数字单位转换
        4. 时间规范化
        5. 热度指标计算
        6. 按热度排序
        """
        if not items:
            print("[Pipeline] 搜索结果数据为空")
            return []

        # 1. 去重
        seen = set()
        unique = []
        for item in items:
            key = (item.title, item.author)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        print(f"[Pipeline] 搜索结果去重：{len(items)} → {len(unique)}")

        # 2. 空值处理
        for item in unique:
            item.title = item.title or "未知标题"
            item.author = item.author or "未知UP主"
            item.url = item.url or ""
            item.play_count = item.play_count or "0"
            item.danmu_count = item.danmu_count or "0"
            item.video_duration = item.video_duration or "无显示内容"
            item.display_publish_time = item.display_publish_time or "无显示内容"

        # 3. 中文数字单位转换
        for item in unique:
            item.play_count_num = self._convert_chinese_number(item.play_count)
            item.danmu_count_num = self._convert_chinese_number(item.danmu_count)

        # 4. 时间规范化
        for item in unique:
            item.normalized_publish_date = self._normalize_time(item.display_publish_time)

        # 5. 热度指标：播放量 + 弹幕数 * 10
        for item in unique:
            item.hot_score = item.play_count_num + item.danmu_count_num * 10

        # 6. 按热度降序排列
        unique.sort(key=lambda x: x.hot_score, reverse=True)

        print(f"[Pipeline] 搜索结果清洗完成，共 {len(unique)} 条")
        return unique

    def save(self, items: list, prefix: str = "search"):
        """保存清洗后的搜索结果到 CSV 和 JSON"""
        os.makedirs("results", exist_ok=True)

        # 保存 CSV
        csv_path = f"results/{prefix}_cleaned.csv"
        if items:
            # fieldnames = [
            #     "视频标题", "UP主", "详情页URL", "播放量", "播放量(数值)",
            #     "弹幕数", "弹幕数(数值)", "视频时长", "页面展示发布时间",
            #     "规范化发布日期", "热度指标"
            # ]
            # field_keys = [
            #     "title", "author", "url", "play_count", "play_count_num",
            #     "danmu_count", "danmu_count_num", "video_duration", "display_publish_time",
            #     "normalized_publish_date", "hot_score"
            # ]

            fieldnames = [
                "视频标题", "UP主", "详情页URL", "播放量",
                "弹幕数", "视频时长", "页面展示发布时间",
                "规范化发布日期", "热度指标"
            ]
            field_keys = [
                "title", "author", "url", "play_count_num",
                "danmu_count_num", "video_duration", "display_publish_time",
                "normalized_publish_date", "hot_score"
            ]

            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for item in items:
                    d = item.to_dict()
                    writer.writerow([d.get(k, "") for k in field_keys])
            print(f"[Pipeline] 已保存: {csv_path}")
        return csv_path
