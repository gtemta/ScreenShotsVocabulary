import os
import logging
from typing import List, Optional
from notion_client import Client
from notion_client.helpers import get_id
from notion_client.errors import RequestTimeoutError, APIResponseError

class UploadError(Exception):
    """Base exception for upload operations"""
    pass

class NotionUploadError(UploadError):
    """Exception for Notion upload failures"""
    pass

class NotionConfigurationError(UploadError):
    """Exception for Notion configuration issues"""
    pass

class NotionUploader:
    """Notion 上傳器"""
    
    def __init__(self):
        self.api_key = os.getenv('NOTION_API_KEY')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.client = Client(auth=self.api_key)
        self.logger = logging.getLogger(__name__)
    
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
            # Validate input data
            self._validate_upload_data(
                word=word, 
                image_url=image_url,
                chinese_word=chinese_word,
                definition=definition,
                chinese_definition=chinese_definition
            )
            
            # Set defaults for optional parameters
            examples = examples or []
            synonyms = synonyms or []
            antonyms = antonyms or []
            
            # Create page structure
            page_data = self._create_page_structure(
                word=word,
                chinese_word=chinese_word,
                definition=definition,
                chinese_definition=chinese_definition
            )
            
            # Add content blocks
            self._add_image_block(page_data, image_url)
            self._add_examples_section(page_data, examples)
            self._add_word_lists(page_data, synonyms, antonyms)
            
            # Create page with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = self.client.pages.create(**page_data)
                    page_id = result.get('id')
                    self.logger.info(f"Successfully uploaded vocabulary '{word}' to Notion (page: {page_id})")
                    return True
                    
                except RequestTimeoutError:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Notion request timeout, retrying ({attempt + 1}/{max_retries})")
                        continue
                    else:
                        raise NotionUploadError("Upload failed due to repeated timeouts")
                        
                except APIResponseError as e:
                    if e.code == 'invalid_request_url':
                        raise NotionConfigurationError(f"Invalid database ID: {self.database_id}")
                    elif e.code == 'unauthorized':
                        raise NotionConfigurationError("Invalid API key or insufficient permissions")
                    elif e.code == 'validation_error':
                        raise NotionUploadError(f"Data validation failed: {str(e)}")
                    else:
                        raise NotionUploadError(f"Notion API error: {str(e)}")
                        
            return False
            
        except (NotionUploadError, NotionConfigurationError):
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during Notion upload: {e}")
            raise NotionUploadError(f"Unexpected upload error: {e}")
    
    def test_connection(self) -> bool:
        """Test Notion connection and database access
        
        Returns:
            True if connection is successful
            
        Raises:
            NotionConfigurationError: If connection fails
        """
        try:
            self._validate_database_access()
            return True
        except Exception as e:
            self.logger.error(f"Notion connection test failed: {e}")
            raise NotionConfigurationError(f"Connection test failed: {e}")
    
    def _validate_upload_data(self, word: str, image_url: str, chinese_word: str, 
                             definition: str, chinese_definition: str) -> None:
        """Validate required upload data"""
        if not word or not word.strip():
            raise NotionUploadError("Word is required")
        if not image_url or not image_url.strip():
            raise NotionUploadError("Image URL is required")
        if not chinese_word or not chinese_word.strip():
            raise NotionUploadError("Chinese translation is required")
        if not definition or not definition.strip():
            raise NotionUploadError("Definition is required")
        if not chinese_definition or not chinese_definition.strip():
            raise NotionUploadError("Chinese definition is required")
    
    def _create_page_structure(self, word: str, chinese_word: str, 
                              definition: str, chinese_definition: str) -> dict:
        """Create basic page structure for Notion"""
        return {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": word}}]
                },
                "Chinese": {
                    "rich_text": [{"text": {"content": chinese_word}}]
                },
                "Definition": {
                    "rich_text": [{"text": {"content": definition}}]
                },
                "Chinese Definition": {
                    "rich_text": [{"text": {"content": chinese_definition}}]
                }
            },
            "children": []
        }
    
    def _add_image_block(self, page_data: dict, image_url: str) -> None:
        """Add image block to page"""
        if image_url:
            page_data["children"].append({
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": image_url}
                }
            })
    
    def _add_examples_section(self, page_data: dict, examples: List[str]) -> None:
        """Add examples section to page"""
        if examples:
            page_data["children"].append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Examples"}}]
                }
            })
            for example in examples:
                page_data["children"].append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": example}}]
                    }
                })
    
    def _add_word_lists(self, page_data: dict, synonyms: List[str], antonyms: List[str]) -> None:
        """Add synonyms and antonyms sections to page"""
        if synonyms:
            page_data["children"].append({
                "object": "block",
                "type": "heading_2", 
                "heading_2": {
                    "rich_text": [{"text": {"content": "Synonyms"}}]
                }
            })
            page_data["children"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": ", ".join(synonyms)}}]
                }
            })
        
        if antonyms:
            page_data["children"].append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Antonyms"}}]
                }
            })
            page_data["children"].append({
                "object": "block",
                "type": "paragraph", 
                "paragraph": {
                    "rich_text": [{"text": {"content": ", ".join(antonyms)}}]
                }
            })
    
    def _validate_database_access(self) -> None:
        """Validate database access"""
        try:
            self.client.databases.retrieve(self.database_id)
        except APIResponseError as e:
            if e.code == 'unauthorized':
                raise NotionConfigurationError("Invalid API key or insufficient permissions")
            elif e.code == 'object_not_found':
                raise NotionConfigurationError(f"Database not found: {self.database_id}")
            else:
                raise NotionConfigurationError(f"Database access failed: {str(e)}") 