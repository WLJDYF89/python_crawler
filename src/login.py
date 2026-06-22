"""
自动登录模块
实现 Bilibili 账号密码登录 + 点选验证码（超级鹰识别）
"""
import os
import time
from PIL import Image
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.chaojiying import Chaojiying_Client


class BilibiliLogin:

    def __init__(self, driver):
        # 如果传入 driver 则使用，否则创建新的
        if driver:
            self.driver = driver
        else:
            self.driver = webdriver.Chrome()

        self.url = 'https://www.bilibili.com/'
        self.image_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(self.image_dir, 'yzm.png')


    def login(self):
        self.driver.get(self.url)
        self.driver.maximize_window()
        time.sleep(1) # 等待页面加载

        # 进入登录界面
        btn1 = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//*[@id="app"]/div[2]/div[1]/div[1]/ul[2]/li[1]/li/div[1]/div'
            ))
        )
        btn1.click()

        time.sleep(2)

        # 输入账号
        send1 = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((
                    By.XPATH,
                    '/html/body/div[3]/div/div[4]/div[2]/form/div[1]/input'
            ))
        )
        send1.send_keys("19127198731")
        time.sleep(1)

        # 输入密码
        send2 = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '/html/body/div[3]/div/div[4]/div[2]/form/div[3]/input'
            ))
        )
        send2.send_keys("WLJDYF89")

        # 点击登录，弹出验证码
        tab = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '/html/body/div[3]/div/div[4]/div[2]/div[2]/div[2]'
            ))
        )
        tab.click()

        # 抠图
        # 等待
        img_file = WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'geetest_item_img'))
        )
        # 只截取标签 点选图片
        img_file.screenshot(self.image_path)


        # input("1验证结束后请按回车继续")
        # time.sleep(2)
        #
        # # 发送验证码
        # btn2 = WebDriverWait(self.driver, 10).until(
        #     EC.element_to_be_clickable((
        #         By.XPATH,
        #         '//*[@id="riskWp"]/div[2]/div[2]/div[1]/div[3]'
        #     ))
        # )
        # btn2.click()
        #
        # input("2验证结束后请按回车继续")
        # time.sleep(2)
        #
        # next_btn = WebDriverWait(self.driver, 10).until(
        #     EC.element_to_be_clickable((
        #         By.XPATH,
        #         '//*[@id="riskWp"]/div[2]/div[2]/div[2]'
        #     ))
        # )
        # next_btn.click()
        #
        # time.sleep(4)
        #
        # # return True
        # return self._verify_login()

    # ================================================================
    #  验证码检测
    # ================================================================

    def dock_chaojiying(self):
        # 对接超级鹰 填写账号、密码、软件id
        chaojiying = Chaojiying_Client('202606088s47u6lo', '270611', '7632e2ccaf948d0f57541e0db198ab36') # 账号 密码 软件ID
        im = open(self.image_path, 'rb').read()
        # result存储的是超级鹰以json格式返回的数据
        # {'err_no': 0,    driver.execute_script('window.scrollBy(0,3650)') 'err_str': 'OK', 'pic_id': '1144316386469800081',
        # 'pic_str': '88,175|267,153', 'md5': '8ff4bd04e90b1fe1f5b19076cbcd8d6a'}
        result = chaojiying.PostPic(im, 9004)
        if result.get('err_no') != 0 or not result.get('pic_str'):
            raise ValueError(f'超级鹰识别失败，请检查账号、密码、软件ID和题目类型：{result}')
        # 提取文字坐标信息
        coordinates = result.get('pic_str').split('|')
        # 280,136|98,212|312,220|161,88
        # [[280,136],[98,212],[312,220],[161,88]]
        # 将坐标['x,y','x,y']形式转换成[[x, y], [x, y]]便于Selenium定位
        locations = [[int(number) for number in coordinate.split(',')] for coordinate in coordinates]

        return locations

    def simulated_click(self):
        self.login()
        # 等待
        img = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'geetest_item_img')))
        screenshot_width, screenshot_height = Image.open(self.image_path).size
        element_width = img.size['width']
        element_height = img.size['height']
        dpr = self.driver.execute_script("return window.devicePixelRatio")
        print('截图尺寸：', screenshot_width, screenshot_height)
        print('页面元素尺寸：', element_width, element_height)
        print('DPR：', dpr)
        locations = self.dock_chaojiying()
        print('超级鹰返回坐标：', locations)
        for index, location in enumerate(locations, start=1):
            # 超级鹰返回的是截图像素坐标，Selenium 点击用的是页面元素的 CSS 像素坐标
            click_x = location[0] * element_width / screenshot_width
            click_y = location[1] * element_height / screenshot_height
            # click_x = location[0] / dpr
            # click_y = location[1] / dpr
            print('第', index, '次点击元素内坐标：', round(click_x), round(click_y))
            self.click_captcha_point(img, click_x, click_y)
            time.sleep(0.8)
        # 点击确认按钮
        commit = WebDriverWait(self.driver, 10).until(
            lambda driver: self.get_enabled_submit()
        )
        self.driver.execute_script("arguments[0].click();", commit)

        # 等待3秒查看是否点击成功
        time.sleep(4)

        # 发送验证码
        btn2 = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//*[@id="riskWp"]/div[2]/div[2]/div[1]/div[3]'
            ))
        )
        btn2.click()

        input("验证结束后请按回车继续")
        time.sleep(2)

        # 点击下一步
        next_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//*[@id="riskWp"]/div[2]/div[2]/div[2]'
            ))
        )
        next_btn.click()

        time.sleep(4)

        # return True
        return self._verify_login()

    def get_enabled_submit(self):
        commit = self.driver.find_element(By.CLASS_NAME, 'geetest_commit')
        class_name = commit.get_attribute('class')
        if commit.is_displayed() and 'geetest_disable' not in class_name:
            return commit
        return False

    def click_captcha_point(self, img, click_x, click_y):
        rect = self.driver.execute_script("""
            var rect = arguments[0].getBoundingClientRect();
            return {left: rect.left, top: rect.top};
        """, img)
        client_x = rect['left'] + click_x
        client_y = rect['top'] + click_y
        print('浏览器页面点击坐标：', round(client_x), round(client_y))
        self.driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseMoved',
            'x': client_x,
            'y': client_y,
        })
        self.driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mousePressed',
            'x': client_x,
            'y': client_y,
            'button': 'left',
            'buttons': 1,
            'clickCount': 1,
        })
        self.driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseReleased',
            'x': client_x,
            'y': client_y,
            'button': 'left',
            'buttons': 0,
            'clickCount': 1,
        })

    # ================================================================
    #  登录状态验证
    # ================================================================

    def _verify_login(self) -> bool:

        try:
            for sel in [".header-avatar-wrap", ".header-avatar", "[class*='avatar']",
                         ".bili-header__bar .user-con", ".right-entry__outside"]:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, sel)
                    return True
                except NoSuchElementException:
                    continue
            return False

        except Exception as e:
            print(f"[Login] 验证登录状态出错: {e}")
            return False
