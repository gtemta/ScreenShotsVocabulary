import requests
import json
import os
from notion_client import Client
from uploaders.imgur_uploader import ImgurUploader
import time

class NotionUploader:
    def __init__(self, api_key, database_id):
        """
        初始化 Notion 上傳器
        
        Args:
            api_key (str): Notion API 密鑰
            database_id (str): Notion 數據庫 ID
        """
        self.api_key = api_key
        self.database_id = database_id
        self.notion = Client(auth=api_key)
        self.timeout = 30  # 設置默認超時時間為 30 秒
        self.imgur = ImgurUploader()
        
    def upload_word_info(self, word, word_info, image_url=None):
        """
        上傳單字信息到 Notion
        
        Args:
            word (str): 單字
            word_info (dict): 單字信息字典
            image_url (str, optional): 圖片 URL
        """
        # 創建標題（英文單字 : 中文意思）
        title = f"{word} : {word_info['chinese_word']}"
        
        # 創建 Notion 頁面
        notion_data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "KeyWord": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }
        
        try:
            # 打印請求數據以便調試
            print("\n發送到 Notion 的數據:")
            print(json.dumps(notion_data, indent=2, ensure_ascii=False))
            
            # 發送請求到 Notion API
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28"
                },
                json=notion_data,
                timeout=self.timeout
            )
            
            # 打印完整的響應內容以便調試
            print("\nNotion API 響應:")
            print(response.text)
            
            if response.status_code == 200:
                notion_page_id = response.json().get("id")
                if notion_page_id:
                    print("✅ 成功創建 Notion 頁面")
                    # 添加內容和圖片
                    self.add_markdown_content(notion_page_id, word_info, image_url)
            else:
                print(f"❌ 上傳失敗 (狀態碼: {response.status_code})")
                
        except Exception as e:
            print(f"❌ 上傳過程發生錯誤: {str(e)}")
    
    def add_markdown_content(self, page_id, word_info, image_url=None):
        """
        添加內容塊到頁面
        
        Args:
            page_id (str): Notion 頁面 ID
            word_info (dict): 單字信息字典
            image_url (str, optional): 圖片 URL
        """
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                # 直接創建所需的塊結構
                children = [
                    # 標題塊
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": f"**{word_info['word']} ({word_info['chinese_word']})**"
                                }
                            }]
                        }
                    }
                ]

                # 如果有圖片 URL，驗證並添加圖片塊
                if image_url:
                    if self.imgur.verify_image_url(image_url):
                        children.append({
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "external",
                                "external": {
                                    "url": image_url
                                }
                            }
                        })
                        print(f"✅ 圖片 URL 驗證成功: {image_url}")
                    else:
                        print(f"⚠️ 圖片 URL 無效，跳過添加圖片: {image_url}")

                # 添加其他內容塊
                children.extend([
                    # 定義塊
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": "📖 定義 (Definition)"
                                }
                            }]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": word_info['definition']
                                }
                            }]
                        }
                    },
                    # 中文解釋塊
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": "📝 中文解釋 (Chinese Explanation)"
                                }
                            }]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": word_info['chinese_definition']
                                }
                            }]
                        }
                    },
                    # 例句塊
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": "💡 例句 (Example Sentence)"
                                }
                            }]
                        }
                    }
                ])

                # 添加所有例句
                for example in word_info['examples']:
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": example
                                }
                            }]
                        }
                    })

                # 添加同義詞和反義詞
                children.extend([
                    # 同義詞塊
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": "🔗 近義詞 (Synonyms)"
                                }
                            }]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": ", ".join(word_info['synonyms']) if word_info['synonyms'] else "無"
                                }
                            }]
                        }
                    },
                    # 反義詞塊
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": "🚫 反義詞 (Antonyms)"
                                }
                            }]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": ", ".join(word_info['antonyms']) if word_info['antonyms'] else "無"
                                }
                            }]
                        }
                    }
                ])
                
                # 使用 Notion API 添加內容
                response = requests.patch(
                    f"https://api.notion.com/v1/blocks/{page_id}/children",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Notion-Version": "2022-06-28"
                    },
                    json={
                        "children": children
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    print("✅ 成功添加詳細內容到頁面")
                    return True
                elif response.status_code == 409 and attempt < max_retries - 1:
                    print(f"⚠️ 發生衝突，正在重試 ({attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"❌ 添加詳細內容失敗: {response.text}")
                    return False
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 發生錯誤，正在重試 ({attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"❌ 添加詳細內容失敗: {str(e)}")
                    return False 