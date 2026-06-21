import os

target = r"E:\python_crawler\src\parser.py"

# SearchParser content with fixes
search_content = '''

class SearchParser:
    """
    \u641c\u7d22\u7ed3\u679c\u89e3\u6790\u5668
    \u89e3\u6790\u641c\u7d22\u300cvibecoding\u300d\u7684\u7ed3\u679c\u9875\u9762
    """

    SEARCH_KEYWORD = "vibecoding"
    SEARCH_URL = f"https://search.bilibili.com/all?keyword={SEARCH_KEYWORD}&order=totalrank"

    def __init__(self, driver):
        self.driver = driver

    def parse(self) -> list:
        """
        \u89e3\u6790\u641c\u7d22\u7ed3\u679c\u9875\uff0c\u8fd4\u56de SearchItem \u5217\u8868
        \u53ea\u91c7\u96c6\u9996\u5c4f\u6570\u636e\uff0c\u4e0d\u6eda\u52a8\u52a0\u8f7d\u66f4\u591a
        """
        items = []

        try:
            print(f"[Parser] \u6b63\u5728\u641c\u7d22: {self.SEARCH_KEYWORD}")
            self.driver.get("https://www.bilibili.com/")
            time.sleep(3)

            search_box_selectors = [
                ".nav-search-input",
                ".search-input-el",
                "input[placeholder*='\u641c\u7d22']",
                "#nav-searchform input",
            ]
            search_box = None
            for sel in search_box_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    print(f"[Parser] \u627e\u5230\u641c\u7d22\u6846 (via {sel})")
                    break
                except TimeoutException:
                    continue

            if not search_box:
                print("[Parser] \u672a\u627e\u5230\u641c\u7d22\u6846\uff0c\u76f4\u63a5\u8bbf\u95ee\u641c\u7d22URL")
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
                        print(f"[Parser] \u70b9\u51fb\u641c\u7d22\u6309\u94ae (via {sel})")
                        break
                    except NoSuchElementException:
                        continue

                if not btn_clicked:
                    search_box.send_keys(Keys.ENTER)
                    print("[Parser] \u4f7f\u7528\u56de\u8f66\u952e\u63d0\u4ea4\u641c\u7d22")

                time.sleep(5)

                self._handle_new_tab()

        except Exception as e:
            print(f"[Parser] \u641c\u7d22\u64cd\u4f5c\u5931\u8d25: {e}\uff0c\u5c1d\u8bd5\u76f4\u63a5\u8bbf\u95ee\u641c\u7d22URL")
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
            print("[Parser] \u641c\u7d22\u7ed3\u679c\u5df2\u52a0\u8f7d")
        except TimeoutException:
            print("[Parser] \u641c\u7d22\u7ed3\u679c\u5217\u8868\u52a0\u8f7d\u8d85\u65f6,\u5c1d\u8bd5\u7ee7\u7eed\u89e3\u6790...")
            time.sleep(5)

        # \u53ea\u89e3\u6790\u9996\u5c4f\u6570\u636e\uff0c\u4e0d\u6eda\u52a8
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
                print(f"[Parser] \u4f7f\u7528\u9009\u62e9\u5668 '{sel}' \u53d1\u73b0 {len(video_items)} \u4e2a\u89c6\u9891\u5143\u7d20")
                break

        if not video_items:
            print("[Parser] \u672a\u627e\u5230\u4efb\u4f55\u89c6\u9891\u5143\u7d20\uff0c\u5c1d\u8bd5\u4ece\u94fe\u63a5\u63d0\u53d6...")
            video_items = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='video']")

        print(f"[Parser] \u641c\u7d22\u7ed3\u679c\u9875\u9762\u53d1\u73b0 {len(video_items)} \u4e2a\u89c6\u9891\u5143\u7d20")

        for item_el in video_items:
            try:
                item = self._parse_single(item_el)
                if item and item.title:
                    items.append(item)
            except Exception as e:
                continue

        print(f"[Parser] \u641c\u7d22\u7ed3\u679c\u89e3\u6790\u5b8c\u6210\uff0c\u5171 {len(items)} \u6761")
        return items

    def _parse_single(self, card) -> SearchItem:
        """\u89e3\u6790\u5355\u4e2a\u641c\u7d22\u7ed3\u679c\u5361\u7247"""
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

        # \u6807\u9898
        title_selectors = [
            ".bili-video-card__info--tit",
            ".video-title",
            ".title",
            "a[href*='video']",
            "h3",
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

        # UP \u4e3b
        author_selectors = [
            ".bili-video-card__info--author",
            ".bili-video-card__info--owner",
            ".up-name",
            "span[class*='author']:not([class*='ico'])",
            "[class*='up-name']",
        ]
        for sel in author_selectors:
            try:
                elements = parent.find_elements(By.CSS_SELECTOR, sel)
                for a in elements:
                    text = a.text.strip()
                    if text:
                        # .bili-video-card__info--owner contains "AuthorName \u00b7 date"
                        if " \u00b7 " in text:
                            text = text.split(" \u00b7 ")[0].strip()
                        item.author = text
                        break
                if item.author:
                    break
            except NoSuchElementException:
                continue

        # \u8be6\u60c5\u9875 URL
        url_selectors = [
            "a[href*='video/BV']",
            "a[href*='video/av']",
            "a[href*='bv/']",
            "a[href*='video']",
        ]
        for sel in url_selectors:
            try:
                link = parent.find_element(By.CSS_SELECTOR, sel)
                href = link.get_attribute("href") or ""
                if href and "bilibili.com/video" in href:
                    item.url = href
                    break
            except NoSuchElementException:
                continue

        if not item.url and parent.tag_name == "a":
            href = parent.get_attribute("href") or ""
            if "video" in href:
                item.url = href

        # \u64ad\u653e\u91cf & \u5f39\u5e55\u6570\uff08\u4f7f\u7528\u65b0\u7684 stats-item \u7ed3\u6784\uff09
        try:
            stats_items = parent.find_elements(By.CSS_SELECTOR, ".bili-video-card__stats--item")
            if len(stats_items) >= 1:
                item.play_count = stats_items[0].text.strip()
            if len(stats_items) >= 2:
                item.danmu_count = stats_items[1].text.strip()
        except NoSuchElementException:
            pass

        # \u89c6\u9891\u65f6\u957f
        duration_selectors = [
            ".bili-video-card__stats__duration",
            ".duration",
            "[class*='duration']",
            "[class*='length']",
        ]
        for sel in duration_selectors:
            try:
                dur = parent.find_element(By.CSS_SELECTOR, sel)
                item.video_duration = dur.text.strip()
                if item.video_duration:
                    break
            except NoSuchElementException:
                continue

        # \u53d1\u5e03\u65f6\u95f4
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

        return item

    def _handle_new_tab(self):
        """\u5904\u7406\u65b0\u6807\u7b7e\u9875\u95ee\u9898\uff1a\u5982\u679c\u6709\u591a\u4e2a\u6807\u7b7e\u9875\uff0c\u5207\u6362\u5230\u6700\u65b0\u7684\u6807\u7b7e\u9875"""
        handles = self.driver.window_handles
        if len(handles) > 1:
            print(f"[Parser] \u68c0\u6d4b\u5230 {len(handles)} \u4e2a\u6807\u7b7e\u9875\uff0c\u5207\u6362\u5230\u6700\u65b0\u6807\u7b7e\u9875")
            self.driver.switch_to.window(handles[-1])
            for handle in handles[:-1]:
                self.driver.switch_to.window(handle)
                self.driver.close()
            self.driver.switch_to.window(handles[-1])
            print("[Parser] \u5df2\u5207\u6362\u5230\u641c\u7d22\u7ed3\u679c\u6807\u7b7e\u9875")
        elif len(handles) == 1:
            print("[Parser] \u5f53\u524d\u53ea\u6709\u4e00\u4e2a\u6807\u7b7e\u9875\uff0c\u65e0\u9700\u5207\u6362")
'''

with open(target, "a", encoding="utf-8") as f:
    f.write(search_content)

# Verify
with open(target, "r", encoding="utf-8") as f:
    check = f.read()
print("Total file size: {} bytes".format(len(check)))

# Syntax check
try:
    compile(check, target, 'exec')
    print("OK: Syntax valid")
except SyntaxError as e:
    print("SYNTAX ERROR:", e)

# Check key content
for key in ["\u641c\u7d22\u7ed3\u679c\u89e3\u6790\u5668", ".bili-video-card__info--owner", ".bili-video-card__stats--item", "_handle_new_tab"]:
    if key in check:
        print("OK: found", repr(key))
    else:
        print("MISSING:", repr(key))
