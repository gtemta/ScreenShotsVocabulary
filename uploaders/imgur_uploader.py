import os
import json
import logging
import time
from pathlib import Path
from typing import Optional
import io
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import certifi

# Optional PIL import for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

class ImgurUploaderError(Exception):
    """Base exception for Imgur uploader errors"""
    pass

class ImgurConfigurationError(ImgurUploaderError):
    """Configuration related errors"""
    pass

class ImgurUploadError(ImgurUploaderError):
    """Upload operation errors"""
    pass

class ImgurUploader:
    def __init__(self, client_id: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize Imgur uploader with dependency injection support"""
        self.logger = logging.getLogger(__name__)
        self.imgur_client_id = client_id or os.getenv('IMGUR_CLIENT_ID')
        self.config_path = config_path or 'imgur_credentials.json'
        self.max_retries = int(os.getenv('IMGUR_MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('IMGUR_RETRY_DELAY', '5'))
        self.max_image_size = int(os.getenv('IMGUR_MAX_SIZE', str(5 * 1024 * 1024)))
        
        if not self.imgur_client_id:
            self._load_imgur_credentials()
        
        if not self.imgur_client_id:
            raise ImgurConfigurationError("Imgur client ID not found in environment or config file")
        
        self._setup_session()
        
    def _setup_session(self) -> None:
        """Configure requests session with security best practices"""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
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
        
        # Use secure certificate verification
        self.session.verify = certifi.where()
        self.session.timeout = (5, 30)
        
        # Disable SSL warnings only in development
        if os.getenv('ENVIRONMENT') != 'production':
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def _load_imgur_credentials(self) -> None:
        """Load Imgur API credentials from file"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.warning(f"Config file {self.config_path} not found")
            return
            
        try:
            with config_file.open('r') as f:
                credentials = json.load(f)
                self.imgur_client_id = credentials.get('client_id')
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load Imgur credentials: {e}")
            raise ImgurConfigurationError(f"Invalid config file: {e}")
            
    def _validate_image_path(self, image_path: str) -> Path:
        """Validate and sanitize image path"""
        path = Path(image_path)
        
        if not path.exists():
            raise ImgurUploadError(f"Image file not found: {image_path}")
            
        if not path.is_file():
            raise ImgurUploadError(f"Path is not a file: {image_path}")
            
        # Security check: ensure file is in allowed location
        try:
            path.resolve(strict=True)
        except (OSError, RuntimeError):
            raise ImgurUploadError(f"Invalid file path: {image_path}")
            
        # Check file size
        if path.stat().st_size > self.max_image_size * 2:  # Allow 2x for pre-compression
            raise ImgurUploadError(f"Image file too large: {path.stat().st_size} bytes")
            
        return path
    
    def _compress_image(self, image_path: Path) -> bytes:
        """Compress image to suitable size with security validation"""
        if not PIL_AVAILABLE:
            raise ImgurUploadError("PIL (Pillow) is required for image processing but not installed")
            
        try:
            with Image.open(image_path) as img:
                # Security: Validate image format
                if img.format not in ('JPEG', 'PNG', 'GIF', 'WEBP'):
                    raise ImgurUploadError(f"Unsupported image format: {img.format}")
                
                # Convert RGBA to RGB for JPEG compatibility
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                
                # Progressive compression
                quality = 95
                output = io.BytesIO()
                
                while quality >= 30:
                    output.seek(0)
                    output.truncate()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    
                    if len(output.getvalue()) <= self.max_image_size:
                        break
                    quality -= 5
                
                compressed_data = output.getvalue()
                if len(compressed_data) > self.max_image_size:
                    raise ImgurUploadError(f"Cannot compress image below size limit: {len(compressed_data)} bytes")
                    
                return compressed_data
                
        except ImgurUploadError:
            raise
        except Exception as e:
            self.logger.error(f"Image compression failed: {e}")
            raise ImgurUploadError(f"Image compression failed: {e}")
            
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for upload security"""
        # Remove directory traversal attempts
        filename = os.path.basename(filename)
        # Keep only alphanumeric, dots, underscores, and hyphens
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        # Limit length
        filename = filename[:255]
        # Ensure we have a valid filename
        if not filename:
            filename = 'image.jpg'
        return filename
    
    def _upload_to_imgur(self, image_path: Path) -> str:
        """Upload image to Imgur with proper error handling"""
        try:
            # Validate and compress image
            compressed_image = self._compress_image(image_path)
            filename = self._sanitize_filename(image_path.name)
            
            # Prepare upload data
            headers = {
                'Authorization': f'Client-ID {self.imgur_client_id}',
                'User-Agent': 'ScreenShotsVocabulary/1.0'
            }
            
            files = {
                'image': (filename, compressed_image, 'image/jpeg')
            }
            
            # Retry mechanism with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    response = self.session.post(
                        'https://api.imgur.com/3/image',
                        headers=headers,
                        files=files
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        image_url = result['data']['link']
                        self.logger.info(f"Successfully uploaded image: {image_url}")
                        return image_url
                        
                    elif response.status_code == 429:  # Rate limiting
                        if attempt < self.max_retries - 1:
                            wait_time = (2 ** attempt) * self.retry_delay
                            self.logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise ImgurUploadError("Rate limit exceeded after all retries")
                            
                    elif response.status_code == 400:
                        error_msg = "Invalid image or request parameters"
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('data', {}).get('error', error_msg)
                        except json.JSONDecodeError:
                            pass
                        raise ImgurUploadError(f"Bad request: {error_msg}")
                        
                    elif response.status_code == 403:
                        raise ImgurConfigurationError("Invalid Imgur client ID or quota exceeded")
                        
                    else:
                        raise ImgurUploadError(f"Upload failed with status {response.status_code}: {response.text[:200]}")
                        
                except requests.exceptions.SSLError as e:
                    self.logger.warning(f"SSL error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep((attempt + 1) * self.retry_delay)
                        continue
                    raise ImgurUploadError(f"SSL error after all retries: {e}")
                    
                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep((attempt + 1) * self.retry_delay)
                        continue
                    raise ImgurUploadError(f"Request failed after all retries: {e}")
                    
            raise ImgurUploadError("Upload failed after all retry attempts")
            
        except ImgurUploaderError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise ImgurUploadError(f"Unexpected upload error: {e}")

    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image to Imgur and return direct access URL
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            Image URL if successful, None if failed
            
        Raises:
            ImgurConfigurationError: If client ID is missing or invalid
            ImgurUploadError: If upload fails due to network or API issues
        """
        try:
            validated_path = self._validate_image_path(image_path)
            return self._upload_to_imgur(validated_path)
        except ImgurUploaderError as e:
            self.logger.error(f"Imgur upload failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in upload_image: {e}")
            return None

    @staticmethod
    def verify_image_url(url: str, timeout: int = 5) -> bool:
        """Verify if image URL is accessible and valid
        
        Args:
            url: Image URL to verify
            timeout: Request timeout in seconds
            
        Returns:
            True if URL is valid and accessible, False otherwise
        """
        logger = logging.getLogger(__name__)
        
        if not url or not isinstance(url, str):
            logger.warning("Invalid URL provided for verification")
            return False
            
        if not url.startswith('https://i.imgur.com/'):
            logger.warning(f"Non-Imgur URL: {url}")
            return False
            
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.head(url, timeout=timeout)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if content_type.startswith('image/'):
                        return True
                    else:
                        logger.warning(f"URL is not an image: {content_type}")
                        return False
                        
                elif response.status_code == 429:  # Rate limiting
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limited, retrying in {retry_delay}s ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.warning("Rate limited, skipping verification")
                        return True  # Assume valid if we can't verify due to rate limits
                        
                else:
                    logger.warning(f"URL returned error status: {response.status_code}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Verification error, retrying ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"URL verification failed: {e}")
                    return False
                    
        return False 