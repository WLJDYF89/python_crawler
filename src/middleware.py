"""
Middleware 中间件模块
封装登录态管理、请求头伪装、反反爬策略
模拟 Scrapy 的 DownloaderMiddleware 设计思想
"""
import pickle
import time
import os
from selenium.webdriver.common.by import By

COOKIE_FILE = "results/bilibili_cookies.pkl"


class LoginStateMiddleware:
    """
    登录态中间件：负责 Cookie 的加载、保存与验证
    模拟 Scrapy 的 DownloaderMiddleware 思路
    """

    def __init__(self, driver):
        self.driver = driver

    def save_cookies(self):
        """保存 Cookie 到本地文件"""
        if not self.driver:
            return
        os.makedirs("results", exist_ok=True)
        cookies = self.driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"[Middleware] Cookie 已保存 ({len(cookies)} 条)")

    def load_cookies(self) -> bool:
        """从本地文件加载 Cookie"""
        if not os.path.exists(COOKIE_FILE):
            print("[Middleware] Cookie 文件不存在")
            return False

        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)

        self.driver.get("https://www.bilibili.com/")
        time.sleep(2)

        for cookie in cookies:
            try:
                # 处理 sameSite 属性
                if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = "Lax"
                # 处理过期时间
                if "expiry" in cookie:
                    cookie["expiry"] = int(cookie["expiry"])
                self.driver.add_cookie(cookie)
            except Exception:
                pass

        print(f"[Middleware] Cookie 已从本地加载 ({len(cookies)} 条)")
        self.driver.get("https://www.bilibili.com/")
        time.sleep(2)
        return True

    def check_login(self) -> bool:
        """检查当前是否已登录"""
        try:
            self.driver.get("https://www.bilibili.com/")
            time.sleep(3)

            # 方法1：查找用户头像元素
            for selector in [".header-avatar-wrap", ".header-avatar",
                            "[class*='avatar']", ".bili-header__bar .user-con",
                            ".right-entry__outside"]:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    return True
                except Exception:
                    continue

            # 方法2：查找未登录标识
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".header-login-entry, .unlogin-avatar")
                return False
            except Exception:
                pass

            # 方法3：检查关键 Cookie
            for cookie in self.driver.get_cookies():
                if cookie.get("name") in ("DedeUserID", "SESSDATA", "bili_jct"):
                    return True

            return False
        except Exception as e:
            print(f"[Middleware] 检查登录状态失败: {e}")
            return False

    def inject_request_headers(self):
        """注入请求头伪装和反检测脚本"""
        anti_detect_js = """
        // 隐藏 webdriver 特征
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // 伪装 plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const arr = [];
                for (let i = 0; i < 5; i++) {
                    arr.push({
                        name: 'Chrome PDF Plugin',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format'
                    });
                }
                return arr;
            }
        });
        
        // 伪装语言
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en']
        });
        
        // 伪装平台
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        
        // 伪装 Chrome 对象
        window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};
        
        // 伪装权限查询
        const orig = window.navigator.permissions.query;
        window.navigator.permissions.query = (p) => (
            p.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : orig(p)
        );
        """
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": anti_detect_js
        })
        print("[Middleware] 已注入反检测脚本")
