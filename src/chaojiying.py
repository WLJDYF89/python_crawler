"""
超级鹰验证码识别平台 API 封装
文档: https://www.chaojiying.com/api.html

纯标准库实现，无需额外依赖
"""
import hashlib
import base64
import json
from urllib import request, parse


class Chaojiying_Client:
    """超级鹰验证码识别客户端"""

    def __init__(self, username: str, password: str, soft_id: str):
        self.username = username
        self.password = hashlib.md5(password.encode()).hexdigest()
        self.soft_id = soft_id
        self.base_params = {
            'user': self.username,
            'pass2': self.password,
            'softid': self.soft_id,
        }

    def PostPic(self, im: bytes, codetype: int) -> dict:
        """
        发送图片进行识别
        
        参数:
            im: 图片字节数据
            codetype: 题目类型
                1902 - 常规验证码(4~6位英文数字)
                9004 - 坐标点选(返回坐标)
                9101 - 点选验证码(返回文字)
                9103 - 点选验证码(返回文字+坐标)
        返回:
            dict, 包含 err_no, err_str, pic_id, pic_str 等字段
            出错返回 {'err_no': -1, 'err_str': '...'}
        """
        params = {'codetype': str(codetype)}
        params.update(self.base_params)

        # 构建 multipart/form-data 请求
        boundary = '----WebKitFormBoundary' + hashlib.md5(str(id(self)).encode()).hexdigest()[:16]
        body = self._build_multipart(boundary, params, im, 'captcha.png')

        headers = {
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'multipart/form-data; boundary=' + boundary,
        }

        try:
            req = request.Request(
                'https://upload.chaojiying.net/Upload/Processing.php',
                data=body,
                headers=headers,
                method='POST',
            )
            with request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result
        except Exception as e:
            return {'err_no': -1, 'err_str': str(e)}

    def _build_multipart(self, boundary: str, params: dict, file_data: bytes, filename: str) -> bytes:
        """构建 multipart/form-data 请求体"""
        lines = []
        for key, value in params.items():
            lines.append(f'--{boundary}'.encode())
            lines.append(f'Content-Disposition: form-data; name="{key}"'.encode())
            lines.append(b'')
            lines.append(str(value).encode())

        # 文件字段
        lines.append(f'--{boundary}'.encode())
        lines.append(
            f'Content-Disposition: form-data; name="userfile"; filename="{filename}"'.encode()
        )
        lines.append(b'Content-Type: image/png')
        lines.append(b'')
        lines.append(file_data)

        # 结束
        lines.append(f'--{boundary}--'.encode())
        return b'\r\n'.join(lines)

    def ReportError(self, im_id: str) -> dict:
        """
        报错（识别错误退分）
        
        参数:
            im_id: 图片 ID（PostPic 返回的 pic_id）
        """
        params = {'id': im_id}
        params.update(self.base_params)
        data = parse.urlencode(params).encode()

        try:
            req = request.Request(
                'https://upload.chaojiying.net/Upload/ReportError.php',
                data=data,
                headers={'User-Agent': 'Mozilla/5.0'},
                method='POST',
            )
            with request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {'err_no': -1, 'err_str': str(e)}
