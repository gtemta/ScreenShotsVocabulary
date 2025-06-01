import os
import sys
import pytesseract
from PIL import Image
from typing import Optional
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_tesseract_path() -> Optional[str]:
    """
    自動尋找 Tesseract 安裝路徑
    
    Returns:
        Optional[str]: Tesseract 執行檔路徑，如果找不到則返回 None
    """
    # 常見的 Windows 安裝路徑
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe'
    ]
    
    # 檢查環境變數
    if 'TESSERACT_PATH' in os.environ:
        tesseract_path = os.environ['TESSERACT_PATH']
        if os.path.exists(tesseract_path):
            return tesseract_path
    
    # 檢查可能的安裝路徑
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return None

def setup_tesseract() -> bool:
    """
    設定 Tesseract 路徑
    
    Returns:
        bool: 設定是否成功
    """
    try:
        tesseract_path = find_tesseract_path()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"已找到 Tesseract 路徑: {tesseract_path}")
            return True
        else:
            logger.error("找不到 Tesseract 安裝路徑，請確保已安裝 Tesseract-OCR")
            return False
    except Exception as e:
        logger.error(f"設定 Tesseract 路徑時發生錯誤: {str(e)}")
        return False

def extract_text(image_path: str, lang: str = "eng") -> Optional[str]:
    """
    從圖片中提取文字
    
    Args:
        image_path (str): 圖片檔案路徑
        lang (str): OCR 語言，預設為英文
        
    Returns:
        Optional[str]: 提取的文字內容，如果發生錯誤則返回 None
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(image_path):
            logger.error(f"找不到圖片檔案: {image_path}")
            return None
            
        # 檢查檔案是否為圖片
        try:
            image = Image.open(image_path)
            image.verify()  # 驗證圖片完整性
        except Exception as e:
            logger.error(f"圖片檔案無效: {str(e)}")
            return None
            
        # 重新開啟圖片（因為 verify 會關閉檔案）
        image = Image.open(image_path)
        
        # 確保 Tesseract 已設定
        if not setup_tesseract():
            return None
            
        # 執行 OCR
        text = pytesseract.image_to_string(image, lang=lang)
        
        # 清理文字
        text = text.strip()
        
        if not text:
            logger.warning("OCR 未能提取到任何文字")
            return None
            
        return text
        
    except Exception as e:
        logger.error(f"OCR 處理時發生錯誤: {str(e)}")
        return None

def get_available_languages() -> list:
    """
    獲取可用的 OCR 語言列表
    
    Returns:
        list: 可用的語言代碼列表
    """
    try:
        if not setup_tesseract():
            return []
        return pytesseract.get_languages()
    except Exception as e:
        logger.error(f"獲取可用語言時發生錯誤: {str(e)}")
        return [] 