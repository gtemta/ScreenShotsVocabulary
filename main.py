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
            'path', 
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
        
        # Get path from arguments
        target_path = args.path or getattr(args, 'path', None)
        
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