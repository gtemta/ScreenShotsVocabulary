import asyncio
import logging
import sys
from pathlib import Path
from typing import List
from processors.word_processor import WordProcessor, is_valid_english_sentence
from uploaders.image_upload_manager import ImageUploadManager, ImageUploadError
from uploaders.notion_uploader import NotionUploader, UploadError
from ocr_utils import extract_text, ImageProcessingError
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
            
        # 4. 上傳圖片到雲端（多個服務商自動備援）
        try:
            upload_manager = ImageUploadManager()
            print(f"\n嘗試上傳圖片到雲端（可用服務商: {len(upload_manager.providers)} 個）...")
            
            image_url = upload_manager.upload_image(image_path)
            if not image_url:
                print("❌ 圖片上傳失敗：所有服務商都無法使用")
                return
                
            print(f"✅ 圖片已成功上傳: {image_url}")
            
        except ImageUploadError as e:
            print(f"❌ 圖片上傳失敗: {e}")
            return
        except Exception as e:
            print(f"❌ 圖片上傳時發生未預期錯誤: {e}")
            return
        
        # 5. 上傳最重要的單字到 Notion（單一單字模式）
        notion = NotionUploader()
        total_words = len(final_result["vocabulary"])
        
        if total_words == 0:
            print("❌ 沒有找到需要學習的詞彙")
            return
        
        # 只處理第一個（最重要的）單字
        vocab = final_result["vocabulary"][0]
        chinese_word = final_result["chinese_words"][0]
        definition = final_result["definitions"][0]
        chinese_def = final_result["chinese_definitions"][0]
        examples = final_result["examples"][0]
        synonyms = final_result["synonyms"][0]
        antonyms = final_result["antonyms"][0]
        
        print(f"\n專注學習最重要的詞彙: {vocab}")
        print(f"（AI 從 {total_words} 個候選詞彙中智能篩選）")
        
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
            
            print(f"✅ 成功上傳詞彙: {vocab}")
            
            # 6. 保存新學習的單字
            save_learned_words([vocab])
            print(f"✅ 已記錄學習進度，避免重複學習")
            
        except Exception as e:
            print(f"❌ 上傳詞彙 {vocab} 失敗: {str(e)}")
            return
            
    except Exception as e:
        print(f"❌ 處理圖片時發生錯誤: {str(e)}")

def get_image_files(directory_path: str) -> List[str]:
    """Get all supported image files from directory"""
    path = Path(directory_path)
    if not path.is_dir():
        raise ImageProcessingError(f"Directory not found: {directory_path}")
        
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
    image_files = []
    
    for ext in extensions:
        image_files.extend(glob.glob(str(path / ext)))
        image_files.extend(glob.glob(str(path / ext.upper())))
    
    return sorted(image_files)

async def process_batch(image_paths: List[str]) -> int:
    """Process multiple images and return success count"""
    success_count = 0
    total_images = len(image_paths)
    
    logger.info(f"Processing batch of {total_images} images")
    
    for i, image_path in enumerate(image_paths, 1):
        try:
            logger.info(f"Processing image {i}/{total_images}: {Path(image_path).name}")
            
            success = await process_image(image_path)
            if success:
                success_count += 1
                logger.info(f"✅ Successfully processed image {i}/{total_images}")
            else:
                logger.warning(f"⚠️ No vocabulary extracted from image {i}/{total_images}")
                
        except ImageProcessingError as e:
            logger.error(f"❌ Image processing failed for {Path(image_path).name}: {e}")
            continue
        except UploadError as e:
            logger.error(f"❌ Upload failed for {Path(image_path).name}: {e}")
            continue
        except Exception as e:
            logger.error(f"❌ Unexpected error for {Path(image_path).name}: {e}")
            continue
    
    logger.info(f"Batch processing completed: {success_count}/{total_images} images processed successfully")
    return success_count

async def main():
    """Main application entry point with comprehensive error handling"""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description='Process images and upload vocabulary to Notion',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python main.py --path image.jpg          # Process single image
  python main.py --path /path/to/images/   # Process directory
  python main.py /path/to/image.png        # Process single image (positional)
            """
        )
        parser.add_argument(
            'positional_path', 
            nargs='?', 
            help='Image file path or directory path'
        )
        parser.add_argument(
            '--path', 
            type=str, 
            help='Image file path or directory path (alternative syntax)'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        args = parser.parse_args()
        
        # Set logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Get path from arguments (positional or named)
        target_path = args.path or args.positional_path
        
        if not target_path:
            parser.print_help()
            logger.error("No path provided. Please specify an image file or directory.")
            sys.exit(1)
        
        target_path = Path(target_path)
        
        # Validate environment configuration
        required_env_vars = ['NOTION_API_KEY', 'NOTION_DATABASE_ID']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("Please check your .env file or environment configuration")
            sys.exit(1)
        
        # Process images
        if target_path.is_file():
            # Process single image
            logger.info(f"Processing single image: {target_path}")
            try:
                success = await process_image(str(target_path))
                if success:
                    logger.info("✅ Image processing completed successfully")
                else:
                    logger.warning("⚠️ No vocabulary extracted from image")
                    sys.exit(1)
            except (ImageProcessingError, UploadError) as e:
                logger.error(f"❌ Processing failed: {e}")
                sys.exit(1)
                
        elif target_path.is_dir():
            # Process directory
            logger.info(f"Processing directory: {target_path}")
            try:
                image_files = get_image_files(str(target_path))
                if not image_files:
                    logger.warning(f"No supported image files found in: {target_path}")
                    sys.exit(1)
                    
                success_count = await process_batch(image_files)
                if success_count == 0:
                    logger.error("❌ No images were processed successfully")
                    sys.exit(1)
                else:
                    logger.info(f"✅ Batch processing completed: {success_count}/{len(image_files)} images successful")
                    
            except ImageProcessingError as e:
                logger.error(f"❌ Directory processing failed: {e}")
                sys.exit(1)
        else:
            logger.error(f"❌ Invalid path: {target_path} (not a file or directory)")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Unexpected application error: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1) 