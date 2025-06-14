# -*- coding: utf-8 -*-
import sys
import os
import json
from typing import Dict, List

# 添加父目錄到系統路徑，以便導入其他模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.deepseek_processor import DeepSeekProcessor
from models.gemma_processor import GemmaProcessor
from models.phi3_processor import Phi3Processor

def test_model(processor, text: str, model_name: str) -> None:
    """
    測試單個模型的處理結果
    
    Args:
        processor: 模型處理器實例
        text (str): 測試文本
        model_name (str): 模型名稱
    """
    print(f"\n{'='*50}")
    print(f"測試 {model_name} 模型")
    print(f"{'='*50}")
    
    try:
        result = processor.process_text(text)
        print("\n處理結果：")
        
        # 檢查結果是否為空
        if not result or not result.get("phrases"):
            print("[ERROR] 沒有提取到任何詞彙")
            return
            
        # 檢查所有必要的欄位是否存在
        required_fields = ["vocabulary", "chinese_word", "definition", 
                         "chinese_definition", "examples", "synonyms", "antonyms"]
        
        # 格式化輸出每個詞彙的詳細資訊
        for i, phrase in enumerate(result["phrases"], 1):
            # 檢查必要欄位
            missing_fields = [field for field in required_fields if field not in phrase]
            if missing_fields:
                print(f"[ERROR] 詞彙 {i} 缺少必要的欄位: {', '.join(missing_fields)}")
                continue
                
            print(f"\n詞彙 {i}:")
            print(f"單字/片語: {phrase['vocabulary']}")
            print(f"中文翻譯: {phrase['chinese_word']}")
            print(f"英文定義: {phrase['definition']}")
            print(f"中文定義: {phrase['chinese_definition']}")
            print("\n例句:")
            for example in phrase['examples']:
                print(f"- {example}")
            if phrase['synonyms']:
                print(f"\n同義詞: {', '.join(phrase['synonyms'])}")
            if phrase['antonyms']:
                print(f"\n反義詞: {', '.join(phrase['antonyms'])}")
            print("-" * 30)
            
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析錯誤: {str(e)}")
        print("請檢查模型返回的 JSON 格式是否正確")
        print("預期的格式：")
        print("""
{
  "phrases": [
    {
      "vocabulary": "extracted word or phrase",
      "chinese_word": "中文翻譯",
      "definition": "English definition",
      "chinese_definition": "中文解釋",
      "examples": ["example sentence 1", "example sentence 2"],
      "synonyms": ["synonym 1", "synonym 2"],
      "antonyms": ["antonym 1", "antonym 2"]
    }
  ]
}
        """)
    except Exception as e:
        print(f"[ERROR] 測試失敗: {str(e)}")
        print("錯誤類型:", type(e).__name__)

def main():
    # 測試文本
    test_text = """
    Artificial Intelligence (AI) is transforming the way we live and work. 
    Machine learning algorithms can now process vast amounts of data to make predictions and decisions. 
    Deep learning, a subset of machine learning, uses neural networks to learn from examples.
    """
    
    # 初始化所有處理器
    processors = {
        "Gemma": GemmaProcessor(),
        "DeepSeek": DeepSeekProcessor(),
        "Phi-3": Phi3Processor()
    }
    
    # 測試每個模型
    for model_name, processor in processors.items():
        test_model(processor, test_text, model_name)

if __name__ == "__main__":
    main() 