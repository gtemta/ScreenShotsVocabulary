"""
Telegraph Image Uploader
A simple, reliable image uploader using Telegraph's free image hosting service.
No API key required, high reliability, perfect for non-confidential images.
"""

import os
import logging
import time
import random
from pathlib import Path
from typing import Optional, List
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

class TelegraphUploaderError(Exception):
    """Base exception for Telegraph uploader errors"""
    pass

class TelegraphUploadError(TelegraphUploaderError):
    """Upload operation errors"""
    pass

class TelegraphUploader:
    """Telegraph image uploader - simple, reliable, no API key required"""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        """Initialize Telegraph uploader
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_image_size = 5 * 1024 * 1024  # 5MB limit
        
        self._setup_session()
        
    def _setup_session(self) -> None:
        """Configure requests session for Telegraph uploads"""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            connect=self.max_retries,
            read=self.max_retries,
            status=self.max_retries,
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
        
        # Set reasonable timeouts
        self.session.timeout = (10, 60)
        
        # User agent
        self.session.headers.update({
            'User-Agent': 'ScreenShotsVocabulary/1.0 Telegraph-Uploader',
            'Accept': 'application/json, text/html, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def _validate_image_path(self, image_path: str) -> Path:
        """Validate and sanitize image path"""
        path = Path(image_path)
        
        if not path.exists():
            raise TelegraphUploadError(f"Image file not found: {image_path}")
            
        if not path.is_file():
            raise TelegraphUploadError(f"Path is not a file: {image_path}")
            
        # Security check: resolve path to prevent directory traversal
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise TelegraphUploadError(f"Invalid file path: {e}")
            
        # Check file size
        file_size = resolved_path.stat().st_size
        if file_size > self.max_image_size * 2:  # Allow 2x for compression
            raise TelegraphUploadError(f"Image file too large: {file_size} bytes (max: {self.max_image_size * 2})")
            
        if file_size == 0:
            raise TelegraphUploadError("Image file is empty")
            
        return resolved_path
    
    def _compress_image_if_needed(self, image_path: Path) -> bytes:
        """Compress image if it's too large, otherwise return raw data"""
        try:
            # First, try to read the file as-is
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # If image is small enough, return as-is
            if len(image_data) <= self.max_image_size:
                self.logger.info(f"Image size OK: {len(image_data)} bytes")
                return image_data
            
            # If PIL is not available and image is too large, fail
            if not PIL_AVAILABLE:
                raise TelegraphUploadError(
                    f"Image too large ({len(image_data)} bytes) and PIL not available for compression"
                )
            
            # Compress using PIL
            self.logger.info(f"Compressing large image: {len(image_data)} bytes")
            return self._compress_with_pil(image_path)
            
        except TelegraphUploadError:
            raise
        except Exception as e:
            raise TelegraphUploadError(f"Failed to process image: {e}")
    
    def _compress_with_pil(self, image_path: Path) -> bytes:
        """Compress image using PIL"""
        try:
            with Image.open(image_path) as img:
                # Validate image format
                if img.format not in ('JPEG', 'PNG', 'GIF', 'WEBP'):
                    raise TelegraphUploadError(f"Unsupported image format: {img.format}")
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    if img.mode == 'P' and 'transparency' in img.info:
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Progressive quality reduction
                import io
                for quality in [85, 75, 65, 55, 45, 35]:
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= self.max_image_size:
                        self.logger.info(f"Compressed to {len(compressed_data)} bytes at quality {quality}")
                        return compressed_data
                
                # If still too large, resize the image
                self.logger.info("Resizing image to reduce size further")
                for scale in [0.8, 0.6, 0.4, 0.2]:
                    new_width = int(img.width * scale)
                    new_height = int(img.height * scale)
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    output = io.BytesIO()
                    resized_img.save(output, format='JPEG', quality=75, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= self.max_image_size:
                        self.logger.info(f"Resized and compressed to {len(compressed_data)} bytes (scale: {scale})")
                        return compressed_data
                
                raise TelegraphUploadError("Cannot compress image to acceptable size")
                
        except TelegraphUploadError:
            raise
        except Exception as e:
            raise TelegraphUploadError(f"Image compression failed: {e}")
    
    def _calculate_backoff_time(self, attempt: int) -> float:
        """Calculate exponential backoff time with jitter"""
        backoff_time = self.retry_delay * (2 ** attempt)
        jitter = random.uniform(0.5, 1.5)
        return min(backoff_time * jitter, 30.0)
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image to Telegraph and return the URL
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            Direct image URL if successful, None if failed
            
        Raises:
            TelegraphUploadError: If upload fails due to validation or processing issues
        """
        try:
            # Validate and process image
            validated_path = self._validate_image_path(image_path)
            image_data = self._compress_image_if_needed(validated_path)
            
            # Prepare upload data - Telegraph specific format
            files = {
                'file': (validated_path.name, image_data, 'image/jpeg')
            }
            
            # Try alternative formats if first attempt fails
            alternative_formats = [
                {'file': (validated_path.name, image_data, 'image/jpeg')},
                {'image': (validated_path.name, image_data, 'image/jpeg')},
                {'upload': (validated_path.name, image_data, 'image/jpeg')},
            ]
            
            # Upload with retry mechanism and format alternatives
            last_exception = None
            for attempt in range(self.max_retries):
                try:
                    # Try different field names for HTTP 400 errors
                    if attempt < len(alternative_formats):
                        current_files = alternative_formats[attempt]
                        format_info = list(current_files.keys())[0]
                    else:
                        current_files = files
                        format_info = "file"
                    
                    self.logger.info(f"Uploading to Telegraph (attempt {attempt + 1}/{self.max_retries}, format: {format_info})...")
                    
                    response = self.session.post(
                        'https://telegra.ph/upload',
                        files=current_files
                    )
                    
                    # Check response
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            
                            # Telegraph returns a list with upload results
                            if isinstance(result, list) and len(result) > 0:
                                upload_result = result[0]
                                if 'src' in upload_result:
                                    # Construct full URL
                                    image_url = f"https://telegra.ph{upload_result['src']}"
                                    self.logger.info(f"✅ Telegraph upload successful: {image_url}")
                                    return image_url
                                else:
                                    self.logger.error(f"Invalid response format: {result}")
                            else:
                                self.logger.error(f"Unexpected response format: {result}")
                                
                        except ValueError as e:
                            self.logger.error(f"Failed to parse JSON response: {e}")
                            self.logger.debug(f"Response content: {response.text[:500]}")
                            
                    elif response.status_code == 413:
                        raise TelegraphUploadError("Image too large for Telegraph")
                        
                    elif response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            wait_time = self._calculate_backoff_time(attempt)
                            self.logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise TelegraphUploadError("Rate limit exceeded")
                            
                    else:
                        if attempt < self.max_retries - 1:
                            wait_time = self._calculate_backoff_time(attempt)
                            self.logger.warning(f"HTTP {response.status_code}, retrying in {wait_time:.1f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise TelegraphUploadError(f"Upload failed with status {response.status_code}")
                
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    self.logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        wait_time = self._calculate_backoff_time(attempt)
                        self.logger.info(f"Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise TelegraphUploadError(f"Network error after all retries: {e}")
            
            # If we get here, all retries failed
            if last_exception:
                raise TelegraphUploadError(f"Upload failed after {self.max_retries} retries: {last_exception}")
            else:
                raise TelegraphUploadError("Upload failed after all retry attempts")
                
        except TelegraphUploadError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise TelegraphUploadError(f"Unexpected upload error: {e}")
    
    @staticmethod
    def verify_image_url(url: str, timeout: int = 10) -> bool:
        """Verify if Telegraph image URL is accessible
        
        Args:
            url: Telegraph image URL to verify
            timeout: Request timeout in seconds
            
        Returns:
            True if URL is valid and accessible, False otherwise
        """
        logger = logging.getLogger(__name__)
        
        if not url or not isinstance(url, str):
            logger.warning("Invalid URL provided for verification")
            return False
            
        if not url.startswith('https://telegra.ph/'):
            logger.warning(f"Non-Telegraph URL: {url}")
            return False
        
        try:
            response = requests.head(url, timeout=timeout)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if content_type.startswith('image/'):
                    logger.info(f"✅ Telegraph URL verified: {url}")
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
        """Test Telegraph service availability
        
        Returns:
            True if Telegraph is accessible, False otherwise
        """
        try:
            response = self.session.get('https://telegra.ph', timeout=10)
            if response.status_code == 200:
                self.logger.info("✅ Telegraph service is accessible")
                return True
            else:
                self.logger.warning(f"Telegraph returned status {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Telegraph connection test failed: {e}")
            return False