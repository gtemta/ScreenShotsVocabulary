"""
PostImage.org Free Image Uploader
Alternative image hosting service that doesn't require API keys.
Simple, reliable, no-registration-required service.
"""

import logging
import time
import random
import base64
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Optional PIL import for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

class PostImageUploaderError(Exception):
    """Base exception for PostImage uploader errors"""
    pass

class PostImageUploadError(PostImageUploaderError):
    """Upload operation errors"""
    pass

class PostImageUploader:
    """PostImage.org uploader - free, no API key required, reliable"""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        """Initialize PostImage uploader
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_image_size = 24 * 1024 * 1024  # 24MB limit for PostImage
        
        self._setup_session()
        
    def _setup_session(self) -> None:
        """Configure requests session for PostImage uploads"""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            connect=self.max_retries,
            read=self.max_retries,
            status=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Set timeouts
        self.session.timeout = (10, 60)
        
        # Headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def _validate_image_path(self, image_path: str) -> Path:
        """Validate and sanitize image path"""
        path = Path(image_path)
        
        if not path.exists():
            raise PostImageUploadError(f"Image file not found: {image_path}")
            
        if not path.is_file():
            raise PostImageUploadError(f"Path is not a file: {image_path}")
            
        # Security check
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise PostImageUploadError(f"Invalid file path: {e}")
            
        # Check file size
        file_size = resolved_path.stat().st_size
        if file_size > self.max_image_size:
            raise PostImageUploadError(f"Image file too large: {file_size} bytes (max: {self.max_image_size})")
            
        if file_size == 0:
            raise PostImageUploadError("Image file is empty")
            
        return resolved_path
    
    def _calculate_backoff_time(self, attempt: int) -> float:
        """Calculate exponential backoff time with jitter"""
        backoff_time = self.retry_delay * (2 ** attempt)
        jitter = random.uniform(0.5, 1.5)
        return min(backoff_time * jitter, 30.0)
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image to PostImage.org and return the URL
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            Direct image URL if successful, None if failed
            
        Raises:
            PostImageUploadError: If upload fails due to validation or processing issues
        """
        try:
            # Validate image
            validated_path = self._validate_image_path(image_path)
            
            # Read image data
            with open(validated_path, 'rb') as f:
                image_data = f.read()
            
            self.logger.info(f"Image size: {len(image_data)} bytes")
            
            # PostImage.org expects form data upload
            files = {
                'upload': (validated_path.name, image_data, 'image/jpeg')
            }
            
            data = {
                'type': 'file',
                'action': 'upload',
                'timestamp': str(int(time.time())),
                'auth_token': '',  # Not required for anonymous uploads
                'nsfw': '0',
            }
            
            # Upload with retry mechanism
            last_exception = None
            for attempt in range(self.max_retries):
                try:
                    self.logger.info(f"Uploading to PostImage.org (attempt {attempt + 1}/{self.max_retries})...")
                    
                    response = self.session.post(
                        'https://postimages.org/',
                        files=files,
                        data=data
                    )
                    
                    self.logger.debug(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        # PostImage returns HTML with image URL
                        html_content = response.text
                        
                        # Extract direct image URL from response
                        # Look for patterns like: https://i.postimg.cc/...
                        import re
                        url_patterns = [
                            r'https://i\.postimg\.cc/[a-zA-Z0-9/]+\.[a-zA-Z]{3,4}',
                            r'https://postimg\.cc/[a-zA-Z0-9]+',
                        ]
                        
                        for pattern in url_patterns:
                            matches = re.findall(pattern, html_content)
                            if matches:
                                image_url = matches[0]
                                self.logger.info(f"✅ PostImage upload successful: {image_url}")
                                return image_url
                        
                        # If no URL found, log response for debugging
                        self.logger.warning("No image URL found in response")
                        self.logger.debug(f"Response content (first 1000 chars): {html_content[:1000]}")
                        
                    elif response.status_code == 413:
                        raise PostImageUploadError("Image too large for PostImage.org")
                        
                    elif response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            wait_time = self._calculate_backoff_time(attempt)
                            self.logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise PostImageUploadError("Rate limit exceeded")
                            
                    else:
                        if attempt < self.max_retries - 1:
                            wait_time = self._calculate_backoff_time(attempt)
                            self.logger.warning(f"HTTP {response.status_code}, retrying in {wait_time:.1f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise PostImageUploadError(f"Upload failed with status {response.status_code}")
                
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    self.logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        wait_time = self._calculate_backoff_time(attempt)
                        self.logger.info(f"Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise PostImageUploadError(f"Network error after all retries: {e}")
            
            # If we get here, all retries failed
            if last_exception:
                raise PostImageUploadError(f"Upload failed after {self.max_retries} retries: {last_exception}")
            else:
                raise PostImageUploadError("Upload failed after all retry attempts")
                
        except PostImageUploadError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise PostImageUploadError(f"Unexpected upload error: {e}")
    
    @staticmethod
    def verify_image_url(url: str, timeout: int = 10) -> bool:
        """Verify if PostImage URL is accessible
        
        Args:
            url: PostImage URL to verify
            timeout: Request timeout in seconds
            
        Returns:
            True if URL is valid and accessible, False otherwise
        """
        logger = logging.getLogger(__name__)
        
        if not url or not isinstance(url, str):
            logger.warning("Invalid URL provided for verification")
            return False
            
        if not (url.startswith('https://i.postimg.cc/') or url.startswith('https://postimg.cc/')):
            logger.warning(f"Non-PostImage URL: {url}")
            return False
        
        try:
            response = requests.head(url, timeout=timeout)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if content_type.startswith('image/'):
                    logger.info(f"✅ PostImage URL verified: {url}")
                    return True
                else:
                    logger.warning(f"URL is not an image: {content_type}")
                    return False
            else:
                logger.warning(f"URL returned status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"URL verification failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test PostImage.org service availability
        
        Returns:
            True if PostImage is accessible, False otherwise
        """
        try:
            response = self.session.get('https://postimages.org/', timeout=10)
            if response.status_code == 200:
                self.logger.info("✅ PostImage.org service is accessible")
                return True
            else:
                self.logger.warning(f"PostImage returned status {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"PostImage connection test failed: {e}")
            return False