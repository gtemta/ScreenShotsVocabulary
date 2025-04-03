import pytesseract
from PIL import Image

def extract_text(image_path):
    """
    从图片中提取文字
    
    Args:
        image_path (str): 图片文件路径
        
    Returns:
        str: 提取的文字内容
    """
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="eng")
    return text 