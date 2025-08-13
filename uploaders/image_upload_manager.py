"""
Multi-Provider Image Upload Manager
Provides fallback mechanism across multiple image hosting providers.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Import available uploaders
try:
    from .telegraph_uploader import TelegraphUploader, TelegraphUploaderError
    TELEGRAPH_AVAILABLE = True
except ImportError:
    TELEGRAPH_AVAILABLE = False

try:
    from .imgur_uploader import ImgurUploader, ImgurUploaderError
    IMGUR_AVAILABLE = True
except ImportError:
    IMGUR_AVAILABLE = False

try:
    from .imgbb_uploader import ImgBBUploader, ImgBBUploaderError
    IMGBB_AVAILABLE = True
except ImportError:
    IMGBB_AVAILABLE = False

class ImageUploadError(Exception):
    """Base exception for image upload operations"""
    pass

class NoUploadersAvailableError(ImageUploadError):
    """No image uploaders are available or configured"""
    pass

class UploadProvider:
    """Wrapper for image upload providers"""
    
    def __init__(self, name: str, uploader: Any, enabled: bool = True, priority: int = 10):
        self.name = name
        self.uploader = uploader
        self.enabled = enabled
        self.priority = priority
        self.success_count = 0
        self.failure_count = 0
        self.last_error = None
        
    def upload(self, image_path: str) -> Optional[str]:
        """Upload image using this provider"""
        try:
            result = self.uploader.upload_image(image_path)
            if result:
                self.success_count += 1
                self.last_error = None
                return result
            else:
                self.failure_count += 1
                self.last_error = "Upload returned None"
                return None
        except Exception as e:
            self.failure_count += 1
            self.last_error = str(e)
            raise
    
    def test_connection(self) -> bool:
        """Test provider connectivity"""
        try:
            if hasattr(self.uploader, 'test_connection'):
                return self.uploader.test_connection()
            return True
        except Exception:
            return False
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def __str__(self):
        return f"{self.name} (Success: {self.success_count}, Failed: {self.failure_count}, Rate: {self.success_rate:.1%})"

class ImageUploadManager:
    """Multi-provider image upload manager with fallback support"""
    
    def __init__(self, preferred_provider: Optional[str] = None):
        """Initialize the upload manager
        
        Args:
            preferred_provider: Preferred provider name ('telegraph', 'imgur', 'auto')
        """
        self.logger = logging.getLogger(__name__)
        self.providers: List[UploadProvider] = []
        self.preferred_provider = preferred_provider or os.getenv('IMAGE_UPLOAD_PROVIDER', 'auto')
        
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize available upload providers"""
        # ImgBB (highest priority if API key available - most reliable)
        if IMGBB_AVAILABLE:
            try:
                imgbb_api_key = os.getenv('IMGBB_API_KEY')
                config_file = Path('imgbb_credentials.json')
                
                if imgbb_api_key or config_file.exists():
                    imgbb = ImgBBUploader()
                    provider = UploadProvider(
                        name="imgbb",
                        uploader=imgbb,
                        enabled=True,
                        priority=1  # Highest priority when available
                    )
                    self.providers.append(provider)
                    self.logger.info("✅ ImgBB uploader initialized (preferred)")
                else:
                    self.logger.info("ℹ️ ImgBB uploader skipped (no credentials)")
            except Exception as e:
                self.logger.warning(f"Failed to initialize ImgBB uploader: {e}")
        
        # Telegraph (secondary - no API key required but has format issues)
        if TELEGRAPH_AVAILABLE:
            try:
                telegraph = TelegraphUploader()
                provider = UploadProvider(
                    name="telegraph",
                    uploader=telegraph,
                    enabled=True,
                    priority=2  # Secondary priority due to API restrictions
                )
                self.providers.append(provider)
                self.logger.info("✅ Telegraph uploader initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Telegraph uploader: {e}")
        
        # Imgur (tertiary - requires API key, has SSL issues)
        if IMGUR_AVAILABLE:
            try:
                # Only initialize if we have credentials
                imgur_client_id = os.getenv('IMGUR_CLIENT_ID')
                config_file = Path('imgur_credentials.json')
                
                if imgur_client_id or config_file.exists():
                    imgur = ImgurUploader()
                    provider = UploadProvider(
                        name="imgur",
                        uploader=imgur,
                        enabled=True,
                        priority=3  # Tertiary priority (due to SSL issues)
                    )
                    self.providers.append(provider)
                    self.logger.info("✅ Imgur uploader initialized")
                else:
                    self.logger.info("ℹ️ Imgur uploader skipped (no credentials)")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Imgur uploader: {e}")
        
        # Sort providers by priority
        self.providers.sort(key=lambda p: p.priority)
        
        if not self.providers:
            raise NoUploadersAvailableError("No image uploaders available")
        
        self.logger.info(f"Initialized {len(self.providers)} upload providers")
        
    def _get_upload_order(self) -> List[UploadProvider]:
        """Get providers in upload order based on preferences and success rates"""
        available_providers = [p for p in self.providers if p.enabled]
        
        if not available_providers:
            raise NoUploadersAvailableError("No enabled upload providers")
        
        # If specific provider is preferred and available, try it first
        if self.preferred_provider != 'auto':
            preferred = next((p for p in available_providers if p.name == self.preferred_provider), None)
            if preferred:
                # Move preferred to front, keep others in priority order
                ordered = [preferred]
                ordered.extend([p for p in available_providers if p != preferred])
                return ordered
        
        # Auto mode: sort by success rate, then priority
        return sorted(available_providers, key=lambda p: (-p.success_rate, p.priority))
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image with multi-provider fallback
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            Image URL if successful, None if all providers failed
            
        Raises:
            ImageUploadError: If validation fails or no providers available
            NoUploadersAvailableError: If no uploaders are configured
        """
        if not image_path or not isinstance(image_path, str):
            raise ImageUploadError("Invalid image path provided")
        
        if not Path(image_path).exists():
            raise ImageUploadError(f"Image file not found: {image_path}")
        
        try:
            providers_to_try = self._get_upload_order()
        except NoUploadersAvailableError:
            raise
        
        self.logger.info(f"Attempting upload with {len(providers_to_try)} providers")
        
        upload_errors = []
        
        for provider in providers_to_try:
            try:
                self.logger.info(f"Trying {provider.name} uploader...")
                
                url = provider.upload(image_path)
                
                if url:
                    self.logger.info(f"✅ Upload successful via {provider.name}: {url}")
                    
                    # Verify URL if possible
                    if hasattr(provider.uploader, 'verify_image_url'):
                        if provider.uploader.verify_image_url(url):
                            self.logger.info(f"✅ URL verified: {url}")
                        else:
                            self.logger.warning(f"⚠️ URL verification failed, but proceeding: {url}")
                    
                    return url
                else:
                    error_msg = f"{provider.name} returned None"
                    upload_errors.append(error_msg)
                    self.logger.warning(f"❌ {error_msg}")
                    
            except Exception as e:
                error_msg = f"{provider.name} failed: {e}"
                upload_errors.append(error_msg)
                self.logger.warning(f"❌ {error_msg}")
                continue
        
        # All providers failed
        self.logger.error("❌ All upload providers failed")
        for error in upload_errors:
            self.logger.error(f"  - {error}")
        
        return None
    
    def test_all_providers(self) -> Dict[str, bool]:
        """Test connectivity for all providers
        
        Returns:
            Dictionary mapping provider names to test results
        """
        results = {}
        
        for provider in self.providers:
            self.logger.info(f"Testing {provider.name} connectivity...")
            try:
                result = provider.test_connection()
                results[provider.name] = result
                status = "✅ OK" if result else "❌ Failed"
                self.logger.info(f"{provider.name}: {status}")
            except Exception as e:
                results[provider.name] = False
                self.logger.error(f"{provider.name}: ❌ Error: {e}")
        
        return results
    
    def get_provider_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all providers
        
        Returns:
            List of provider statistics
        """
        stats = []
        
        for provider in self.providers:
            stats.append({
                'name': provider.name,
                'enabled': provider.enabled,
                'priority': provider.priority,
                'success_count': provider.success_count,
                'failure_count': provider.failure_count,
                'success_rate': provider.success_rate,
                'last_error': provider.last_error
            })
        
        return stats
    
    def set_provider_enabled(self, provider_name: str, enabled: bool):
        """Enable or disable a specific provider
        
        Args:
            provider_name: Name of the provider to modify
            enabled: Whether to enable or disable the provider
        """
        provider = next((p for p in self.providers if p.name == provider_name), None)
        if provider:
            provider.enabled = enabled
            status = "enabled" if enabled else "disabled"
            self.logger.info(f"Provider {provider_name} {status}")
        else:
            self.logger.warning(f"Provider {provider_name} not found")
    
    def reset_provider_stats(self):
        """Reset statistics for all providers"""
        for provider in self.providers:
            provider.success_count = 0
            provider.failure_count = 0
            provider.last_error = None
        self.logger.info("Provider statistics reset")
    
    def __str__(self):
        if not self.providers:
            return "ImageUploadManager (no providers)"
        
        provider_list = [str(p) for p in self.providers]
        return f"ImageUploadManager:\n" + "\n".join(f"  - {p}" for p in provider_list)