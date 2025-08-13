"""
ImgBB Image Uploader
Reliable image hosting service with simple API and good performance.
Requires API key but offers excellent uptime and features.
"""

import os
import json
import base64
import logging
import time
import random
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

class ImgBBUploaderError(Exception):
    """Base exception for ImgBB uploader errors"""
    pass

class ImgBBConfigurationError(ImgBBUploaderError):
    """Configuration related errors"""
    pass

class ImgBBUploadError(ImgBBUploaderError):
    """Upload operation errors"""
    pass

class ImgBBUploader:
    """ImgBB image uploader - reliable, requires API key"""
    
    def __init__(self, api_key: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize ImgBB uploader
        
        Args:
            api_key: ImgBB API key
            config_path: Path to config file with API key
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv('IMGBB_API_KEY')
        self.config_path = config_path or 'imgbb_credentials.json'
        self.max_retries = 3
        self.retry_delay = 2
        self.max_image_size = 32 * 1024 * 1024  # 32MB limit for ImgBB
        
        if not self.api_key:
            self._load_credentials()
        
        if not self.api_key:
            raise ImgBBConfigurationError("ImgBB API key not found in environment or config file")
        
        self._setup_session()
    
    def _load_credentials(self) -> None:
        """Load ImgBB API credentials from file"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.warning(f"Config file {self.config_path} not found")
            return
            
        try:
            with config_file.open('r') as f:
                credentials = json.load(f)
                self.api_key = credentials.get('api_key')
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load ImgBB credentials: {e}")
            raise ImgBBConfigurationError(f"Invalid config file: {e}")
    
    def _setup_session(self) -> None:
        """Configure requests session for ImgBB uploads"""
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
        
        # Headers
        self.session.headers.update({
            'User-Agent': 'ScreenShotsVocabulary/1.0 ImgBB-Uploader',
            'Accept': 'application/json',
        })
    
    def _validate_image_path(self, image_path: str) -> Path:
        """Validate and sanitize image path"""
        path = Path(image_path)
        
        if not path.exists():
            raise ImgBBUploadError(f"Image file not found: {image_path}")
            
        if not path.is_file():
            raise ImgBBUploadError(f"Path is not a file: {image_path}")
            
        # Security check
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise ImgBBUploadError(f"Invalid file path: {e}")
            
        # Check file size
        file_size = resolved_path.stat().st_size
        if file_size > self.max_image_size:
            raise ImgBBUploadError(f"Image file too large: {file_size} bytes (max: {self.max_image_size})")
            
        if file_size == 0:
            raise ImgBBUploadError("Image file is empty")
            
        return resolved_path
    
    def _compress_image_if_needed(self, image_path: Path) -> bytes:
        """Compress image if needed to fit size limits"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # If image is acceptable size, return as-is
            if len(image_data) <= self.max_image_size:
                self.logger.info(f"Image size OK: {len(image_data)} bytes")
                return image_data
            
            # If PIL not available and image is too large, fail
            if not PIL_AVAILABLE:
                raise ImgBBUploadError(
                    f"Image too large ({len(image_data)} bytes) and PIL not available for compression"
                )
            
            # Compress using PIL
            self.logger.info(f"Compressing large image: {len(image_data)} bytes")
            return self._compress_with_pil(image_path)
            
        except ImgBBUploadError:
            raise
        except Exception as e:
            raise ImgBBUploadError(f"Failed to process image: {e}")
    
    def _compress_with_pil(self, image_path: Path) -> bytes:
        """Compress image using PIL"""
        try:
            with Image.open(image_path) as img:
                # Validate format
                if img.format not in ('JPEG', 'PNG', 'GIF', 'WEBP', 'BMP'):
                    raise ImgBBUploadError(f"Unsupported image format: {img.format}")
                
                # Convert to RGB for better compression
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
                
                import io
                
                # Try different quality levels
                for quality in [85, 75, 65, 55, 45]:
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= self.max_image_size:
                        self.logger.info(f"Compressed to {len(compressed_data)} bytes at quality {quality}")
                        return compressed_data
                
                # If still too large, resize
                for scale in [0.8, 0.6, 0.4]:
                    new_width = int(img.width * scale)
                    new_height = int(img.height * scale)
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    output = io.BytesIO()
                    resized_img.save(output, format='JPEG', quality=75, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= self.max_image_size:
                        self.logger.info(f"Resized and compressed to {len(compressed_data)} bytes (scale: {scale})")
                        return compressed_data
                
                raise ImgBBUploadError("Cannot compress image to acceptable size")
                
        except ImgBBUploadError:
            raise
        except Exception as e:
            raise ImgBBUploadError(f"Image compression failed: {e}")
    
    def _calculate_backoff_time(self, attempt: int) -> float:
        """Calculate exponential backoff time with jitter"""
        backoff_time = self.retry_delay * (2 ** attempt)
        jitter = random.uniform(0.5, 1.5)
        return min(backoff_time * jitter, 30.0)
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image to ImgBB and return the URL
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            Direct image URL if successful, None if failed
            
        Raises:
            ImgBBUploadError: If upload fails due to validation or processing issues
            ImgBBConfigurationError: If API key is invalid
        """
        try:
            # Validate and process image
            validated_path = self._validate_image_path(image_path)
            image_data = self._compress_image_if_needed(validated_path)
            
            # Encode image as base64 for ImgBB
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare upload data
            data = {
                'key': self.api_key,
                'image': image_base64,
                'name': validated_path.stem,
            }
            
            # Upload with retry mechanism
            last_exception = None
            for attempt in range(self.max_retries):
                try:
                    self.logger.info(f"Uploading to ImgBB (attempt {attempt + 1}/{self.max_retries})...")
                    
                    response = self.session.post(
                        'https://api.imgbb.com/1/upload',
                        data=data
                    )
                    
                    self.logger.debug(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            
                            if result.get('success'):
                                image_url = result['data']['url']
                                self.logger.info(f"✅ ImgBB upload successful: {image_url}")
                                return image_url
                            else:
                                error_msg = result.get('error', {}).get('message', 'Unknown error')
                                raise ImgBBUploadError(f"API returned error: {error_msg}")
                                
                        except (ValueError, KeyError) as e:
                            self.logger.error(f"Failed to parse response: {e}")
                            self.logger.debug(f"Response content: {response.text[:500]}")
                            raise ImgBBUploadError(f"Invalid API response: {e}")
                    
                    elif response.status_code == 400:
                        try:
                            result = response.json()
                            error_msg = result.get('error', {}).get('message', 'Bad request')
                            if 'key' in error_msg.lower():
                                raise ImgBBConfigurationError(f"Invalid API key: {error_msg}")
                            else:
                                raise ImgBBUploadError(f"Bad request: {error_msg}")
                        except (ValueError, KeyError):
                            raise ImgBBUploadError(f"Bad request: {response.text[:200]}")
                    
                    elif response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            wait_time = self._calculate_backoff_time(attempt)
                            self.logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise ImgBBUploadError("Rate limit exceeded")
                    
                    else:
                        if attempt < self.max_retries - 1:
                            wait_time = self._calculate_backoff_time(attempt)
                            self.logger.warning(f"HTTP {response.status_code}, retrying in {wait_time:.1f}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise ImgBBUploadError(f"Upload failed with status {response.status_code}")
                
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    self.logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        wait_time = self._calculate_backoff_time(attempt)
                        self.logger.info(f"Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ImgBBUploadError(f"Network error after all retries: {e}")
            
            # If we get here, all retries failed
            if last_exception:
                raise ImgBBUploadError(f"Upload failed after {self.max_retries} retries: {last_exception}")
            else:
                raise ImgBBUploadError("Upload failed after all retry attempts")
                
        except (ImgBBUploadError, ImgBBConfigurationError):
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise ImgBBUploadError(f"Unexpected upload error: {e}")
    
    @staticmethod
    def verify_image_url(url: str, timeout: int = 10) -> bool:
        """Verify if ImgBB image URL is accessible
        
        Args:
            url: ImgBB image URL to verify
            timeout: Request timeout in seconds
            
        Returns:
            True if URL is valid and accessible, False otherwise
        """
        logger = logging.getLogger(__name__)
        
        if not url or not isinstance(url, str):
            logger.warning("Invalid URL provided for verification")
            return False
            
        if not (url.startswith('https://i.ibb.co/') or url.startswith('https://ibb.co/')):
            logger.warning(f"Non-ImgBB URL: {url}")
            return False
        
        try:
            response = requests.head(url, timeout=timeout)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if content_type.startswith('image/'):
                    logger.info(f"✅ ImgBB URL verified: {url}")
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
        """Test ImgBB service availability and API key validity
        
        Returns:
            True if ImgBB is accessible and API key is valid, False otherwise
        """
        try:
            # Test with minimal request
            data = {
                'key': self.api_key,
                'image': base64.b64encode(b'test').decode('utf-8'),  # Minimal data
            }
            
            response = self.session.post('https://api.imgbb.com/1/upload', data=data, timeout=10)
            
            # We expect this to fail, but should not be due to network/auth issues
            if response.status_code in [200, 400]:  # 400 = bad image data, but API works
                self.logger.info("✅ ImgBB service is accessible and API key is valid")
                return True
            elif response.status_code == 401:
                self.logger.error("❌ Invalid ImgBB API key")
                return False
            else:
                self.logger.warning(f"ImgBB returned unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"ImgBB connection test failed: {e}")
            return False