import os
import logging
from typing import Dict, List, Tuple, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PropertyType(Enum):
    """Notion 資料庫屬性類型"""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    URL = "url"
    
@dataclass
class PropertyDefinition:
    """Notion 資料庫屬性定義"""
    name: str
    property_type: PropertyType
    required: bool = True
    description: str = ""
    select_options: Optional[List[str]] = None
    
class NotionDatabaseValidator:
    """Notion 資料庫結構驗證器"""
    
    def __init__(self, database_id: str = None, api_key: str = None):
        self.database_id = database_id or os.getenv('NOTION_DATABASE_ID')
        self.api_key = api_key or os.getenv('NOTION_API_KEY')
        self.client = Client(auth=self.api_key) if self.api_key else None
        
        # 定義理想的資料庫結構
        self.ideal_schema = self._define_ideal_schema()
        
    def _define_ideal_schema(self) -> Dict[str, PropertyDefinition]:
        """定義理想的Notion資料庫結構"""
        return {
            # 核心詞彙欄位
            "Name": PropertyDefinition(
                name="Name",
                property_type=PropertyType.TITLE,
                required=True,
                description="英文單字或短語"
            ),
            "Chinese": PropertyDefinition(
                name="Chinese", 
                property_type=PropertyType.RICH_TEXT,
                required=True,
                description="中文翻譯"
            ),
            "Definition": PropertyDefinition(
                name="Definition",
                property_type=PropertyType.RICH_TEXT,
                required=True,
                description="英文定義"
            ),
            "Chinese Definition": PropertyDefinition(
                name="Chinese Definition",
                property_type=PropertyType.RICH_TEXT,
                required=True,
                description="中文定義"
            ),
            
            # 詞彙詳細信息
            "Image URL": PropertyDefinition(
                name="Image URL",
                property_type=PropertyType.URL,
                required=False,
                description="原始截圖連結"
            ),
            "Examples": PropertyDefinition(
                name="Examples",
                property_type=PropertyType.RICH_TEXT,
                required=False,
                description="例句"
            ),
            "Synonyms": PropertyDefinition(
                name="Synonyms",
                property_type=PropertyType.RICH_TEXT,
                required=False,
                description="同義詞"
            ),
            "Antonyms": PropertyDefinition(
                name="Antonyms",
                property_type=PropertyType.RICH_TEXT,
                required=False,
                description="反義詞"
            ),
            
            # SRS 學習系統欄位
            "Learning Status": PropertyDefinition(
                name="Learning Status",
                property_type=PropertyType.SELECT,
                required=False,
                description="學習狀態",
                select_options=["新學習", "學習中", "已熟悉", "已掌握"]
            ),
            "Difficulty": PropertyDefinition(
                name="Difficulty",
                property_type=PropertyType.SELECT,
                required=False,
                description="單字困難度",
                select_options=["簡單", "中等", "困難", "極難"]
            ),
            "Last Review": PropertyDefinition(
                name="Last Review",
                property_type=PropertyType.DATE,
                required=False,
                description="上次複習日期"
            ),
            "Next Review": PropertyDefinition(
                name="Next Review",
                property_type=PropertyType.DATE,
                required=False,
                description="下次複習日期"
            ),
            "Review Count": PropertyDefinition(
                name="Review Count",
                property_type=PropertyType.NUMBER,
                required=False,
                description="複習次數"
            ),
            "Mastery Level": PropertyDefinition(
                name="Mastery Level",
                property_type=PropertyType.SELECT,
                required=False,
                description="掌握程度",
                select_options=["0星", "1星", "2星", "3星", "4星", "5星"]
            )
        }
    
    def validate_database_structure(self) -> Tuple[bool, Dict]:
        """
        驗證Notion資料庫結構
        
        Returns:
            (is_valid, report): 驗證結果和詳細報告
        """
        if not self.client or not self.database_id:
            return False, {
                "error": "Missing Notion API key or database ID",
                "missing_config": ["NOTION_API_KEY", "NOTION_DATABASE_ID"]
            }
        
        try:
            # 獲取資料庫結構
            database = self.client.databases.retrieve(self.database_id)
            current_properties = database.get("properties", {})
            
            # 分析當前結構
            report = self._analyze_database_structure(current_properties)
            
            # 檢查是否所有必需欄位都存在
            is_valid = len(report["missing_required"]) == 0
            
            logger.info(f"Database validation completed. Valid: {is_valid}")
            return is_valid, report
            
        except APIResponseError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}
    
    def _analyze_database_structure(self, current_properties: Dict) -> Dict:
        """分析資料庫結構並生成報告"""
        report = {
            "current_properties": {},
            "missing_required": [],
            "missing_optional": [],
            "type_mismatches": [],
            "unexpected_properties": [],
            "compatibility_score": 0,
            "recommendations": []
        }
        
        # 分析當前屬性
        for prop_name, prop_data in current_properties.items():
            prop_type = prop_data.get("type", "unknown")
            report["current_properties"][prop_name] = prop_type
        
        # 檢查理想結構中的每個屬性
        for prop_name, ideal_prop in self.ideal_schema.items():
            if prop_name not in current_properties:
                if ideal_prop.required:
                    report["missing_required"].append(prop_name)
                else:
                    report["missing_optional"].append(prop_name)
            else:
                # 檢查類型匹配
                current_type = current_properties[prop_name].get("type")
                if current_type != ideal_prop.property_type.value:
                    report["type_mismatches"].append({
                        "property": prop_name,
                        "expected": ideal_prop.property_type.value,
                        "actual": current_type
                    })
        
        # 檢查意外的屬性
        for prop_name in current_properties:
            if prop_name not in self.ideal_schema:
                report["unexpected_properties"].append(prop_name)
        
        # 計算兼容性分數
        total_properties = len(self.ideal_schema)
        missing_count = len(report["missing_required"]) + len(report["missing_optional"])
        mismatch_count = len(report["type_mismatches"])
        
        compatibility_score = max(0, (total_properties - missing_count - mismatch_count) / total_properties * 100)
        report["compatibility_score"] = round(compatibility_score, 1)
        
        # 生成建議
        report["recommendations"] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """根據分析結果生成改善建議"""
        recommendations = []
        
        if report["missing_required"]:
            recommendations.append(
                f"❌ 緊急：缺少必需欄位: {', '.join(report['missing_required'])}"
            )
        
        if report["type_mismatches"]:
            for mismatch in report["type_mismatches"]:
                recommendations.append(
                    f"⚠️ 類型不匹配：'{mismatch['property']}' 應為 {mismatch['expected']}，實際為 {mismatch['actual']}"
                )
        
        if report["missing_optional"]:
            recommendations.append(
                f"💡 建議新增SRS功能欄位: {', '.join(report['missing_optional'][:3])}..."
            )
        
        if report["compatibility_score"] < 50:
            recommendations.append("🔧 建議重新建立資料庫以獲得最佳功能支援")
        elif report["compatibility_score"] < 80:
            recommendations.append("✨ 建議新增缺失欄位以啟用完整功能")
        
        return recommendations
    
    def generate_database_creation_guide(self) -> str:
        """生成資料庫建立指南"""
        guide = "# Notion 資料庫建立指南\n\n"
        guide += "## 必需屬性 (核心功能)\n\n"
        
        for prop_name, prop_def in self.ideal_schema.items():
            if prop_def.required:
                guide += f"### {prop_name}\n"
                guide += f"- 類型: {prop_def.property_type.value}\n"
                guide += f"- 說明: {prop_def.description}\n"
                if prop_def.select_options:
                    guide += f"- 選項: {', '.join(prop_def.select_options)}\n"
                guide += "\n"
        
        guide += "## 可選屬性 (進階功能)\n\n"
        
        for prop_name, prop_def in self.ideal_schema.items():
            if not prop_def.required:
                guide += f"### {prop_name}\n"
                guide += f"- 類型: {prop_def.property_type.value}\n"
                guide += f"- 說明: {prop_def.description}\n"
                if prop_def.select_options:
                    guide += f"- 選項: {', '.join(prop_def.select_options)}\n"
                guide += "\n"
        
        return guide
    
    def get_minimal_required_properties(self) -> List[str]:
        """獲取最低限度必需的屬性列表"""
        return [name for name, prop in self.ideal_schema.items() if prop.required]
    
    def check_connection(self) -> Tuple[bool, str]:
        """檢查Notion API連接"""
        if not self.client:
            return False, "Notion API key not configured"
        
        if not self.database_id:
            return False, "Database ID not configured"
        
        try:
            database = self.client.databases.retrieve(self.database_id)
            return True, f"Successfully connected to database: {database.get('title', [{}])[0].get('plain_text', 'Untitled')}"
        except APIResponseError as e:
            return False, f"API error: {str(e)}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"