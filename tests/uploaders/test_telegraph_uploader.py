#!/usr/bin/env python3
"""
Comprehensive test suite for Telegraph image uploader.
Tests all functionality including edge cases and error handling.
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_image(width: int = 100, height: int = 100, format: str = 'JPEG') -> Path:
    """Create a test image using PIL if available, or use existing image"""
    try:
        from PIL import Image, ImageDraw
        
        # Create a simple test image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add some content
        draw.rectangle([10, 10, width-10, height-10], outline='blue', width=2)
        draw.text((20, 20), f"Test {width}x{height}", fill='black')
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=f'.{format.lower()}', delete=False)
        img.save(temp_file.name, format=format, quality=85)
        temp_file.close()
        
        return Path(temp_file.name)
        
    except ImportError:
        # PIL not available, use existing image
        existing_images = list(project_root.glob("*.jpg"))
        if existing_images:
            return existing_images[0]
        else:
            raise RuntimeError("PIL not available and no existing images found for testing")

def test_telegraph_basic_upload():
    """Test basic Telegraph upload functionality"""
    logger.info("=== Testing Basic Telegraph Upload ===")
    
    try:
        from uploaders.telegraph_uploader import TelegraphUploader, TelegraphUploadError
        
        uploader = TelegraphUploader()
        
        # Test connection first
        logger.info("Testing Telegraph connection...")
        if not uploader.test_connection():
            logger.error("❌ Telegraph connection test failed")
            return False
        logger.info("✅ Telegraph connection OK")
        
        # Create or use test image
        test_image = create_test_image(200, 150)
        logger.info(f"Using test image: {test_image} (size: {test_image.stat().st_size} bytes)")
        
        # Upload image
        logger.info("Uploading test image...")
        image_url = uploader.upload_image(str(test_image))
        
        if image_url:
            logger.info(f"✅ Upload successful: {image_url}")
            
            # Verify URL format
            if image_url.startswith('https://telegra.ph/'):
                logger.info("✅ URL format correct")
            else:
                logger.warning(f"⚠️ Unexpected URL format: {image_url}")
            
            # Verify URL accessibility
            if uploader.verify_image_url(image_url):
                logger.info("✅ URL verification passed")
            else:
                logger.warning("⚠️ URL verification failed")
            
            # Clean up test image if we created it
            if 'tmp' in str(test_image):
                test_image.unlink()
            
            return True
        else:
            logger.error("❌ Upload returned None")
            return False
            
    except Exception as e:
        logger.error(f"❌ Basic upload test failed: {e}")
        return False

def test_telegraph_large_image():
    """Test Telegraph upload with large image"""
    logger.info("=== Testing Large Image Upload ===")
    
    try:
        from uploaders.telegraph_uploader import TelegraphUploader
        
        uploader = TelegraphUploader()
        
        # Create large test image
        test_image = create_test_image(2000, 1500)  # Large image
        logger.info(f"Created large test image: {test_image.stat().st_size} bytes")
        
        # Upload should succeed with compression
        image_url = uploader.upload_image(str(test_image))
        
        if image_url:
            logger.info(f"✅ Large image upload successful: {image_url}")
            # Clean up
            if 'tmp' in str(test_image):
                test_image.unlink()
            return True
        else:
            logger.error("❌ Large image upload failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Large image test failed: {e}")
        return False

def test_telegraph_error_handling():
    """Test Telegraph uploader error handling"""
    logger.info("=== Testing Error Handling ===")
    
    try:
        from uploaders.telegraph_uploader import TelegraphUploader, TelegraphUploadError
        
        uploader = TelegraphUploader()
        
        # Test with non-existent file
        try:
            uploader.upload_image("nonexistent_file.jpg")
            logger.error("❌ Should have failed with non-existent file")
            return False
        except TelegraphUploadError as e:
            logger.info(f"✅ Correctly handled non-existent file: {e}")
        
        # Test with empty file path
        try:
            uploader.upload_image("")
            logger.error("❌ Should have failed with empty path")
            return False
        except TelegraphUploadError as e:
            logger.info(f"✅ Correctly handled empty path: {e}")
        
        # Test with directory instead of file
        try:
            uploader.upload_image(str(project_root))
            logger.error("❌ Should have failed with directory path")
            return False
        except TelegraphUploadError as e:
            logger.info(f"✅ Correctly handled directory path: {e}")
        
        logger.info("✅ Error handling tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False

def test_multi_provider_manager():
    """Test the multi-provider upload manager"""
    logger.info("=== Testing Multi-Provider Manager ===")
    
    try:
        from uploaders.image_upload_manager import ImageUploadManager, NoUploadersAvailableError
        
        # Initialize manager
        manager = ImageUploadManager(preferred_provider='telegraph')
        logger.info(f"Manager initialized: {len(manager.providers)} providers")
        
        # Test provider connectivity
        logger.info("Testing all provider connectivity...")
        test_results = manager.test_all_providers()
        
        for provider, result in test_results.items():
            status = "✅ OK" if result else "❌ Failed"
            logger.info(f"  {provider}: {status}")
        
        # Test upload with manager
        test_image = create_test_image(300, 200)
        logger.info(f"Testing manager upload with: {test_image}")
        
        image_url = manager.upload_image(str(test_image))
        
        if image_url:
            logger.info(f"✅ Manager upload successful: {image_url}")
            
            # Show provider statistics
            stats = manager.get_provider_stats()
            logger.info("Provider Statistics:")
            for stat in stats:
                logger.info(f"  {stat['name']}: {stat['success_count']} success, {stat['failure_count']} failures")
            
            # Clean up
            if 'tmp' in str(test_image):
                test_image.unlink()
            
            return True
        else:
            logger.error("❌ Manager upload failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Multi-provider manager test failed: {e}")
        return False

def test_batch_uploads():
    """Test batch uploads to ensure reliability"""
    logger.info("=== Testing Batch Uploads ===")
    
    try:
        from uploaders.telegraph_uploader import TelegraphUploader
        
        uploader = TelegraphUploader()
        
        # Create multiple test images
        test_images = []
        for i in range(3):
            img = create_test_image(150 + i*50, 100 + i*30)
            test_images.append(img)
        
        logger.info(f"Created {len(test_images)} test images")
        
        # Upload all images
        uploaded_urls = []
        for i, img_path in enumerate(test_images):
            logger.info(f"Uploading image {i+1}/{len(test_images)}: {img_path.name}")
            url = uploader.upload_image(str(img_path))
            
            if url:
                uploaded_urls.append(url)
                logger.info(f"  ✅ Success: {url}")
            else:
                logger.error(f"  ❌ Failed to upload {img_path.name}")
        
        # Clean up test images
        for img_path in test_images:
            if 'tmp' in str(img_path):
                img_path.unlink()
        
        success_rate = len(uploaded_urls) / len(test_images)
        logger.info(f"Batch upload results: {len(uploaded_urls)}/{len(test_images)} successful ({success_rate:.1%})")
        
        if success_rate >= 0.8:  # 80% success rate acceptable
            logger.info("✅ Batch upload test passed")
            return True
        else:
            logger.error("❌ Batch upload success rate too low")
            return False
            
    except Exception as e:
        logger.error(f"❌ Batch upload test failed: {e}")
        return False

def run_comprehensive_tests() -> Dict[str, bool]:
    """Run all comprehensive tests and return results"""
    tests = {
        "Basic Upload": test_telegraph_basic_upload,
        "Large Image": test_telegraph_large_image,
        "Error Handling": test_telegraph_error_handling,
        "Multi-Provider Manager": test_multi_provider_manager,
        "Batch Uploads": test_batch_uploads
    }
    
    results = {}
    
    for test_name, test_func in tests.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info('='*60)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    return results

def check_dependencies():
    """Check if all required dependencies are available"""
    logger.info("Checking dependencies...")
    
    missing_deps = []
    
    # Check required packages
    try:
        import requests
        logger.info("✅ requests available")
    except ImportError:
        missing_deps.append("requests")
    
    try:
        from PIL import Image
        logger.info("✅ PIL/Pillow available")
    except ImportError:
        logger.warning("⚠️ PIL/Pillow not available (image compression disabled)")
    
    if missing_deps:
        logger.error(f"❌ Missing dependencies: {missing_deps}")
        return False
    
    return True

if __name__ == "__main__":
    print("="*80)
    print("COMPREHENSIVE TELEGRAPH UPLOAD TEST SUITE")
    print("="*80)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed!")
        sys.exit(1)
    
    # Run all tests
    logger.info("\nStarting comprehensive test suite...")
    results = run_comprehensive_tests()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
        if result:
            passed += 1
    
    print("="*80)
    print(f"OVERALL RESULT: {passed}/{total} tests passed ({passed/total:.1%})")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Telegraph uploader is ready for production use.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the logs above.")
        sys.exit(1)