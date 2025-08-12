"""Core functionality tests without external dependencies"""
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestImgurUploaderCore(unittest.TestCase):
    """Test Imgur uploader core functionality"""
    
    def test_initialization_errors(self):
        """Test initialization error handling"""
        with patch.dict(os.environ, {}, clear=True):
            from uploaders.imgur_uploader import ImgurUploader, ImgurConfigurationError
            with self.assertRaises(ImgurConfigurationError):
                ImgurUploader()
    
    def test_filename_sanitization(self):
        """Test filename sanitization functionality"""
        from uploaders.imgur_uploader import ImgurUploader
        
        uploader = ImgurUploader(client_id='test')
        
        # Test cases
        test_cases = [
            ('normal.jpg', 'normal.jpg'),
            ('test../dangerous.jpg', 'dangerous.jpg'),  # basename removes path
            ('../../evil.jpg', 'evil.jpg'),  # basename removes path
            ('file with spaces.png', 'filewithspaces.png'),  # spaces removed
            ('special!@#$%^&*()chars.gif', 'specialchars.gif'),  # special chars removed
            ('', 'image.jpg'),
            ('a' * 300 + '.jpg', 'a' * 255),  # Length limit - extension gets cut off
        ]
        
        for input_filename, expected in test_cases:
            with self.subTest(input_filename=input_filename):
                result = uploader._sanitize_filename(input_filename)
                self.assertEqual(result, expected)
                self.assertLessEqual(len(result), 255)
    
    @patch('requests.head')
    def test_url_verification(self, mock_head):
        """Test URL verification functionality"""
        from uploaders.imgur_uploader import ImgurUploader
        
        # Test valid URL
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg'}
        mock_head.return_value = mock_response
        
        result = ImgurUploader.verify_image_url('https://i.imgur.com/test.jpg')
        self.assertTrue(result)
        
        # Test non-Imgur URL
        result = ImgurUploader.verify_image_url('https://example.com/test.jpg')
        self.assertFalse(result)
        
        # Test empty/None URL
        result = ImgurUploader.verify_image_url('')
        self.assertFalse(result)
        
        result = ImgurUploader.verify_image_url(None)
        self.assertFalse(result)


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment configuration handling"""
    
    def test_imgur_env_variables(self):
        """Test Imgur environment variable handling"""
        from uploaders.imgur_uploader import ImgurUploader
        
        # Test with environment variable
        with patch.dict(os.environ, {'IMGUR_CLIENT_ID': 'env_client_id'}):
            uploader = ImgurUploader()
            self.assertEqual(uploader.imgur_client_id, 'env_client_id')
        
        # Test with direct parameter (should override env)
        with patch.dict(os.environ, {'IMGUR_CLIENT_ID': 'env_client_id'}):
            uploader = ImgurUploader(client_id='direct_client_id')
            self.assertEqual(uploader.imgur_client_id, 'direct_client_id')
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        from uploaders.imgur_uploader import ImgurUploader, ImgurConfigurationError
        
        # Test missing configuration
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImgurConfigurationError):
                ImgurUploader()
        
        # Test valid configuration
        uploader = ImgurUploader(client_id='valid_client_id')
        self.assertIsNotNone(uploader.imgur_client_id)


class TestErrorHandling(unittest.TestCase):
    """Test error handling throughout the application"""
    
    def test_custom_exceptions(self):
        """Test that custom exceptions are properly defined"""
        from uploaders.imgur_uploader import (
            ImgurUploaderError, 
            ImgurConfigurationError, 
            ImgurUploadError
        )
        
        # Test exception hierarchy
        self.assertTrue(issubclass(ImgurConfigurationError, ImgurUploaderError))
        self.assertTrue(issubclass(ImgurUploadError, ImgurUploaderError))
        
        # Test exception instantiation
        base_error = ImgurUploaderError("Base error")
        self.assertEqual(str(base_error), "Base error")
        
        config_error = ImgurConfigurationError("Config error")
        self.assertEqual(str(config_error), "Config error")
        
        upload_error = ImgurUploadError("Upload error")
        self.assertEqual(str(upload_error), "Upload error")


class TestSecurityValidation(unittest.TestCase):
    """Test security-related validation"""
    
    def test_path_validation(self):
        """Test path validation for security"""
        from uploaders.imgur_uploader import ImgurUploader, ImgurUploadError
        
        uploader = ImgurUploader(client_id='test')
        
        # Test non-existent path
        with self.assertRaises(ImgurUploadError):
            uploader._validate_image_path('/nonexistent/path.jpg')
        
        # Test directory traversal attempt
        with self.assertRaises(ImgurUploadError):
            uploader._validate_image_path('../../../etc/passwd')
    
    def test_url_security(self):
        """Test URL security validation"""
        from uploaders.imgur_uploader import ImgurUploader
        
        # Only Imgur URLs should be accepted for verification
        test_cases = [
            ('https://i.imgur.com/test.jpg', True),  # Valid Imgur URL
            ('http://i.imgur.com/test.jpg', False),  # HTTP not HTTPS
            ('https://example.com/test.jpg', False),  # Non-Imgur domain
            ('https://imgur.com/test.jpg', False),   # Wrong subdomain
            ('', False),                             # Empty URL
            (None, False),                           # None URL
        ]
        
        for url, should_check in test_cases:
            with self.subTest(url=url):
                # The verify_image_url should return False for non-Imgur URLs
                # without making HTTP requests
                if not should_check:
                    result = ImgurUploader.verify_image_url(url)
                    self.assertFalse(result)


class TestConfigurationFiles(unittest.TestCase):
    """Test configuration file handling"""
    
    def test_env_example_exists(self):
        """Test that .env.example file exists and is properly formatted"""
        env_example_path = project_root / '.env.example'
        self.assertTrue(env_example_path.exists(), ".env.example file should exist")
        
        # Read and validate content
        with open(env_example_path, 'r') as f:
            content = f.read()
            
        # Check for required configuration keys
        required_keys = [
            'NOTION_API_KEY',
            'NOTION_DATABASE_ID', 
            'IMGUR_CLIENT_ID',
            'TESSERACT_PATH'
        ]
        
        for key in required_keys:
            self.assertIn(key, content, f"{key} should be in .env.example")


if __name__ == '__main__':
    # Configure logging to reduce noise during tests
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    
    unittest.main()