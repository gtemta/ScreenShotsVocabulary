"""Basic functionality tests without heavy dependencies"""
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from uploaders.imgur_uploader import ImgurUploader, ImgurUploaderError, ImgurConfigurationError
from uploaders.notion_uploader import NotionUploader, NotionUploaderError, NotionConfigurationError

class TestImgurUploader(unittest.TestCase):
    """Test Imgur uploader basic functionality"""
    
    def test_initialization_without_credentials(self):
        """Test that uploader raises error when no credentials provided"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImgurConfigurationError):
                ImgurUploader()
    
    def test_initialization_with_env_credentials(self):
        """Test successful initialization with environment credentials"""
        with patch.dict(os.environ, {'IMGUR_CLIENT_ID': 'test_client_id'}):
            uploader = ImgurUploader()
            self.assertEqual(uploader.imgur_client_id, 'test_client_id')
    
    def test_initialization_with_direct_credentials(self):
        """Test successful initialization with direct credentials"""
        uploader = ImgurUploader(client_id='direct_client_id')
        self.assertEqual(uploader.imgur_client_id, 'direct_client_id')
    
    def test_validate_image_path_nonexistent(self):
        """Test validation of non-existent image path"""
        uploader = ImgurUploader(client_id='test')
        with self.assertRaises(Exception):  # Should raise some form of error
            uploader._validate_image_path('/nonexistent/path.jpg')
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        uploader = ImgurUploader(client_id='test')
        
        # Test normal filename
        result = uploader._sanitize_filename('test.jpg')
        self.assertEqual(result, 'test.jpg')
        
        # Test filename with dangerous characters
        result = uploader._sanitize_filename('test/../evil.jpg')
        self.assertEqual(result, 'test..evil.jpg')
        
        # Test empty filename
        result = uploader._sanitize_filename('')
        self.assertEqual(result, 'image.jpg')
    
    @patch('requests.head')
    def test_verify_image_url_valid(self, mock_head):
        """Test URL verification with valid URL"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg'}
        mock_head.return_value = mock_response
        
        result = ImgurUploader.verify_image_url('https://i.imgur.com/test.jpg')
        self.assertTrue(result)
    
    @patch('requests.head')
    def test_verify_image_url_invalid(self, mock_head):
        """Test URL verification with invalid URL"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        
        result = ImgurUploader.verify_image_url('https://i.imgur.com/nonexistent.jpg')
        self.assertFalse(result)
    
    def test_verify_image_url_non_imgur(self):
        """Test URL verification with non-Imgur URL"""
        result = ImgurUploader.verify_image_url('https://example.com/test.jpg')
        self.assertFalse(result)

class TestNotionUploader(unittest.TestCase):
    """Test Notion uploader basic functionality"""
    
    def test_initialization_without_credentials(self):
        """Test that uploader raises error when no credentials provided"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(NotionConfigurationError):
                NotionUploader()
    
    @patch('notion_client.Client')
    def test_initialization_with_env_credentials(self, mock_client):
        """Test successful initialization with environment credentials"""
        with patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_api_key',
            'NOTION_DATABASE_ID': 'test_db_id'
        }):
            # Mock the client initialization and database access
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.databases.retrieve.return_value = {
                'title': [{'plain_text': 'Test Database'}]
            }
            
            uploader = NotionUploader()
            self.assertEqual(uploader.api_key, 'test_api_key')
            self.assertEqual(uploader.database_id, 'test_db_id')
    
    @patch('notion_client.Client')
    def test_initialization_with_direct_credentials(self, mock_client):
        """Test successful initialization with direct credentials"""
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.databases.retrieve.return_value = {
            'title': [{'plain_text': 'Test Database'}]
        }
        
        uploader = NotionUploader(api_key='direct_api_key', database_id='direct_db_id')
        self.assertEqual(uploader.api_key, 'direct_api_key')
        self.assertEqual(uploader.database_id, 'direct_db_id')
    
    def test_sanitize_text(self):
        """Test text sanitization"""
        with patch.dict(os.environ, {
            'NOTION_API_KEY': 'test',
            'NOTION_DATABASE_ID': 'test'
        }):
            with patch('notion_client.Client'):
                uploader = NotionUploader()
                
                # Test normal text
                result = uploader._sanitize_text('normal text')
                self.assertEqual(result, 'normal text')
                
                # Test empty text
                result = uploader._sanitize_text('')
                self.assertEqual(result, '')
                
                # Test None
                result = uploader._sanitize_text(None)
                self.assertEqual(result, '')
                
                # Test long text
                long_text = 'a' * 3000
                result = uploader._sanitize_text(long_text)
                self.assertTrue(len(result) <= 2000)
                self.assertTrue(result.endswith('...'))
    
    def test_validate_upload_data_valid(self):
        """Test upload data validation with valid data"""
        with patch.dict(os.environ, {
            'NOTION_API_KEY': 'test',
            'NOTION_DATABASE_ID': 'test'
        }):
            with patch('notion_client.Client'):
                uploader = NotionUploader()
                
                # Should not raise any exception
                uploader._validate_upload_data(
                    word='test',
                    image_url='https://i.imgur.com/test.jpg'
                )
    
    def test_validate_upload_data_invalid_word(self):
        """Test upload data validation with invalid word"""
        with patch.dict(os.environ, {
            'NOTION_API_KEY': 'test',
            'NOTION_DATABASE_ID': 'test'
        }):
            with patch('notion_client.Client'):
                uploader = NotionUploader()
                
                with self.assertRaises(Exception):
                    uploader._validate_upload_data(
                        word='',
                        image_url='https://i.imgur.com/test.jpg'
                    )
    
    def test_validate_upload_data_invalid_url(self):
        """Test upload data validation with invalid URL"""
        with patch.dict(os.environ, {
            'NOTION_API_KEY': 'test',
            'NOTION_DATABASE_ID': 'test'
        }):
            with patch('notion_client.Client'):
                uploader = NotionUploader()
                
                with self.assertRaises(Exception):
                    uploader._validate_upload_data(
                        word='test',
                        image_url='http://insecure.com/test.jpg'  # HTTP instead of HTTPS
                    )

class TestBasicImports(unittest.TestCase):
    """Test that basic imports work correctly"""
    
    def test_import_uploaders(self):
        """Test that uploader modules can be imported"""
        try:
            from uploaders.imgur_uploader import ImgurUploader
            from uploaders.notion_uploader import NotionUploader
            self.assertTrue(True)  # If we get here, imports worked
        except ImportError as e:
            self.fail(f"Import failed: {e}")
    
    def test_import_exceptions(self):
        """Test that custom exceptions can be imported"""
        try:
            from uploaders.imgur_uploader import ImgurUploaderError, ImgurConfigurationError
            from uploaders.notion_uploader import NotionUploaderError, NotionConfigurationError
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Exception import failed: {e}")

if __name__ == '__main__':
    unittest.main()