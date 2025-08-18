import os
import logging
from pathlib import Path
from typing import Optional, List
from utils.text_cleaner import TextCleaner

# Optional imports for OCR functionality
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False
    
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRError(Exception):
    """Base exception for OCR operations"""
    pass

class TesseractNotFoundError(OCRError):
    """Tesseract executable not found"""
    pass

class ImageProcessingError(OCRError):
    """Image processing related errors"""
    pass

def find_tesseract_path() -> Optional[str]:
    """Automatically find Tesseract installation path
    
    Returns:
        Tesseract executable path if found, None otherwise
    """
    # Check environment variable first
    env_path = os.getenv('TESSERACT_PATH')
    if env_path:
        path_obj = Path(env_path)
        if path_obj.exists() and path_obj.is_file():
            return str(path_obj)
        else:
            logger.warning(f"TESSERACT_PATH points to non-existent file: {env_path}")
    
    # Common installation paths by platform
    if os.name == 'nt':  # Windows
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe'
        ]
    else:  # Unix-like systems
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',  # macOS with Homebrew
            '/data/data/com.termux/files/usr/bin/tesseract'  # Termux
        ]
    
    for path_str in possible_paths:
        path_obj = Path(path_str)
        if path_obj.exists() and path_obj.is_file():
            return str(path_obj)
            
    return None

def setup_tesseract() -> None:
    """Setup Tesseract path and validate installation
    
    Raises:
        TesseractNotFoundError: If Tesseract cannot be found or configured
    """
    if not PYTESSERACT_AVAILABLE:
        raise TesseractNotFoundError("pytesseract is not installed")
        
    try:
        tesseract_path = find_tesseract_path()
        if not tesseract_path:
            raise TesseractNotFoundError(
                "Tesseract-OCR not found. Please install Tesseract or set TESSERACT_PATH environment variable"
            )
            
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Validate Tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract found at {tesseract_path}, version: {version}")
        except Exception as e:
            raise TesseractNotFoundError(f"Tesseract installation invalid: {e}")
            
    except TesseractNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error setting up Tesseract: {e}")
        raise TesseractNotFoundError(f"Tesseract setup failed: {e}")

def _validate_image_file(image_path: str) -> Path:
    """Validate image file path and format
    
    Args:
        image_path: Path to image file
        
    Returns:
        Validated Path object
        
    Raises:
        ImageProcessingError: If image is invalid or inaccessible
    """
    path = Path(image_path)
    
    if not path.exists():
        raise ImageProcessingError(f"Image file not found: {image_path}")
        
    if not path.is_file():
        raise ImageProcessingError(f"Path is not a file: {image_path}")
    
    # Security check: resolve path to prevent directory traversal
    try:
        resolved_path = path.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise ImageProcessingError(f"Invalid file path: {e}")
    
    # Validate image format if PIL is available
    if PIL_AVAILABLE:
        try:
            with Image.open(resolved_path) as img:
                img.verify()
        except Exception as e:
            raise ImageProcessingError(f"Invalid image file: {e}")
    else:
        # Basic file extension check if PIL not available
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        if resolved_path.suffix.lower() not in allowed_extensions:
            raise ImageProcessingError(f"Unsupported image format: {resolved_path.suffix}")
        
    return resolved_path

def extract_text(image_path: str, lang: str = "eng", config: str = "") -> str:
    """Extract text from image using OCR
    
    Args:
        image_path: Path to image file
        lang: OCR language (default: "eng")
        config: Additional Tesseract configuration
        
    Returns:
        Extracted text content
        
    Raises:
        TesseractNotFoundError: If Tesseract is not available
        ImageProcessingError: If image processing fails
        OCRError: If OCR operation fails
    """
    if not PIL_AVAILABLE:
        raise ImageProcessingError("PIL (Pillow) is required for image processing but not installed")
        
    try:
        # Validate inputs
        if not image_path or not isinstance(image_path, str):
            raise ImageProcessingError("Invalid image path provided")
            
        if not lang or not isinstance(lang, str):
            raise OCRError("Invalid language parameter")
        
        # Setup Tesseract
        setup_tesseract()
        
        # Validate image file
        validated_path = _validate_image_file(image_path)
        
        # Extract text
        with Image.open(validated_path) as image:
            # Apply basic image preprocessing if needed
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
                
            text = pytesseract.image_to_string(
                image, 
                lang=lang, 
                config=config or '--psm 6'
            )
        
        # Clean and validate extracted text
        raw_text = text.strip()
        
        if not raw_text:
            logger.warning(f"No text extracted from image: {image_path}")
            return ""
        
        # 使用TextCleaner清理OCR輸出
        logger.info(f"Raw OCR output length: {len(raw_text)} characters")
        
        cleaner = TextCleaner()
        cleaned_text = cleaner.clean_ocr_text(raw_text)
        
        # 獲取清理統計
        stats = cleaner.get_cleaning_stats(raw_text, cleaned_text)
        logger.info(f"Text cleaning completed: {stats['cleaned_length']} chars ({stats['reduction_ratio']:.1%} reduction)")
        logger.info(f"Found {stats['english_words_found']} English words in {stats['cleaned_lines']} clean lines")
        
        if not cleaned_text:
            logger.warning(f"No valid text found after cleaning from image: {image_path}")
            return ""
            
        return cleaned_text
        
    except (TesseractNotFoundError, ImageProcessingError):
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise OCRError(f"OCR processing failed: {e}")

def get_available_languages() -> List[str]:
    """Get list of available OCR languages
    
    Returns:
        List of available language codes
        
    Raises:
        TesseractNotFoundError: If Tesseract is not available
        OCRError: If language detection fails
    """
    if not PYTESSERACT_AVAILABLE:
        raise TesseractNotFoundError("pytesseract is not installed")
        
    try:
        setup_tesseract()
        languages = pytesseract.get_languages()
        logger.info(f"Available languages: {languages}")
        return languages
    except TesseractNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get available languages: {e}")
        raise OCRError(f"Language detection failed: {e}")

def validate_ocr_config() -> bool:
    """Validate OCR configuration and dependencies
    
    Returns:
        True if OCR is properly configured
        
    Raises:
        TesseractNotFoundError: If Tesseract is not available
    """
    try:
        setup_tesseract()
        languages = get_available_languages()
        
        if 'eng' not in languages:
            logger.warning("English language pack not available")
            
        logger.info("OCR configuration validated successfully")
        return True
        
    except Exception as e:
        logger.error(f"OCR configuration validation failed: {e}")
        raise 