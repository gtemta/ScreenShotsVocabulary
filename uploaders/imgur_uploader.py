import os.path
import json
import requests
import base64
import time
from PIL import Image
import io
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import certifi

class ImgurUploader:
    def __init__(self):
        """初始化 Imgur 上傳器"""
        self.imgur_client_id = None
        self.load_imgur_credentials()
        self.max_retries = 3
        self.retry_delay = 5  # 重试延迟秒数
        self.max_image_size = 5 * 1024 * 1024  # 最大图片大小（5MB）
        
        # 配置请求会话
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET", "HEAD"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # 使用 certifi 提供的证书
        self.session.verify = certifi.where()
        
        # 设置连接超时
        self.session.timeout = (5, 30)  # (连接超时, 读取超时)
        
        # 禁用 SSL 警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
    def load_imgur_credentials(self):
        """加載 Imgur API 憑證"""
        try:
            with open('imgur_credentials.json', 'r') as f:
                credentials = json.load(f)
                self.imgur_client_id = credentials.get('client_id')
        except Exception as e:
            print(f"⚠️ 無法加載 Imgur 憑證: {str(e)}")
            print("請確保 imgur_credentials.json 文件存在並包含有效的 client_id")
            
    def compress_image(self, image_path):
        """
        壓縮圖片到合適的大小
        
        Args:
            image_path (str): 圖片路徑
            
        Returns:
            bytes: 壓縮後的圖片數據
        """
        try:
            # 打開圖片
            with Image.open(image_path) as img:
                # 轉換為 RGB 模式（如果是 RGBA）
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                
                # 計算壓縮比例
                quality = 95
                output = io.BytesIO()
                
                while True:
                    output.seek(0)
                    output.truncate()
                    img.save(output, format='JPEG', quality=quality)
                    if len(output.getvalue()) <= self.max_image_size or quality <= 30:
                        break
                    quality -= 5
                
                return output.getvalue()
                
        except Exception as e:
            print(f"⚠️ 圖片壓縮失敗: {str(e)}")
            return None
            
    def upload_to_imgur(self, image_path):
        """
        將圖片上傳到 Imgur
        
        Args:
            image_path (str): 要上傳的圖片路徑
            
        Returns:
            str: 上傳後圖片的直接連結
        """
        if not self.imgur_client_id:
            print("❌ 未找到 Imgur API 憑證")
            return None
            
        try:
            # 處理文件名，確保符合 Imgur 要求
            filename = os.path.basename(image_path)
            filename = ''.join(c for c in filename if c.isalnum() or c in '_.')
            filename = filename[:255]
            
            # 壓縮圖片
            compressed_image = self.compress_image(image_path)
            if not compressed_image:
                return None
                
            # 準備上傳數據
            headers = {
                'Authorization': f'Client-ID {self.imgur_client_id}'
            }
            
            # 使用文件上传
            files = {
                'image': (filename, compressed_image, 'image/jpeg')
            }
            
            # 重試機制
            for attempt in range(self.max_retries):
                try:
                    response = self.session.post(
                        'https://api.imgur.com/3/image',
                        headers=headers,
                        files=files
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return result['data']['link']
                    elif response.status_code == 429:  # 速率限制
                        if attempt < self.max_retries - 1:
                            wait_time = (attempt + 1) * self.retry_delay
                            print(f"⚠️ 達到速率限制，等待 {wait_time} 秒後重試...")
                            time.sleep(wait_time)
                            continue
                    else:
                        print(f"❌ Imgur 上傳失敗 (狀態碼: {response.status_code}): {response.text}")
                        
                except requests.exceptions.SSLError as e:
                    print(f"⚠️ SSL 錯誤: {str(e)}")
                    if attempt < self.max_retries - 1:
                        wait_time = (attempt + 1) * self.retry_delay
                        print(f"⚠️ 等待 {wait_time} 秒後重試...")
                        time.sleep(wait_time)
                        continue
                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries - 1:
                        wait_time = (attempt + 1) * self.retry_delay
                        print(f"⚠️ 上傳失敗，等待 {wait_time} 秒後重試: {str(e)}")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Imgur 上傳失敗: {str(e)}")
                        return None
                        
            return None
                
        except Exception as e:
            print(f"❌ Imgur 上傳過程發生錯誤: {str(e)}")
            return None

    def upload_image(self, image_path):
        """
        將圖片上傳到 Imgur，返回直接訪問連結
        
        Args:
            image_path (str): 要上傳的圖片路徑
            
        Returns:
            str: 上傳後圖片的直接連結
        """
        return self.upload_to_imgur(image_path)

    @staticmethod
    def verify_image_url(url):
        """
        驗證圖片 URL 是否有效
        
        Args:
            url (str): 圖片 URL
            
        Returns:
            bool: URL 是否有效
        """
        max_retries = 3
        retry_delay = 2  # 秒
        
        if not url.startswith('https://i.imgur.com/'):
            print(f"⚠️ 非 Imgur 圖片 URL: {url}")
            return False
            
        for attempt in range(max_retries):
            try:
                response = requests.head(url, timeout=5)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if content_type.startswith('image/'):
                        return True
                    else:
                        print(f"⚠️ URL 不是圖片格式: {content_type}")
                        return False
                elif response.status_code == 429:  # 速率限制
                    if attempt < max_retries - 1:
                        print(f"⚠️ 達到速率限制，等待 {retry_delay} 秒後重試 ({attempt + 1}/{max_retries})...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print("⚠️ 達到速率限制，跳過圖片驗證")
                        return True
                else:
                    print(f"⚠️ URL 返回錯誤狀態碼: {response.status_code}")
                    return False
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 驗證圖片 URL 時出錯，正在重試 ({attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"⚠️ 驗證圖片 URL 時出錯: {str(e)}")
                    return False
                    
        return False 