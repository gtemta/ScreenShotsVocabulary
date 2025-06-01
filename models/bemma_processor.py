import os
from typing import Dict, List
from .base_model import BaseModel
import openai
import json
from utils.prompt_utils import build_prompt

class BEMMAProcessor(BaseModel):
    """BEMMA 模型處理器"""
    
    def __init__(self):
        self.api_key = os.getenv('BEMMA_API_KEY')
        self.model_name = "bemma-7b"
        self.version = "1.0.0"
        
    def process_text(self, text: str) -> Dict[str, List[str]]:
        """
        使用 BEMMA 模型處理文本
        
        Args:
            text (str): 要處理的文本
            
        Returns:
            Dict[str, List[str]]: 包含詞彙和相關資訊的字典
        """
        try:
            # 使用統一的提示詞
            prompt = build_prompt(text)
            
            # 調用 API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一個專業的英文詞彙分析師，請從文本中提取重要的英文詞彙。"},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 解析 JSON 回應
            result = json.loads(response.choices[0].message.content)
            
            # 轉換為標準格式
            return {
                "vocabulary": [item["phrase"] for item in result["phrases"]],
                "definitions": [item["explanation"] for item in result["phrases"]],
                "examples": [item["example"] for item in result["phrases"]],
                "translations": [item["translation"] for item in result["phrases"]]
            }
            
        except Exception as e:
            print(f"BEMMA 處理錯誤: {str(e)}")
            return {"vocabulary": [], "definitions": [], "examples": [], "translations": []}
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def get_model_version(self) -> str:
        return self.version 