import re
import string
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class TextCleaner:
    """OCR文字清理器，專門處理截圖文字提取後的雜訊問題"""
    
    def __init__(self):
        # 編譯正則表達式模式以提高效率
        self.patterns = self._compile_cleaning_patterns()
        
    def _compile_cleaning_patterns(self) -> dict:
        """編譯所有清理用的正則表達式模式"""
        return {
            # 版本號和座標信息 (V0.92350, VII NS x)
            'version_coords': re.compile(r'\b[V]?\d+\.\d+\w*\b|^[IVX]+\s+[A-Z]+\s+[a-z]$', re.MULTILINE),
            
            # 無意義的短符號組合 (少於3個字符且包含特殊符號)
            'meaningless_symbols': re.compile(r'^[^\w\s]{1,3}$|^[\w\s]{1,2}[^\w\s]+$', re.MULTILINE),
            
            # 孤立的單字符或數字行
            'isolated_chars': re.compile(r'^\s*[a-zA-Z0-9]\s*$', re.MULTILINE),
            
            # 大量特殊符號的行 (符號比例>50%)
            'symbol_heavy': re.compile(r'^[^\w\s]*[\w\s][^\w\s]*$', re.MULTILINE),
            
            # 系統路徑和URL殘留
            'paths_urls': re.compile(r'[/\\][a-zA-Z0-9_\-/.\\]+|https?://\S+'),
            
            # 連續的特殊符號 (3個以上)
            'consecutive_symbols': re.compile(r'[^\w\s]{3,}'),
            
            # 英文單詞模式 (用於保留有用內容)
            'english_words': re.compile(r'\b[a-zA-Z]+\b'),
            
            # 完整句子模式
            'complete_sentences': re.compile(r'[A-Z][^.!?]*[.!?]'),
            
            # 對話模式 (引號包圍的內容)
            'dialogue': re.compile(r'"[^"]*"|\'[^\']*\'')
        }
    
    def clean_ocr_text(self, raw_text: str) -> str:
        """
        清理OCR提取的原始文字
        
        Args:
            raw_text: OCR提取的原始文字
            
        Returns:
            清理後的乾淨文字
        """
        if not raw_text or not raw_text.strip():
            return ""
            
        logger.info(f"開始清理OCR文字，原始長度: {len(raw_text)} 字符")
        
        # 第一階段：基本清理
        cleaned = self._basic_cleaning(raw_text)
        
        # 第二階段：行級過濾
        cleaned = self._filter_lines(cleaned)
        
        # 第三階段：句子重組
        cleaned = self._reconstruct_sentences(cleaned)
        
        # 第四階段：最終清理
        cleaned = self._final_cleanup(cleaned)
        
        logger.info(f"文字清理完成，清理後長度: {len(cleaned)} 字符")
        
        return cleaned
    
    def _basic_cleaning(self, text: str) -> str:
        """基本清理：移除明顯的系統信息和路徑"""
        # 移除版本號和座標
        text = self.patterns['version_coords'].sub('', text)
        
        # 移除路徑和URL
        text = self.patterns['paths_urls'].sub('', text)
        
        # 處理連續符號
        text = self.patterns['consecutive_symbols'].sub(' ', text)
        
        # 標準化空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _filter_lines(self, text: str) -> str:
        """行級過濾：移除無意義的行"""
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳過空行
            if not line:
                continue
                
            # 跳過純符號行
            if self.patterns['meaningless_symbols'].match(line):
                continue
                
            # 跳過孤立字符
            if self.patterns['isolated_chars'].match(line):
                continue
                
            # 檢查英文內容比例
            english_words = self.patterns['english_words'].findall(line)
            if len(english_words) > 0:  # 包含英文單詞的行
                filtered_lines.append(line)
            elif len(line) > 20:  # 長行可能包含有用內容
                filtered_lines.append(line)
                
        return '\n'.join(filtered_lines)
    
    def _reconstruct_sentences(self, text: str) -> str:
        """句子重組：嘗試修復被分割的句子"""
        lines = text.split('\n')
        reconstructed = []
        current_sentence = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 如果當前行以大寫字母開頭，可能是新句子
            if line and line[0].isupper() and current_sentence:
                # 保存前一個句子
                if current_sentence.strip():
                    reconstructed.append(current_sentence.strip())
                current_sentence = line
            else:
                # 繼續當前句子
                if current_sentence:
                    current_sentence += " " + line
                else:
                    current_sentence = line
            
            # 如果句子以標點結尾，完成這個句子
            if current_sentence and current_sentence[-1] in '.!?':
                reconstructed.append(current_sentence.strip())
                current_sentence = ""
        
        # 處理最後一個句子
        if current_sentence.strip():
            reconstructed.append(current_sentence.strip())
            
        return '\n'.join(reconstructed)
    
    def _final_cleanup(self, text: str) -> str:
        """最終清理：格式化和質量控制"""
        lines = text.split('\n')
        final_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳過過短的行（少於3個字符）
            if len(line) < 3:
                continue
                
            # 修復常見OCR錯誤
            line = self._fix_common_ocr_errors(line)
            
            # 確保句子格式正確
            if line and not line.endswith(('.', '!', '?', ':')):
                # 如果不是以標點結尾，可能是標題或未完整的句子
                if len(line.split()) <= 5:  # 短行，可能是標題
                    pass  # 保持原樣
                else:  # 長行，添加句號
                    line += "."
            
            final_lines.append(line)
        
        result = '\n'.join(final_lines)
        
        # 移除多餘空白
        result = re.sub(r'\n\s*\n', '\n', result)
        result = re.sub(r' +', ' ', result)
        
        return result.strip()
    
    def _fix_common_ocr_errors(self, text: str) -> str:
        """修復常見的OCR錯誤"""
        fixes = {
            # 常見字符混淆
            r'\bl\b': 'I',  # 孤立的小寫l通常是大寫I
            r'\bO\b': '0',  # 在數字上下文中的O
            r'\b0\b(?=[a-zA-Z])': 'O',  # 在字母上下文中的0
            
            # 修復間距問題
            r'([a-z])([A-Z])': r'\1 \2',  # 在小寫和大寫字母間添加空格
            
            # 修復標點符號
            r'\s+([,.!?;:])': r'\1',  # 移除標點前的空格
            r'([.!?])\s*([a-z])': r'\1 \2',  # 確保句子間的空格
        }
        
        for pattern, replacement in fixes.items():
            text = re.sub(pattern, replacement, text)
            
        return text
    
    def extract_clean_sentences(self, text: str) -> List[str]:
        """提取乾淨的句子列表"""
        cleaned = self.clean_ocr_text(text)
        
        # 分割成句子
        sentences = []
        for line in cleaned.split('\n'):
            line = line.strip()
            if line:
                # 按標點符號分割句子
                parts = re.split(r'[.!?]+', line)
                for part in parts:
                    part = part.strip()
                    if len(part) > 10:  # 只保留有意義長度的句子
                        sentences.append(part)
        
        return sentences
    
    def get_cleaning_stats(self, original: str, cleaned: str) -> dict:
        """獲取清理統計信息"""
        return {
            'original_length': len(original),
            'cleaned_length': len(cleaned),
            'reduction_ratio': 1 - (len(cleaned) / len(original)) if len(original) > 0 else 0,
            'original_lines': len(original.split('\n')),
            'cleaned_lines': len(cleaned.split('\n')),
            'english_words_found': len(re.findall(r'\b[a-zA-Z]+\b', cleaned))
        }