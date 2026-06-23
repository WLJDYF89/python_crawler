"""
Parser 解析模块
负责从页面 DOM 中提取视频信息字段，输出 Item 对象
"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .items import HistoryItem, SearchItem


class HistoryParser:
    """
    历史记录页面解析器
    解析 https://www.bilibili.com/history 页面中的视频信息
    """

    HISTORY_URL = "https://www.bilibili.com/history"

    def __init__(self, driver):
        self.driver = driver


    """
    解析历史记录浏览页面，返回 HistoryItem 列表
    """
    def parse(self) -> list:
        """
        解析历史记录页面，返回 HistoryItem 列表
        """
        items = []

        if "history" not in self.driver.current_url:
            self.driver.get(self.HISTORY_URL)
            time.sleep(5)

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    ".history-list, [class*='history-'], .bili-video-card"
                ))
            )
        except TimeoutException:
            print("[Parser] 历史记录列表加载超时，尝试继续解析...")

        self._scroll_to_load()

        timeline_items = self.driver.find_elements(By.CSS_SELECTOR, ".timeline-item.history-timeline-item")
        if not timeline_items:
            timeline_items = self.driver.find_elements(By.CSS_SELECTOR, "[class*='timeline-item']")

        print(f"[Parser] 发现 {len(timeline_items)} 个时间分区")

        for tl_item in timeline_items:
            try:
                section_date = ""
                try:
                    st = tl_item.find_element(By.CSS_SELECTOR, ".section-title")
                    section_date = st.text.strip()
                except NoSuchElementException:
                    pass

                if not section_date:
                    continue

                if not self._is_recent(section_date):
                    print(f"[Parser] 跳过非近期分区: {section_date}")
                    continue

                cards = tl_item.find_elements(By.CSS_SELECTOR, ".bili-video-card")
                if not cards:
                    cards = tl_item.find_elements(By.CSS_SELECTOR, ".history-card")

                print(f"[Parser] 分区 '{section_date}' 下有 {len(cards)} 个视频卡片")

                for card in cards:
                    try:
                        item = self._parse_single(card)
                        item.section_date = section_date
                        if item.title:
                            items.append(item)
                    except Exception:
                        continue

            except Exception:
                continue

        print(f"[Parser] 历史记录解析完成，近一周共 {len(items)} 条")
        return items

    # 解析单个视频条目
    def _parse_single(self, el) -> HistoryItem:
        """解析单个视频条目"""
        item = HistoryItem()
        parent = el

        try:
            t = parent.find_element(By.CSS_SELECTOR, ".bili-video-card__title")
            item.title = (t.get_attribute("title") or t.text or "").strip()
        except NoSuchElementException:
            for sel in ["a[title]", ".title", "[class*='title']"]:
                try:
                    t = parent.find_element(By.CSS_SELECTOR, sel)
                    item.title = (t.get_attribute("title") or t.text or "").strip()
                    if item.title:
                        break
                except NoSuchElementException:
                    continue

        try:
            author_el = parent.find_element(By.CSS_SELECTOR, ".bili-video-card__author")
            spans = author_el.find_elements(By.CSS_SELECTOR, "span")
            for span in spans:
                text = span.text.strip()
                if text:
                    item.author = text
                    break
        except NoSuchElementException:
            for sel in [".up-name", "[class*='author']"]:
                try:
                    a = parent.find_element(By.CSS_SELECTOR, sel)
                    item.author = a.text.strip()
                    if item.author:
                        break
                except NoSuchElementException:
                    continue

        for sel in ["a[href*='video/BV']", "a[href*='bv/']", "a[href*='cheese/play']"]:
            try:
                link = parent.find_element(By.CSS_SELECTOR, sel)
                href = link.get_attribute("href") or ""
                if href and ("bilibili.com/video" in href or "bilibili.com/cheese" in href):
                    item.url = href
                    break
            except NoSuchElementException:
                continue

        if not item.url:
            try:
                link = parent.find_element(By.CSS_SELECTOR, "a[href*='video']")
                href = link.get_attribute("href") or ""
                if href and "bilibili.com" in href:
                    item.url = href
            except NoSuchElementException:
                pass

        try:
            corner = parent.find_element(By.CSS_SELECTOR, ".bili-video-card__corner")
            item.display_watch_time = corner.text.strip()
        except NoSuchElementException:
            pass

        try:
            stats = parent.find_element(By.CSS_SELECTOR, ".bili-cover-card__stats")
            stat_spans = stats.find_elements(By.CSS_SELECTOR, "span")
            for span in stat_spans:
                text = span.text.strip()
                if "/" in text:
                    parts = text.split("/")
                    if len(parts) == 2:
                        item.watch_progress = parts[0].strip()
                        item.video_duration = parts[1].strip()
                    break
        except NoSuchElementException:
            pass

        return item

    # 判断是否近一周的数据
    def _is_recent(self, section_date: str) -> bool:
        """判断是否近一周的数据"""
        if not section_date:
            return False
        import re
        # 今天、近一周、本周等标记
        if re.search(r"今天|今日|近一周|本周|7天内", section_date):
            return True
        # 昨天、前天
        if re.search(r"昨天|前天", section_date):
            return True
        return False

    # 滚动加载更多历史记录
    def _scroll_to_load(self):
        """滚动加载更多历史记录，遇到“一周前”标记则停止"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        no_change_count = 0
        reached_limit = False

        while scroll_attempts < 15 and no_change_count < 3 and not reached_limit:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
            else:
                no_change_count = 0
                last_height = new_height
            scroll_attempts += 1

            # 检查是否已滚动到“一周前”标记，确保“近一周”内容全部加载
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "一周前" in page_text:
                    reached_limit = True
                    print("[Parser] 已滚动到“一周前”，停止加载")
            except Exception:
                pass

        print(f"[Parser] 历史记录滚动加载完成 (共 {scroll_attempts} 次)")


