# ScreenShotsVocabulary

一個自動化工具，可以從截圖中提取英文單字，生成相關信息並上傳到 Notion 數據庫。

## 功能特點

- 📸 從截圖中提取英文文字
- 🔍 自動識別關鍵單字
- 📚 獲取單字的詳細信息（定義、例句、近義詞、反義詞）
- 🌐 自動翻譯成中文
- 🖼️ 圖片上傳到 Imgur
- 📝 自動整理並上傳到 Notion 數據庫

## 安裝步驟

1. Clone Repo：
```bash
git clone https://github.com/gtemta/ScreenShotsVocabulary.git
cd ScreenShotsVocabulary
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

3. 配置環境變量：
   - 複製 `.env.example` 為 `.env`
   - 填入你的 Notion API 密鑰和數據庫 ID

4. 配置 Imgur：
   - 複製 `imgur_credentials.example.json` 為 `imgur_credentials.json`
   - 填入你的 Imgur API client_id

## 使用方法

### 基本用法

程序支持兩種使用方式：

1. 處理單個圖片文件：
```bash
python main.py 圖片路徑
```

2. 處理整個目錄中的圖片：
```bash
python main.py 目錄路徑
```

### 支持的圖片格式
- JPG/JPEG
- PNG
- GIF

### 使用示例

1. 處理單個圖片：
```bash
python main.py C:\Users\YourName\Pictures\word.jpg
# 或
python main.py ./images/word.jpg
```

2. 處理整個文件夾：
```bash
python main.py C:\Users\YourName\Pictures\words_folder
# 或
python main.py ./images/words_folder
```

### 注意事項
- 請使用 `python main.py` 命令來運行程序，不要直接運行圖片文件
- 確保圖片路徑或目錄路徑正確
- 路徑中如果包含空格，請使用引號包裹，例如：
  ```bash
  python main.py "C:\Users\Your Name\Pictures\word.jpg"
  ```

### 輸出結果
- 程序會自動處理圖片
- 提取文字並識別關鍵單字
- 獲取單字詳細信息
- 上傳圖片到 Imgur
- 將所有信息整理並上傳到 Notion 數據庫

## 配置說明

### Notion 配置
在 `.env` 文件中配置：
```
NOTION_TOKEN=你的_Notion_API_密鑰
NOTION_DATABASE_ID=你的_數據庫_ID
```

### Imgur 配置
在 `imgur_credentials.json` 文件中配置：
```json
{
    "client_id": "你的_Imgur_API_Client_ID"
}
```

## 注意事項

- 確保截圖清晰可讀
- 需要有效的 Notion API 密鑰
- 需要有效的 Imgur API 憑證
- 建議使用英文截圖以獲得最佳效果
- 處理目錄時會自動處理所有支持的圖片格式

## 開發環境

- Python 3.8+
- 依賴包：見 requirements.txt

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

## 授權

MIT License
