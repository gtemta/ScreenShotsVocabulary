from typing import Dict, List
import json

class BaseModel:
    """基礎模型類"""
    
    def process_text(self, text: str) -> Dict[str, List[str]]:
        """
        處理文本並提取詞彙
        
        Args:
            text (str): 要處理的文本
            
        Returns:
            Dict[str, List[str]]: 包含詞彙和相關資訊的字典
        """
        raise NotImplementedError("子類必須實現此方法")
    
    def get_model_name(self) -> str:
        """獲取模型名稱"""
        raise NotImplementedError("子類必須實現此方法")
    
    def get_model_version(self) -> str:
        """獲取模型版本"""
        raise NotImplementedError("子類必須實現此方法")
    
    def _parse_response(self, response: Dict) -> Dict:
        """
        解析模型回應，轉換為標準格式
        
        Args:
            response (Dict): 模型原始回應
            
        Returns:
            Dict: 標準化的詞彙資訊
        """
        try:
            # 檢查必要欄位
            if "phrases" not in response:
                raise ValueError("回應中缺少 'phrases' 欄位")
                
            # 轉換為標準格式
            return {
                "phrases": [
                    {
                        "vocabulary": item["vocabulary"],
                        "chinese_word": item["chinese_word"],
                        "definition": item["definition"],
                        "chinese_definition": item["chinese_definition"],
                        "examples": item["examples"],
                        "synonyms": item["synonyms"],
                        "antonyms": item["antonyms"]
                    }
                    for item in response["phrases"]
                ]
            }
            
        except KeyError as e:
            raise ValueError(f"回應格式錯誤，缺少必要欄位: {str(e)}")
        except Exception as e:
            raise ValueError(f"解析回應時發生錯誤: {str(e)}") 