class SearchParser:
    """
    搜索结果解析器
    解析搜索「vibecoding」的结果页面
    """

    SEARCH_KEYWORD = "vibecoding"
    SEARCH_URL = f"https://search.bilibili.com/all?keyword={SEARCH_KEYWORD}&order=totalrank"

    def __init__(self, driver):
        self.driver = driver

    """
    解析搜索结果页面，返回 SearchItem 列表
    """
    def parse(self) -> list:
        """
        解析搜索结果页，返回 SearchItem 列表
        只采集首屏数据，不滚动加载更多
        """
        items = []

        try:
            print(f"[Parser] 正在搜索: {self.SEARCH_KEYWORD}")
            self.driver.get("https://www.bilibili.com/")
            time.sleep(3)

            search_box_selectors = [
                ".nav-search-input",
                ".search-input-el",
                "input[placeholder*='搜索']",
                "#nav-searchform input",
            ]
            search_box = None
            for sel in search_box_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    print(f"[Parser] 找到搜索框 (via {sel})")
                    break
                except TimeoutException:
                    continue

            if not search_box:
                print("[Parser] 未找到搜索框，直接访问搜索URL")
                self.driver.get(self.SEARCH_URL)
                time.sleep(5)
            else:
                search_box.click()
                time.sleep(0.3)
                search_box.clear()
                search_box.send_keys(self.SEARCH_KEYWORD)
                time.sleep(1)

                search_box.send_keys(Keys.ESCAPE)
                time.sleep(0.3)

                search_btn_selectors = [
                    ".nav-search-btn",
                    ".search-btn",
                    "[class*='search-btn']",
                ]
                btn_clicked = False
                for sel in search_btn_selectors:
                    try:
                        btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                        btn.click()
                        btn_clicked = True
                        print(f"[Parser] 点击搜索按钮 (via {sel})")
                        break
                    except NoSuchElementException:
                        continue

                if not btn_clicked:
                    search_box.send_keys(Keys.ENTER)
                    print("[Parser] 使用回车键提交搜索")

                time.sleep(5)

                self._handle_new_tab()

        except Exception as e:
            print(f"[Parser] 搜索操作失败: {e}，尝试直接访问搜索URL")
            self.driver.get(self.SEARCH_URL)
            time.sleep(5)

            self._handle_new_tab()

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    ".video-list, .search-page, [class*='video-list'], .search-layout"
                ))
            )
            print("[Parser] 搜索结果已加载")
        except TimeoutException:
            print("[Parser] 搜索结果列表加载超时,尝试继续解析...")
            time.sleep(5)

        self._scroll_to_load_all()

        time.sleep(3)

        # self._pre_render_all_cards()

        video_selectors = [
            ".video-list-item",
            ".search-result-item",
            ".bili-video-card",
            "[class*='video-card']",
            "[class*='video-item']",
            "[class*='result-item']",
        ]


        video_items = []
        for sel in video_selectors:
            video_items = self.driver.find_elements(By.CSS_SELECTOR, sel)
            if video_items:
                print(f"[Parser] 使用选择器 '{sel}' 发现 {len(video_items)} 个视频元素")
                break

        if not video_items:
            print("[Parser] 未找到任何视频元素，尝试从链接提取...")
            video_items = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='video']")

        print(f"[Parser] 搜索结果页面发现 {len(video_items)} 个视频元素")

        for item_el in video_items:
            if len(items) >= 24:
                print(f"[Parser] 已达到目标数量，停止爬取")
                break
            try:
                item = self._parse_single(item_el)
                if item and item.title:
                    items.append(item)
            except Exception as e:
                continue

        print(f"[Parser] 搜索结果解析完成，共 {len(items)} 条")
        return items

    # 解析单个搜索结果卡片
    def _parse_single(self, card) -> SearchItem:
        """解析单个搜索结果卡片"""
        item = SearchItem()

        parent = card
        if card.tag_name == "a":
            try:
                for _ in range(3):
                    parent_el = parent.find_element(By.XPATH, "..")
                    cls = parent_el.get_attribute("class") or ""
                    if "card" in cls or "item" in cls or "video" in cls:
                        parent = parent_el
                        break
                    parent = parent_el
            except Exception:
                pass

        self._ensure_card_rendered(parent)

        # 标题
        title_selectors = [
            ".bili-video-card__info--tit",
            ".video-title",
            ".title",
            "h3",
            "a[href*='video']",
            "[class*='title']",
        ]
        for sel in title_selectors:
            try:
                t = parent.find_element(By.CSS_SELECTOR, sel)
                item.title = (t.get_attribute("title") or t.text or "").strip()
                if item.title:
                    break
            except NoSuchElementException:
                continue

        # UP 主
        author_selectors = [
            ".bili-video-card__info--author",
            ".bili-video-card__info--owner",
            ".up-name",
            "[class*='up-name']",
            "span[class*='author']:not([class*='ico'])",
            "[class*='author']",
        ]
        for sel in author_selectors:
            try:
                elements = parent.find_elements(By.CSS_SELECTOR, sel)
                for a in elements:
                    text = a.text.strip()
                    if text:
                        if " · " in text:
                            text = text.split(" · ")[0].strip()
                        item.author = text
                        break
                if item.author:
                    break
            except NoSuchElementException:
                continue

        if not item.author:
            try:
                all_links = parent.find_elements(By.CSS_SELECTOR, "a")
                for link in all_links:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    if text and "space.bilibili.com" in href:
                        item.author = text
                        break
            except Exception:
                pass

        if not item.author:
            try:
                full_text = parent.text or ""
                import re
                title_text = item.title or ""
                text_after_title = full_text.replace(title_text, "", 1) if title_text else full_text
                lines = [l.strip() for l in text_after_title.split("\n") if l.strip()]
                for line in lines:
                    if line and len(line) < 30 and not line.startswith(("·", "•")) \
                            and "播放" not in line and "弹幕" not in line \
                            and "万" not in line and not re.match(r'^\d', line):
                        item.author = line
                        break
            except Exception:
                pass

        # 详情页 URL
        url_selectors = [
            "a[href*='video/BV']",
            "a[href*='video/av']",
            "a[href*='bv/']",
            "a[href*='cheese/play']",
            "a[href*='video']",
        ]
        for sel in url_selectors:
            try:
                link = parent.find_element(By.CSS_SELECTOR, sel)
                href = link.get_attribute("href") or ""
                if href.startswith("//"):
                    href = "https:" + href
                if href and ("bilibili.com/video" in href or "bilibili.com/cheese" in href):
                    item.url = href
                    break
            except NoSuchElementException:
                continue

        if not item.url and parent.tag_name == "a":
            href = parent.get_attribute("href") or ""
            if href.startswith("//"):
                href = "https:" + href
            if "video" in href or "cheese" in href:
                item.url = href

        if not item.url:
            try:
                ad_link = parent.find_element(By.CSS_SELECTOR, "a[data-target-url]")
                target = ad_link.get_attribute("data-target-url") or ""
                if target and "bilibili.com/video" in target:
                    item.url = target
            except Exception:
                pass

        # 播放量 & 弹幕数
        try:
            stats_items = parent.find_elements(By.CSS_SELECTOR, ".bili-video-card__stats--item")
            if len(stats_items) >= 1:
                item.play_count = stats_items[0].text.strip()
            if len(stats_items) >= 2:
                item.danmu_count = stats_items[1].text.strip()
        except Exception:
            pass

        if not item.play_count:
            for sel in [".bili-video-card__stats--item", "[class*='stats'] [class*='item']", "[class*='play']"]:
                try:
                    elements = parent.find_elements(By.CSS_SELECTOR, sel)
                    if elements:
                        item.play_count = elements[0].text.strip()
                        if len(elements) >= 2:
                            item.danmu_count = elements[1].text.strip()
                        break
                except Exception:
                    continue

        # 视频时长
        duration_selectors = [
            ".bili-video-card__stats__duration",
            ".bili-cover-card__stats span",
            ".duration",
            "[class*='duration']",
            "[class*='length']",
        ]
        for sel in duration_selectors:
            try:
                dur = parent.find_element(By.CSS_SELECTOR, sel)
                text = dur.text.strip()
                if text:
                    if "/" in text:
                        parts = text.split("/")
                        if len(parts) == 2:
                            item.video_duration = parts[1].strip()
                    else:
                        item.video_duration = text
                    if item.video_duration:
                        break
            except NoSuchElementException:
                continue

        # 发布时间
        time_selectors = [
            ".bili-video-card__info--date",
            ".publish-time",
            "[class*='date']",
            "[class*='time']",
            "[class*='pub']",
        ]
        for sel in time_selectors:
            try:
                pt = parent.find_element(By.CSS_SELECTOR, sel)
                item.display_publish_time = pt.text.strip()
                if item.display_publish_time:
                    break
            except NoSuchElementException:
                continue

        if not item.display_publish_time:
            try:
                all_text = parent.text
                import re
                m = re.search(r'[·•]\s*(\d{4}-\d{2}-\d{2}|\d{1,2}-\d{1,2}|昨天|今天|前天|\d+天前|\d+小时前|\d+分钟前)', all_text)
                if m:
                    item.display_publish_time = m.group(0).strip()
            except Exception:
                pass

        return item

    # 确保卡片内容渲染完成
    def _ensure_card_rendered(self, card):
        """滚动到卡片可见位置并等待内容渲染完成"""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                card
            )
            time.sleep(0.3)

            for _ in range(3):
                try:
                    elements = card.find_elements(By.CSS_SELECTOR,
                        ".bili-video-card__info--author, .bili-video-card__info--owner, "
                        ".up-name, [class*='author'], [class*='up-name']")
                    for el in elements:
                        if el.text.strip():
                            return
                    stats = card.find_elements(By.CSS_SELECTOR,
                        ".bili-video-card__stats--item, [class*='stats']")
                    for el in stats:
                        if el.text.strip():
                            return
                except Exception:
                    pass
                time.sleep(0.3)
        except Exception:
            pass

    # 滚动加载所有卡片
    def _scroll_to_load_all(self):
        """滚动搜索结果页面，确保所有卡片内容渲染完成"""
        print("[Parser] 开始滚动加载搜索结果...")
        last_count = 0
        no_change_count = 0

        for i in range(5):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            video_selectors = [
                ".video-list-item", ".bili-video-card",
                "[class*='video-card']", "[class*='result-item']",
            ]
            current_count = 0
            for sel in video_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if elements:
                    current_count = len(elements)
                    break

            if current_count == last_count:
                no_change_count += 1
            else:
                no_change_count = 0
            last_count = current_count

            if no_change_count >= 2:
                print(f"[Parser] 搜索结果已全部加载 (共 {current_count} 条)")
                break

            print(f"[Parser] 滚动第 {i+1} 次，当前 {current_count} 条")

        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        print("[Parser] 滚动加载完成，开始解析")

    # 处理新标签页问题
    def _handle_new_tab(self):
        """处理新标签页问题：如果有多个标签页，切换到最新的标签页"""
        handles = self.driver.window_handles
        if len(handles) > 1:
            print(f"[Parser] 检测到 {len(handles)} 个标签页，切换到最新标签页")
            self.driver.switch_to.window(handles[-1])
            for handle in handles[:-1]:
                self.driver.switch_to.window(handle)
                self.driver.close()
            self.driver.switch_to.window(handles[-1])
            print("[Parser] 已切换到搜索结果标签页")
        elif len(handles) == 1:
            print("[Parser] 当前只有一个标签页，无需切换")

