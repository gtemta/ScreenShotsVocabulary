from googletrans import Translator

def translate_to_chinese(text):
    """
    将文本翻译成中文
    
    Args:
        text (str): 要翻译的英文文本
        
    Returns:
        str: 翻译后的中文文本
    """
    translator = Translator()
    result = translator.translate(text, src="en", dest="zh-tw")
    return result.text 