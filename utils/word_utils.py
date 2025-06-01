import json
from typing import List
import logging

# 設定日誌
logger = logging.getLogger(__name__)

def load_learned_words() -> List[str]:
    """
    從 processed_words.json 讀取已學習的單字列表
    
    Returns:
        List[str]: 已學習的單字列表
    """
    try:
        with open('processed_words.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("找不到 processed_words.json 檔案，將使用空列表")
        return []
    except json.JSONDecodeError:
        logger.error("processed_words.json 格式錯誤，將使用空列表")
        return []

def save_learned_words(words: List[str]) -> None:
    """
    將學習過的單字保存到 processed_words.json
    
    Args:
        words (List[str]): 要保存的單字列表
    """
    try:
        # 讀取現有的單字列表
        existing_words = load_learned_words()
        
        # 合併並去重
        all_words = list(set(existing_words + words))
        
        # 保存到檔案
        with open('processed_words.json', 'w', encoding='utf-8') as f:
            json.dump(all_words, f, ensure_ascii=False, indent=2)
            
        logger.info(f"已保存 {len(all_words)} 個單字到 processed_words.json")
    except Exception as e:
        logger.error(f"保存單字時發生錯誤: {str(e)}") 