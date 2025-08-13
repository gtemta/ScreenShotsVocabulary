#!/usr/bin/env python3
"""
Working ImgBB uploader test - tests the reliable ImgBB service.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_imgbb_api_key():
    """Get ImgBB API key from environment or create config"""
    # Try environment variable
    api_key = os.getenv('IMGBB_API_KEY')
    if api_key:
        return api_key
    
    # Try config file
    config_file = Path('imgbb_credentials.json')
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                credentials = json.load(f)
                return credentials.get('api_key')
        except Exception as e:
            logger.error(f"Failed to read ImgBB config: {e}")
    
    # Instructions for getting API key
    logger.info("ImgBB API key not found. To get one:")
    logger.info("1. Go to https://api.imgbb.com/")
    logger.info("2. Create free account")
    logger.info("3. Get your API key")
    logger.info("4. Set IMGBB_API_KEY environment variable or create imgbb_credentials.json:")
    logger.info('   {"api_key": "your_api_key_here"}')
    
    return None

def test_imgbb_upload():
    """Test ImgBB upload functionality"""
    logger.info("=== Testing ImgBB Upload ===")
    
    # Get API key
    api_key = get_imgbb_api_key()
    if not api_key:
        logger.error("❌ ImgBB API key required")
        return False
    
    logger.info(f"✅ Found ImgBB API key: {api_key[:10]}...")
    
    try:
        from uploaders.imgbb_uploader import ImgBBUploader, ImgBBConfigurationError, ImgBBUploadError
        
        # Initialize uploader
        uploader = ImgBBUploader(api_key=api_key)
        
        # Test connection
        logger.info("Testing ImgBB connection and API key...")
        if not uploader.test_connection():
            logger.error("❌ ImgBB connection test failed")
            return False
        logger.info("✅ ImgBB connection and API key OK")
        
        # Find test image
        test_images = list(project_root.glob("*.jpg"))
        if not test_images:
            logger.error("❌ No test images found (*.jpg)")
            return False
        
        test_image = test_images[0]
        logger.info(f"Using test image: {test_image.name} ({test_image.stat().st_size} bytes)")
        
        # Upload image
        logger.info("Uploading to ImgBB...")
        image_url = uploader.upload_image(str(test_image))
        
        if image_url:
            logger.info(f"✅ Upload successful!")
            logger.info(f"Image URL: {image_url}")
            
            # Verify URL
            if uploader.verify_image_url(image_url):
                logger.info("✅ URL verification passed")
            else:
                logger.warning("⚠️ URL verification failed")
            
            return True
        else:
            logger.error("❌ Upload returned None")
            return False
            
    except ImgBBConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        return False
    except ImgBBUploadError as e:
        logger.error(f"❌ Upload error: {e}")
        return False
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_multi_provider_with_imgbb():
    """Test multi-provider manager with ImgBB"""
    logger.info("=== Testing Multi-Provider Manager with ImgBB ===")
    
    try:
        from uploaders.image_upload_manager import ImageUploadManager
        
        # Set ImgBB API key in environment for the manager
        api_key = get_imgbb_api_key()
        if api_key:
            os.environ['IMGBB_API_KEY'] = api_key
        
        # Initialize manager preferring ImgBB
        manager = ImageUploadManager(preferred_provider='imgbb')
        logger.info(f"Manager initialized with {len(manager.providers)} providers")
        
        # Test all providers
        test_results = manager.test_all_providers()
        for provider, result in test_results.items():
            status = "✅ OK" if result else "❌ Failed"
            logger.info(f"  {provider}: {status}")
        
        # Find test image
        test_images = list(project_root.glob("*.jpg"))
        if not test_images:
            logger.error("❌ No test images found")
            return False
        
        test_image = test_images[0]
        logger.info(f"Testing manager upload: {test_image.name}")
        
        # Upload via manager
        image_url = manager.upload_image(str(test_image))
        
        if image_url:
            logger.info(f"✅ Manager upload successful: {image_url}")
            
            # Show stats
            stats = manager.get_provider_stats()
            for stat in stats:
                logger.info(f"  {stat['name']}: {stat['success_count']} success, {stat['failure_count']} failures")
            
            return True
        else:
            logger.error("❌ Manager upload failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Multi-provider test failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("ImgBB Upload Test - Reliable Image Hosting")
    print("="*60)
    
    # Test basic upload
    logger.info("Testing basic ImgBB upload...")
    basic_result = test_imgbb_upload()
    
    print("\n" + "="*60)
    if basic_result:
        print("✅ BASIC TEST PASSED!")
        
        # If basic test passes, test multi-provider
        logger.info("Testing multi-provider system...")
        multi_result = test_multi_provider_with_imgbb()
        
        print("\n" + "="*60)
        if multi_result:
            print("🎉 ALL TESTS PASSED!")
            print("ImgBB uploader is ready for production use.")
            sys.exit(0)
        else:
            print("⚠️ Multi-provider test failed, but basic upload works.")
            sys.exit(1)
    else:
        print("❌ BASIC TEST FAILED!")
        print("Check your ImgBB API key and network connection.")
        sys.exit(1)