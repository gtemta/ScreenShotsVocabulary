import asyncio
import logging
from processors.word_processor import WordProcessor, is_valid_english_sentence
from uploaders.imgur_uploader import ImgurUploader
from uploaders.notion_uploader import NotionUploader
from ocr_utils import extract_text
import os
from dotenv import load_dotenv
import argparse
import glob
from models.deepseek_processor import DeepSeekProcessor
from models.gemma_processor import GemmaProcessor
from models.phi3_processor import Phi3Processor
from reviewers.chatgpt_reviewer import ChatGPTReviewer
from utils.word_utils import load_learned_words, save_learned_words

# 載入環境變量
load_dotenv()

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_image(image_path):
    """處理單個圖片"""
    try:
        # 1. 從圖片中提取文字
        text = extract_text(image_path)
        print("提取的文字:", text)
        
        # 2. 初步篩選文字
        # print("\n進行初步文字篩選...")
        # if not is_valid_english_sentence(text):
        #     print("❌ 提取的文字不是有效的英文句子，跳過此圖片")
        #     return
            
        # print("✅ 文字通過初步篩選")
        
        # 3. 使用本地 AI 模型處理文本
        processors = {
            "DeepSeek": DeepSeekProcessor(),
            "Gemma": GemmaProcessor(),
            "Phi-3": Phi3Processor()
        }
        
        # 讀取已學習的單字
        learned_words = load_learned_words()
        print(f"已載入 {len(learned_words)} 個已學習的單字")
        
        # 使用多個模型處理文本
        results = {}
        for name, processor in processors.items():
            print(f"\n使用 {name} 處理文本...")
            result = processor.process_text(text)
            results[name] = result
        
        # 使用 ChatGPT 審核結果
        reviewer = ChatGPTReviewer()
        final_result = reviewer.review_vocabulary(results, learned_words)
        
        if not final_result["vocabulary"]:
            print("❌ 無法從圖片中提取有效的關鍵字，跳過此圖片")
            return
            
        # 4. 上傳圖片到 Imgur（只上傳一次）
        imgur = ImgurUploader()
        image_url = imgur.upload_image(image_path)
        if not image_url:
            print("❌ 圖片上傳到 Imgur 失敗")
            return
            
        print(f"\n圖片已上傳到 Imgur: {image_url}")
        
        # 5. 為每個詞彙創建 Notion 頁面
        notion = NotionUploader()
        success_count = 0
        total_words = len(final_result["vocabulary"])
        new_words = []  # 用於收集成功上傳的新單字
        
        print(f"\n開始上傳 {total_words} 個詞彙到 Notion...")
        
        for i, (vocab, chinese_word, definition, chinese_def, examples, synonyms, antonyms) in enumerate(
            zip(
                final_result["vocabulary"],
                final_result["chinese_words"],
                final_result["definitions"],
                final_result["chinese_definitions"],
                final_result["examples"],
                final_result["synonyms"],
                final_result["antonyms"]
            ),
            1
        ):
            try:
                # 上傳到 Notion
                await notion.upload(
                    word=vocab,
                    image_url=image_url,
                    chinese_word=chinese_word,
                    definition=definition,
                    chinese_definition=chinese_def,
                    examples=examples,
                    synonyms=synonyms,
                    antonyms=antonyms
                )
                success_count += 1
                new_words.append(vocab)  # 添加到新單字列表
                print(f"✅ 成功上傳詞彙 {i}/{total_words}: {vocab}")
            except Exception as e:
                print(f"❌ 上傳詞彙 {vocab} 失敗: {str(e)}")
        
        print(f"\n上傳完成：成功 {success_count}/{total_words} 個詞彙")
        
        # 6. 保存新學習的單字
        if new_words:
            save_learned_words(new_words)
            
    except Exception as e:
        print(f"❌ 處理圖片時發生錯誤: {str(e)}")

async def main():
    try:
        # 創建命令行參數解析器
        parser = argparse.ArgumentParser(description='處理圖片並上傳到 Notion')
        parser.add_argument('--path', type=str, help='圖片路徑或目錄路徑')
        args = parser.parse_args()
        
        # 處理圖片
        if args.path:
            if os.path.isfile(args.path):
                # 處理單個圖片
                await process_image(args.path)
            elif os.path.isdir(args.path):
                # 處理目錄中的所有圖片
                image_files = glob.glob(os.path.join(args.path, '*.jpg')) + \
                            glob.glob(os.path.join(args.path, '*.png'))
                for image_path in image_files:
                    await process_image(image_path)
            else:
                print(f"❌ 無效的路徑: {args.path}")
        else:
            print("❌ 請提供圖片路徑或目錄路徑")
            
    except Exception as e:
        logger.error(f"處理過程發生錯誤: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 