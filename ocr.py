import pytesseract
from PIL import Image
import spacy
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'

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
