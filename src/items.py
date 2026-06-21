"""
Scrapy 风格的 Item 数据结构定义
定义历史记录和搜索结果的数据字段
"""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class HistoryItem:
    """浏览历史记录 Item"""
    title: str = ""                       # 视频标题
    author: str = ""                      # UP 主或来源
    url: str = ""                         # 详情页 URL
    section_date: str = ""                # 所属时间区块：今天/近一周/一周前
    display_watch_time: str = ""          # 页面展示的观看时间
    normalized_watch_time: str = ""       # 规范化观看时间
    watch_progress: str = ""              # 观看进度
    video_duration: str = ""              # 视频总时长

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchItem:
    """搜索结果 Item"""
    title: str = ""                       # 视频标题
    author: str = ""                      # UP 主
    url: str = ""                         # 详情页 URL
    play_count: str = ""                  # 播放量（原始文本）
    play_count_num: int = 0               # 播放量（数值）
    danmu_count: str = ""                 # 弹幕数（原始文本）
    danmu_count_num: int = 0              # 弹幕数（数值）
    video_duration: str = ""              # 视频时长
    display_publish_time: str = ""        # 页面展示发布时间
    normalized_publish_date: str = ""     # 规范化发布日期
    hot_score: int = 0                    # 热度指标：播放量 + 弹幕数 * 10

    def to_dict(self) -> dict:
        return asdict(self)