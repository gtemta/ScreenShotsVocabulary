from ocr_utils import extract_text
from word_processor import extract_keyword, get_word_info
from translator import translate_to_chinese
from imgur_uploader import ImgurUploader
from notion_utils import NotionUploader
import os
from dotenv import load_dotenv
import argparse
import glob

def process_image(image_path, notion_api_key=None, notion_database_id=None):
    """
    處理圖片並獲取單字信息
    
    Args:
        image_path (str): 圖片文件路徑
        notion_api_key (str, optional): Notion API 密鑰
        notion_database_id (str, optional): Notion 數據庫 ID
    """
    # 檢查 Notion 配置
    if not notion_api_key or not notion_database_id:
        print("⚠️ 警告: Notion API 密鑰或數據庫 ID 未設置")
        print("請檢查 .env 文件是否包含以下配置：")
        print("NOTION_TOKEN=你的 Notion API 密鑰")
        print("NOTION_DATABASE_ID=你的數據庫 ID")
        return

    # 1. 從圖片中提取文字
    text = extract_text(image_path)
    print("提取的文字:", text)
    
    # 2. 提取關鍵詞
    selected_word = extract_keyword(text)
    print("選出的單字:", selected_word)
    
    # 檢查是否找到有效的關鍵字
    if selected_word == "No suitable keywords found":
        print("❌ 無法從圖片中提取有效的關鍵字，跳過此圖片")
        return
    
    # 3. 獲取單字詳細信息
    word_info = get_word_info(selected_word)
    if not word_info:
        print(f"❌ 無法獲取單字 '{selected_word}' 的詳細信息，跳過此圖片")
        return
        
    # 4. 翻譯單字和定義
    word_info.chinese_definition = translate_to_chinese(word_info.definition)
    word_info.chinese_word = translate_to_chinese(word_info.word)
    
    # 5. 顯示結果
    print("\n單字信息:")
    print(word_info)
    
    # 6. 上傳圖片到 Imgur
    imgur = ImgurUploader()
    imgur_link = imgur.upload_image(image_path)
    if imgur_link:
        print(f"\n圖片已上傳到 Imgur: {imgur_link}")
        
        # 7. 上傳到 Notion
        try:
            notion_uploader = NotionUploader(notion_api_key, notion_database_id)
            notion_uploader.upload_word_info(
                selected_word,
                word_info,
                imgur_link
            )
        except Exception as e:
            print(f"❌ Notion 上傳失敗: {str(e)}")
            print("請檢查：")
            print("1. Notion API 密鑰是否正確")
            print("2. 數據庫 ID 是否正確")
            print("3. 數據庫是否已與集成共享")
            print("4. 網絡連接是否正常")
    else:
        print("❌ Imgur 上傳失敗，無法繼續 Notion 上傳")

def process_directory(directory_path, notion_api_key, notion_database_id):
    """
    處理目錄中的所有圖片文件
    
    Args:
        directory_path (str): 目錄路徑
        notion_api_key (str): Notion API 密鑰
        notion_database_id (str): Notion 數據庫 ID
    """
    # 支持的圖片格式
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif']
    image_files = []
    
    # 收集所有圖片文件
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(directory_path, ext)))
    
    if not image_files:
        print(f"⚠️ 在目錄 {directory_path} 中沒有找到支持的圖片文件")
        return
    
    print(f"找到 {len(image_files)} 個圖片文件")
    
    # 處理每個圖片文件
    for image_path in image_files:
        print(f"\n處理圖片: {os.path.basename(image_path)}")
        process_image(image_path, notion_api_key, notion_database_id)

def main():
    # 創建命令行參數解析器
    parser = argparse.ArgumentParser(description='從圖片中提取單字並上傳到 Notion')
    parser.add_argument('path', help='圖片文件路徑或包含圖片的目錄路徑')
    args = parser.parse_args()
    
    # 加載 .env 文件
    load_dotenv()
    
    # 從 .env 文件獲取 Notion 配置
    notion_api_key = os.getenv("NOTION_TOKEN")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_api_key or not notion_database_id:
        print("❌ 錯誤: 未找到 Notion 配置")
        print("請確保 .env 文件存在並包含以下配置：")
        print("NOTION_TOKEN=你的 Notion API 密鑰")
        print("NOTION_DATABASE_ID=你的數據庫 ID")
        exit(1)
    
    # 檢查路徑是否存在
    if not os.path.exists(args.path):
        print(f"❌ 錯誤: 路徑 '{args.path}' 不存在")
        exit(1)
    
    # 根據路徑類型進行處理
    if os.path.isdir(args.path):
        process_directory(args.path, notion_api_key, notion_database_id)
    elif os.path.isfile(args.path):
        process_image(args.path, notion_api_key, notion_database_id)
    else:
        print(f"❌ 錯誤: '{args.path}' 既不是文件也不是目錄")
        exit(1)

if __name__ == "__main__":
    main() 