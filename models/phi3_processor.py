import requests
from typing import Dict, List
from models.base_model import BaseModel
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
                },
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if "response" not in response_data:
                        print(f"Phi-3 API 返回格式錯誤: 缺少 'response' 字段")
                        return self._get_empty_result()
                        
                    # 處理被 Markdown 代碼塊包裹的 JSON
                    response_text = response_data["response"]
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]  # 移除 ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # 移除結尾的 ```
                    response_text = response_text.strip()
                    
                    result = json.loads(response_text)
                    
                    # 驗證必要欄位
                    if "phrases" not in result:
                        print(f"Phi-3 API 返回格式錯誤: 缺少 'phrases' 字段")
                        print(f"API 返回內容: {response_text}")
                        return self._get_empty_result()
                        
                    # 驗證每個詞彙的必要欄位
                    required_fields = ["vocabulary", "chinese_word", "definition", 
                                     "chinese_definition", "examples", "synonyms", "antonyms"]
                    for i, phrase in enumerate(result["phrases"]):
                        missing_fields = [field for field in required_fields if field not in phrase]
                        if missing_fields:
                            print(f"Phi-3 API 返回格式錯誤: 詞彙 {i+1} 缺少必要欄位: {', '.join(missing_fields)}")
                            print(f"詞彙內容: {json.dumps(phrase, ensure_ascii=False, indent=2)}")
                            return self._get_empty_result()
                    
                    return self._parse_response(result)
                except json.JSONDecodeError as e:
                    print(f"Phi-3 API 返回格式錯誤: {str(e)}")
                    print(f"API 返回內容: {response.text}")
                    return self._get_empty_result()
            else:
                print(f"Phi-3 API 錯誤: {response.status_code}")
                print(f"API 返回內容: {response.text}")
                return self._get_empty_result()
            
        except Exception as e:
            print(f"Phi-3 處理錯誤: {str(e)}")
            return self._get_empty_result()
    
    def _get_empty_result(self) -> Dict[str, List[str]]:
        """返回空結果"""
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