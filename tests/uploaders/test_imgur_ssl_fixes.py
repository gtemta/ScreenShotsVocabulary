#!/usr/bin/env python3
"""
Imgur upload test with SSL workarounds for Ubuntu environment.
"""

import os
import sys
import json
import logging
import ssl
import urllib3
from pathlib import Path

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_imgur_client_id():
    """Get Imgur client ID from environment or config file"""
    # Try environment variable first
    client_id = os.getenv('IMGUR_CLIENT_ID')
    if client_id:
        return client_id
    
    # Try config file
    config_file = Path("imgur_credentials.json")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                credentials = json.load(f)
                return credentials.get('client_id')
        except Exception as e:
            logger.error(f"Failed to read config file: {e}")
    
    return None

def test_imgur_with_ssl_workaround():
    """Test imgur upload with various SSL workarounds"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    # Get client ID
    client_id = get_imgur_client_id()
    if not client_id:
        logger.error("❌ No Imgur client ID found!")
        return False
    
    logger.info(f"✅ Found Imgur client ID: {client_id[:8]}...")
    
    # Find test image
    test_images = list(Path(".").glob("*.jpg"))
    if not test_images:
        logger.error("❌ No test images found (*.jpg)")
        return False
    
    test_image = test_images[0]
    logger.info(f"Using test image: {test_image.name}")
    
    # Strategy 1: Disable SSL verification
    logger.info("=== Strategy 1: Disable SSL verification ===")
    try:
        session = requests.Session()
        session.verify = False
        
        with open(test_image, 'rb') as f:
            image_data = f.read()
        
        headers = {
            'Authorization': f'Client-ID {client_id}',
            'User-Agent': 'ScreenShotsVocabulary-Test/1.0'
        }
        
        files = {'image': (test_image.name, image_data, 'image/jpeg')}
        
        response = session.post(
            'https://api.imgur.com/3/image',
            headers=headers,
            files=files,
            timeout=(15, 90)
        )
        
        if response.status_code == 200:
            result = response.json()
            image_url = result['data']['link']
            logger.info(f"✅ Strategy 1 SUCCESS! Image URL: {image_url}")
            return True
        else:
            logger.warning(f"Strategy 1 failed with status: {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Strategy 1 failed: {e}")
    
    # Strategy 2: Custom SSL context
    logger.info("=== Strategy 2: Custom SSL context ===")
    try:
        session = requests.Session()
        
        # Create permissive SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
        
        class CustomHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                kwargs['ssl_context'] = ssl_context
                return super().init_poolmanager(*args, **kwargs)
        
        session.mount("https://", CustomHTTPAdapter())
        session.verify = False
        
        with open(test_image, 'rb') as f:
            image_data = f.read()
            
        files = {'image': (test_image.name, image_data, 'image/jpeg')}
        
        response = session.post(
            'https://api.imgur.com/3/image',
            headers=headers,
            files=files,
            timeout=(15, 90)
        )
        
        if response.status_code == 200:
            result = response.json()
            image_url = result['data']['link']
            logger.info(f"✅ Strategy 2 SUCCESS! Image URL: {image_url}")
            return True
        else:
            logger.warning(f"Strategy 2 failed with status: {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Strategy 2 failed: {e}")
    
    # Strategy 3: HTTP instead of HTTPS (if available)
    logger.info("=== Strategy 3: Test connectivity only ===")
    try:
        session = requests.Session()
        session.verify = False
        
        # Just test basic connectivity to Imgur
        response = session.get('https://imgur.com', timeout=10)
        logger.info(f"Imgur connectivity test: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Can reach Imgur, but API upload failed due to SSL")
            logger.info("This suggests a network/firewall SSL issue in Ubuntu environment")
        
    except Exception as e:
        logger.error(f"Even basic connectivity failed: {e}")
    
    return False

def diagnose_ssl_environment():
    """Diagnose SSL environment issues"""
    logger.info("=== SSL Environment Diagnosis ===")
    
    # Check SSL module info
    logger.info(f"SSL module version: {ssl.OPENSSL_VERSION}")
    logger.info(f"SSL supports SNI: {ssl.HAS_SNI}")
    logger.info(f"SSL supports TLS 1.3: {hasattr(ssl, 'PROTOCOL_TLS')}")
    
    # Check available ciphers
    try:
        context = ssl.create_default_context()
        ciphers = context.get_ciphers()
        logger.info(f"Available cipher suites: {len(ciphers)}")
    except Exception as e:
        logger.warning(f"Cannot get cipher info: {e}")
    
    # Check CA bundle
    try:
        import certifi
        ca_bundle = certifi.where()
        logger.info(f"CA bundle location: {ca_bundle}")
        logger.info(f"CA bundle exists: {os.path.exists(ca_bundle)}")
    except ImportError:
        logger.warning("certifi not available")
    
    # Check environment variables
    ssl_related_vars = ['SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE']
    for var in ssl_related_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"{var}: {value}")

if __name__ == "__main__":
    print("=" * 60)
    print("Imgur Upload Test with SSL Workarounds")
    print("=" * 60)
    
    diagnose_ssl_environment()
    
    print("\n" + "=" * 40)
    print("Testing Upload Strategies")
    print("=" * 40)
    
    success = test_imgur_with_ssl_workaround()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Found working upload method!")
    else:
        print("❌ TEST FAILED: All upload strategies failed")
        print("This indicates a network/SSL configuration issue in the Ubuntu environment")
        print("Possible solutions:")
        print("1. Update system SSL certificates: sudo apt update && sudo apt install ca-certificates")
        print("2. Update Python SSL: pip install --upgrade certifi")
        print("3. Check firewall/proxy settings")
        print("4. Try from a different network")
    print("=" * 60)
    
    sys.exit(0 if success else 1)