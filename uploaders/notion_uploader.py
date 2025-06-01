import os
from typing import List, Optional
from notion_client import Client
from notion_client.helpers import get_id

class NotionUploader:
    """Notion 上傳器"""
    
    def __init__(self):
        self.api_key = os.getenv('NOTION_API_KEY')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.client = Client(auth=self.api_key)
    
    async def upload(
        self,
        word: str,
        image_url: str,
        chinese_word: str,
        definition: str,
        chinese_definition: str,
        examples: List[str],
        synonyms: List[str],
        antonyms: List[str]
    ) -> bool:
        """
        上傳詞彙到 Notion
        
        Args:
            word (str): 英文單字或片語
            image_url (str): 圖片 URL
            chinese_word (str): 中文翻譯
            definition (str): 英文定義
            chinese_definition (str): 中文定義
            examples (List[str]): 例句列表
            synonyms (List[str]): 同義詞列表
            antonyms (List[str]): 反義詞列表
            
        Returns:
            bool: 是否上傳成功
        """
        try:
            # 創建新頁面
            new_page = {
                "parent": {"database_id": get_id(self.database_id)},
                "properties": {
                    "Word": {
                        "title": [
                            {
                                "text": {
                                    "content": word
                                }
                            }
                        ]
                    },
                    "Chinese": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": chinese_word
                                }
                            }
                        ]
                    },
                    "Definition": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": definition
                                }
                            }
                        ]
                    },
                    "Chinese Definition": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": chinese_definition
                                }
                            }
                        ]
                    }
                },
                "children": [
                    {
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {
                                "url": image_url
                            }
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": "Examples"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            
            # 添加例句
            for example in examples:
                new_page["children"].append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": example
                                }
                            }
                        ]
                    }
                })
            
            # 添加同義詞
            if synonyms:
                new_page["children"].extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": "Synonyms"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": ", ".join(synonyms)
                                    }
                                }
                            ]
                        }
                    }
                ])
            
            # 添加反義詞
            if antonyms:
                new_page["children"].extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": "Antonyms"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": ", ".join(antonyms)
                                    }
                                }
                            ]
                        }
                    }
                ])
            
            # 創建頁面
            self.client.pages.create(**new_page)
            return True
            
        except Exception as e:
            print(f"Notion 上傳錯誤: {str(e)}")
            return False 