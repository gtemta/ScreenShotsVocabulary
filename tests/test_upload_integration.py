#!/usr/bin/env python3
"""
Test all available image upload providers to find what works
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env")
except ImportError:
    print("⚠️ dotenv not available, using system environment only")

def check_environment():
    """Check environment variables and .env file"""
    print("\n=== Environment Check ===")
    
    # Check if .env file exists
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file found")
        # Show IMGBB_API_KEY from file (masked)
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                if 'IMGBB_API_KEY' in content:
                    print("✅ IMGBB_API_KEY found in .env file")
                else:
                    print("❌ IMGBB_API_KEY NOT found in .env file")
        except Exception as e:
            print(f"⚠️ Error reading .env file: {e}")
    else:
        print("❌ .env file not found")
    
    # Check environment variable
    imgbb_key = os.getenv('IMGBB_API_KEY')
    if imgbb_key:
        print(f"✅ IMGBB_API_KEY loaded: {imgbb_key[:10]}...")
    else:
        print("❌ IMGBB_API_KEY not loaded into environment")
    
    # Show all environment variables containing 'IMGBB'
    imgbb_vars = {k: v for k, v in os.environ.items() if 'IMGBB' in k}
    if imgbb_vars:
        print("Environment variables with 'IMGBB':")
        for k, v in imgbb_vars.items():
            masked_value = v[:10] + "..." if len(v) > 10 else v
            print(f"  {k}: {masked_value}")
    else:
        print("No IMGBB environment variables found")

def test_all_providers():
    """Test each provider individually"""
    
    # Find test image
    test_images = list(project_root.glob("*.jpg"))
    if not test_images:
        print("❌ No test images found")
        return
    
    test_image = test_images[0]
    print(f"Testing with: {test_image.name} ({test_image.stat().st_size} bytes)")
    
    # Test 1: ImgBB (if API key available)
    imgbb_key = os.getenv('IMGBB_API_KEY')
    if imgbb_key:
        print("\n🔵 Testing ImgBB...")
        try:
            from uploaders.imgbb_uploader import ImgBBUploader
            uploader = ImgBBUploader(api_key=imgbb_key)
            url = uploader.upload_image(str(test_image))
            if url:
                print(f"✅ ImgBB SUCCESS: {url}")
                return url
            else:
                print("❌ ImgBB failed")
        except Exception as e:
            print(f"❌ ImgBB error: {e}")
    else:
        print("🔵 ImgBB skipped (no API key)")
    
    # Test 2: Telegraph (with fixes)
    print("\n🟡 Testing Telegraph...")
    try:
        from uploaders.telegraph_uploader import TelegraphUploader
        uploader = TelegraphUploader()
        url = uploader.upload_image(str(test_image))
        if url:
            print(f"✅ Telegraph SUCCESS: {url}")
            return url
        else:
            print("❌ Telegraph failed")
    except Exception as e:
        print(f"❌ Telegraph error: {e}")
    
    # Test 3: PostImage (new alternative)
    print("\n🟢 Testing PostImage.org...")
    try:
        from uploaders.postimage_uploader import PostImageUploader
        uploader = PostImageUploader()
        url = uploader.upload_image(str(test_image))
        if url:
            print(f"✅ PostImage SUCCESS: {url}")
            return url
        else:
            print("❌ PostImage failed")
    except Exception as e:
        print(f"❌ PostImage error: {e}")
    
    print("\n❌ All providers failed")
    return None

if __name__ == "__main__":
    print("="*60)
    print("Testing All Image Upload Providers")
    print("="*60)
    
    # First check environment
    check_environment()
    
    working_url = test_all_providers()
    
    if working_url:
        print(f"\n🎉 SUCCESS! Working image URL: {working_url}")
        print("\nYour upload system is working!")
    else:
        print("\n💡 SOLUTIONS:")
        print("1. Check .env file format (see below)")
        print("2. Try different network (mobile hotspot)")
        print("3. Check firewall/proxy settings")
        print("4. Contact your IT department about HTTPS restrictions")
        print("\n📝 CORRECT .env FORMAT:")
        print("IMGBB_API_KEY=your_actual_api_key_here")
        print("(No spaces around = sign, no quotes needed)")