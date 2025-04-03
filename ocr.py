import pytesseract
from PIL import Image
import spacy

def extract_text(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="eng")
    return text

text = extract_text("20240607222058_1.jpg")
print(text)  # 顯示擷取的遊戲對話


nlp = spacy.load("en_core_web_sm")

def extract_keyword(text):
    doc = nlp(text)
    keywords = [token.text for token in doc if token.pos_ in ["NOUN", "VERB", "ADJ"]]
    return keywords[0] if keywords else "No keywords found"

selected_word = extract_keyword(text)
print("選出的單字:", selected_word)

import nltk
nltk.download('wordnet')
from nltk.corpus import wordnet

class WordInfo:
    def __init__(self, word, chinese_word, definition, chinese_definition, examples, synonyms, antonyms):
        """
        單字資訊類別
        
        :param word: 英文單字
        :param chinese_word: 中文翻譯
        :param definition: 英文定義
        :param chinese_definition: 中文解釋
        :param examples: 例句（列表）
        :param synonyms: 近義詞（列表）
        :param antonyms: 反義詞（列表）
        """
        self.word = word
        self.chinese_word = chinese_word
        self.definition = definition
        self.chinese_definition = chinese_definition
        self.examples = examples if isinstance(examples, list) else [examples]
        self.synonyms = synonyms if isinstance(synonyms, list) else []
        self.antonyms = antonyms if isinstance(antonyms, list) else []

    def __str__(self):
        """
        以文字格式顯示單字資訊
        """
        return (
            f"📖 單字: {self.word} ({self.chinese_word})\n"
            f"🔍 定義: {self.definition}\n"
            f"📝 中文解釋: {self.chinese_definition}\n"
            f"💡 例句: {'; '.join(self.examples)}\n"
            f"🔗 近義詞: {', '.join(self.synonyms) if self.synonyms else '無'}\n"
            f"🚫 反義詞: {', '.join(self.antonyms) if self.antonyms else '無'}"
        )

    def to_dict(self):
        """
        轉換成字典格式（適合 JSON 存儲或 API 傳輸）
        """
        return {
            "word": self.word,
            "chinese_word": self.chinese_word,
            "definition": self.definition,
            "chinese_definition": self.chinese_definition,
            "examples": self.examples,
            "synonyms": self.synonyms,
            "antonyms": self.antonyms
        }
    def to_markdown(self):
        """
        轉換為 Markdown 格式
        """
        markdown_content = f"""# **{self.word.capitalize()} ({self.chinese_word})**

        ## 📖 定義 (Definition)
        - {self.definition}

        ## 📝 中文解釋 (Chinese Explanation)
        - {self.chinese_definition}

        ## 💡 例句 (Example Sentence)
        - {self.examples[0] if self.examples else 'No examples available'}

        ## 🔗 近義詞 (Synonyms)
        - {", ".join(self.synonyms) if self.synonyms else "無"}

        ## 🚫 反義詞 (Antonyms)
        - {", ".join(self.antonyms) if self.antonyms else "無"}
        """
        return markdown_content



def get_word_info(word):
    synsets = wordnet.synsets(word)
    if not synsets:
        return None

    definition = synsets[0].definition()  # 取第一個詞義
    examples = synsets[0].examples()[:1]  # 取第一個例句
    synonyms = set(lemma.name() for syn in synsets for lemma in syn.lemmas())  # 近義詞
    antonyms = set(lemma.antonyms()[0].name() for syn in synsets for lemma in syn.lemmas() if lemma.antonyms())  # 反義詞

    # 使用 WordInfo 類創建實例
    word_info = WordInfo(
        word=word,
        chinese_word="",  # 需要另外翻譯獲取
        definition=definition,
        chinese_definition="",  # 需要另外翻譯獲取
        examples=examples if examples else ["No examples available"],
        synonyms=list(synonyms)[:3],
        antonyms=list(antonyms)[:3]
    )
    
    return word_info

word_info = get_word_info(selected_word)

from googletrans import Translator

def translate_to_chinese(text):
    translator = Translator()
    result = translator.translate(text, src="en", dest="zh-tw")
    return result.text


word_info.chinese_definition = translate_to_chinese(word_info.definition)
word_info.chinese_word = translate_to_chinese(word_info.word)
print(word_info.__str__())

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os.path

def upload_image_to_gdrive(image_path):
    # 如果你還沒有憑證檔案,需要先設定OAuth 2.0
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    creds = None
    # 檢查是否有現有的token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 如果沒有憑證或憑證無效,則要求用戶授權
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        # 保存憑證供之後使用
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # 建立Drive API服務
        service = build('drive', 'v3', credentials=creds)
        
        # 上傳檔案
        file_metadata = {'name': os.path.basename(image_path)}
        media = MediaFileUpload(image_path, mimetype='image/jpeg')
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id,webViewLink').execute()
        
        return file.get('webViewLink')  # 回傳檔案的共用連結
    except Exception as e:
        print(f'上傳過程發生錯誤: {str(e)}')
        return None