import requests
from typing import Dict, List
from .base_model import BaseModel
import json
from utils.prompt_utils import build_prompt

class Phi3Processor(BaseModel):
    """Phi-3 模型處理器"""
    
    def __init__(self):
        self.model_name = "phi3"
        self.version = "1.0.0"
        self.api_url = "http://localhost:11434/api/generate"
        
    def process_text(self, text: str) -> Dict[str, List[str]]:
        """
        使用 Phi-3 模型處理文本
        
        Args:
            text (str): 要處理的文本
            
        Returns:
            Dict[str, List[str]]: 包含詞彙和相關資訊的字典
        """
        try:
            # 使用統一的提示詞
            prompt = build_prompt(text)
            
            # 調用本地 API
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                # 解析 JSON 回應
                result = json.loads(response.json()["response"])
                # 使用基類的解析方法
                return self._parse_response(result)
            else:
                print(f"Phi-3 API 錯誤: {response.status_code}")
                return {
                    "vocabulary": [],
                    "chinese_words": [],
                    "definitions": [],
                    "chinese_definitions": [],
                    "examples": [],
                    "synonyms": [],
                    "antonyms": []
                }
            
        except Exception as e:
            print(f"Phi-3 處理錯誤: {str(e)}")
            return {
                "vocabulary": [],
                "chinese_words": [],
                "definitions": [],
                "chinese_definitions": [],
                "examples": [],
                "synonyms": [],
                "antonyms": []
            }
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def get_model_version(self) -> str:
        return self.version 