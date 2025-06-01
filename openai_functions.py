import os
import json
from typing import List, Dict, Optional
import openai
from dotenv import load_dotenv

# 載入環境變量
load_dotenv()

# 設置 OpenAI API 密鑰
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_learning_phrases_with_gpt(text: str) -> List[Dict[str, str]]:
    """
    使用 OpenAI GPT 從文本中提取適合學習的英文單字和片語
    
    Args:
        text (str): 輸入的英文文本
        
    Returns:
        List[Dict[str, str]]: 包含提取的單字/片語及其解釋的列表
    """
    try:
        # 構建提示詞
        prompt = f"""請從以下文本中提取 3-5 個最適合學習的英文單字或片語。
        對於每個提取的項目，請提供：
        1. 單字/片語本身
        2. 中文翻譯
        3. 簡短的英文解釋
        4. 使用場景或例句
        
        文本內容：
        {text}
        
        請以 JSON 格式返回，格式如下：
        {{
            "phrases": [
                {{
                    "phrase": "單字或片語",
                    "translation": "中文翻譯",
                    "explanation": "英文解釋",
                    "example": "使用場景或例句"
                }}
            ]
        }}
        """
        
        # 調用 OpenAI API（新版本）
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一個專業的英語教學助手，擅長從文本中提取重要的學習內容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # 解析回應（新版本）
        result = json.loads(response.choices[0].message.content)
        return result.get("phrases", [])
        
    except Exception as e:
        print(f"⚠️ 提取學習內容時發生錯誤: {str(e)}")
        return []

def get_learning_content(text: str) -> Optional[Dict[str, List[Dict[str, str]]]]:
    """
    整合 GPT 提取的學習內容，並進行後處理
    
    Args:
        text (str): 輸入的英文文本
        
    Returns:
        Optional[Dict[str, List[Dict[str, str]]]]: 處理後的學習內容
    """
    try:
        # 使用 GPT 提取學習內容
        phrases = extract_learning_phrases_with_gpt(text)
        
        if not phrases:
            return None
            
        # 對每個提取的內容進行額外處理
        processed_content = {
            "vocabulary": [],
            "phrases": []
        }
        
        for item in phrases:
            # 檢查是否為單字（不包含空格）
            if " " not in item["phrase"]:
                processed_content["vocabulary"].append(item)
            else:
                processed_content["phrases"].append(item)
        
        return processed_content
        
    except Exception as e:
        print(f"⚠️ 處理學習內容時發生錯誤: {str(e)}")
        return None 