import unittest
import os
import requests
from uploaders.imgur_uploader import ImgurUploader
from unittest.mock import patch, MagicMock

class TestImgurUploader(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.uploader = ImgurUploader()
        # 创建测试用的临时图片
        self.test_image_path = "test_image.jpg"
        self.create_test_image()
        
    def tearDown(self):
        """测试后的清理工作"""
        # 删除测试图片
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
            
    def create_test_image(self):
        """创建测试用的图片文件"""
        from PIL import Image
        # 创建一个 100x100 的红色图片
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_image_path)
        
    @patch('requests.Session.post')
    def test_upload_image_success(self, mock_post):
        """测试成功上传图片的情况（模拟）"""
        # 模拟成功的响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'link': 'https://i.imgur.com/test123.jpg'
            }
        }
        mock_post.return_value = mock_response
        
        # 执行上传
        result = self.uploader.upload_image(self.test_image_path)
        
        # 验证结果
        self.assertEqual(result, 'https://i.imgur.com/test123.jpg')
        self.assertTrue(mock_post.called)
        
    @patch('requests.Session.post')
    def test_upload_image_failure(self, mock_post):
        """测试上传失败的情况（模拟）"""
        # 模拟失败的响应
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        # 执行上传
        result = self.uploader.upload_image(self.test_image_path)
        
        # 验证结果
        self.assertIsNone(result)
        self.assertTrue(mock_post.called)
        
    def test_upload_image_invalid_path(self):
        """测试无效的图片路径"""
        result = self.uploader.upload_image("nonexistent.jpg")
        self.assertIsNone(result)
        
    @patch('requests.Session.post')
    def test_upload_image_ssl_error(self, mock_post):
        """测试 SSL 错误的情况（模拟）"""
        # 模拟 SSL 错误
        mock_post.side_effect = requests.exceptions.SSLError("SSL Error")
        
        # 执行上传
        result = self.uploader.upload_image(self.test_image_path)
        
        # 验证结果
        self.assertIsNone(result)
        self.assertTrue(mock_post.called)

    @unittest.skipIf(not os.path.exists('imgur_credentials.json'), "需要 imgur_credentials.json 文件")
    def test_real_upload(self):
        """测试真实的上传（集成测试）"""
        # 确保有凭证
        if not self.uploader.imgur_client_id:
            self.skipTest("未找到 Imgur API 凭证")
            
        # 执行真实上传
        result = self.uploader.upload_image(self.test_image_path)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith('https://i.imgur.com/'))
        
        # 验证返回的 URL 是否可访问
        response = requests.head(result)
        self.assertEqual(response.status_code, 200)
        
    @unittest.skipIf(not os.path.exists('imgur_credentials.json'), "需要 imgur_credentials.json 文件")
    def test_real_upload_with_retry(self):
        """测试真实上传的重试机制（集成测试）"""
        # 确保有凭证
        if not self.uploader.imgur_client_id:
            self.skipTest("未找到 Imgur API 凭证")
            
        # 临时修改重试次数和延迟
        original_retries = self.uploader.max_retries
        original_delay = self.uploader.retry_delay
        self.uploader.max_retries = 2
        self.uploader.retry_delay = 1
        
        try:
            # 执行真实上传
            result = self.uploader.upload_image(self.test_image_path)
            
            # 验证结果
            self.assertIsNotNone(result)
            self.assertTrue(result.startswith('https://i.imgur.com/'))
        finally:
            # 恢复原始设置
            self.uploader.max_retries = original_retries
            self.uploader.retry_delay = original_delay

if __name__ == '__main__':
    unittest.main() 