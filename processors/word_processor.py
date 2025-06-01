from typing import Dict, List
from models.deepseek_processor import DeepSeekProcessor
from models.bemma_processor import BEMMAProcessor
from models.phi3_processor import Phi3Processor
from reviewers.chatgpt_reviewer import ChatGPTReviewer
import asyncio
import logging
import re

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WordProcessor:
    """主要的詞彙處理器，整合所有模型和審核器"""
    
    def __init__(self):
        self.models = {
            'deepseek': DeepSeekProcessor(),
            'bemma': BEMMAProcessor(),
            'phi3': Phi3Processor()
        }
        self.reviewer = ChatGPTReviewer()
        
    async def process_text(self, text: str) -> Dict[str, List[str]]:
        """
        處理文本並返回最終的詞彙列表
        
        Args:
            text (str): 要處理的文本
            
        Returns:
            Dict[str, List[str]]: 最終的詞彙列表
        """
        try:
            # 並行處理所有模型
            tasks = []
            for model_name, model in self.models.items():
                tasks.append(self._process_with_model(model_name, model, text))
            
            # 等待所有模型處理完成
            results = await asyncio.gather(*tasks)
            
            # 整合結果
            vocab_lists = {}
            for model_name, result in zip(self.models.keys(), results):
                vocab_lists[model_name] = result
            
            # 審核結果
            final_vocabulary = self.reviewer.review_vocabulary(vocab_lists)
            
            return final_vocabulary
            
        except Exception as e:
            logger.error(f"詞彙處理錯誤: {str(e)}")
            return {"vocabulary": [], "definitions": [], "examples": []}
    
    async def _process_with_model(self, model_name: str, model: object, text: str) -> Dict[str, List[str]]:
        """
        使用特定模型處理文本
        
        Args:
            model_name (str): 模型名稱
            model (object): 模型實例
            text (str): 要處理的文本
            
        Returns:
            Dict[str, List[str]]: 處理結果
        """
        try:
            logger.info(f"開始使用 {model_name} 處理文本")
            result = await asyncio.to_thread(model.process_text, text)
            logger.info(f"{model_name} 處理完成")
            return result
        except Exception as e:
            logger.error(f"{model_name} 處理錯誤: {str(e)}")
            return {"vocabulary": [], "definitions": [], "examples": []}

def is_valid_english_word(word):
    """
    检查单词是否只包含英文字母，并过滤特殊格式
    
    Args:
        word (str): 要检查的单词
        
    Returns:
        bool: 如果是有效的英文字母则返回 True
    """
    # 过滤掉包含版本号格式的文本（如 V0.92350）
    if re.match(r'^[vV]\d+\.?\d*', word):
        return False
        
    # 过滤掉包含数字的文本
    if re.search(r'\d', word):
        return False
        
    # 过滤掉包含特殊字符的文本
    if re.search(r'[^a-zA-Z]', word):
        return False
        
    # 过滤掉太短的单词
    if len(word) < 2:
        return False
        
    # 过滤掉全大写的单词（通常是缩写）
    if word.isupper():
        return False
        
    # 过滤掉包含连续相同字母的单词（如 "hellooo"）
    if re.search(r'(.)\1{2,}', word):
        return False
        
    return True

def is_valid_english_sentence(text: str) -> bool:
    """
    判斷是否為有效的英文句子
    
    Args:
        text (str): 要檢查的文字
        
    Returns:
        bool: 如果是有效的英文句子則返回 True
    """
    # 移除空白
    text = text.strip()
    
    # 檢查是否為空
    if not text:
        return False
        
    # 檢查是否包含句號、問號或驚嘆號
    if not any(text.endswith(p) for p in ['.', '?', '!']):
        return False
        
    # 檢查是否至少包含一個空格（表示多個單字）
    if ' ' not in text:
        return False
        
    # 檢查句子中的每個單字
    words = text.split()
    valid_words = [word for word in words if is_valid_english_word(word)]
    
    # 如果有效單字數量太少，則認為不是有效句子
    if len(valid_words) < 2:
        return False
        
    return True