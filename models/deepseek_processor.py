import requests
from typing import Dict, List
from .base_model import BaseModel
import json
from utils.prompt_utils import build_prompt

class DeepSeekProcessor(BaseModel):
    """DeepSeek 模型處理器"""
    
    def __init__(self):
        self.model_name = "deepseek-llm"
        self.version = "1.0.0"
        self.api_url = "http://localhost:11434/api/generate"
        
    def process_text(self, text: str) -> Dict[str, List[str]]:
        """
        使用 DeepSeek 模型處理文本
        
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
                timeout=30  # 添加30秒超时
            )
            
            if response.status_code == 200:
                try:
                    # 获取原始响应
                    raw_response = response.json()
                    
                    # 检查响应格式
                    if "response" not in raw_response:
                        print("❌ API 响应中没有 'response' 字段")
                        return self._get_empty_result()
                    
                    # 尝试直接使用 response 字段
                    try:
                        result = raw_response["response"]
                        if isinstance(result, str):
                            # 如果 response 是字符串，尝试解析为 JSON
                            try:
                                result = json.loads(result)
                            except json.JSONDecodeError:
                                # 如果不是 JSON 格式，直接使用字符串
                                result = {"text": result}
                        return self._parse_response(result)
                    except Exception as e:
                        print(f"❌ 处理响应内容时出错: {str(e)}")
                        return self._get_empty_result()
                        
                except Exception as e:
                    print(f"❌ 处理 API 响应时出错: {str(e)}")
                    return self._get_empty_result()
            else:
                print(f"❌ DeepSeek API 錯誤 (狀態碼: {response.status_code}): {response.text}")
                return self._get_empty_result()
            
        except Exception as e:
            print(f"❌ DeepSeek 處理錯誤: {str(e)}")
            return self._get_empty_result()
    
    def _get_empty_result(self) -> Dict[str, List[str]]:
        """返回空结果字典"""
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