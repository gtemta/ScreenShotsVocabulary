def build_prompt(text: str) -> str:
    """
    構建用於提取詞彙的提示詞
    
    Args:
        text (str): 要處理的文本
        
    Returns:
        str: 格式化後的提示詞
    """
    return f"""You are an expert English language instructor helping intermediate to advanced learners.

Please extract at most 3 useful English words or phrases from the following text. For each word/phrase, provide:
1. The word/phrase itself
2. Chinese translation
3. English definition
4. Chinese definition
5. Example sentences (at least 2)
6. Synonyms (if any)
7. Antonyms (if any)

Only return the results in the following JSON format:
{{
  "phrases": [
    {{
      "vocabulary": "extracted word or phrase",
      "chinese_word": "中文翻譯",
      "definition": "English definition",
      "chinese_definition": "中文解釋",
      "examples": ["example sentence 1", "example sentence 2"],
      "synonyms": ["synonym 1", "synonym 2"],
      "antonyms": ["antonym 1", "antonym 2"]
    }},
    ...
  ]
}}

Text to analyze:
{text}""" 