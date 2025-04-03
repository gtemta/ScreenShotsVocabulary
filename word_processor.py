import spacy
import nltk
from nltk.corpus import wordnet
from nltk.corpus import brown
import json
import os
import re

# 下载必要的 NLTK 数据
nltk.download('wordnet')
nltk.download('brown')

def is_valid_english_word(word):
    """
    检查单词是否只包含英文字母，并过滤特殊格式
    
    Args:
        word (str): 要检查的单词
        
    Returns:
        bool: 如果是有效的英文字母则返回 True
    """
    # 过滤掉包含版本号格式的文本（如 V0.92350）
    if re.match(r'^[vV]\d+\.?\d*', word):
        return False
        
    # 过滤掉包含数字的文本
    if re.search(r'\d', word):
        return False
        
    # 过滤掉包含特殊字符的文本
    if re.search(r'[^a-zA-Z]', word):
        return False
        
    # 过滤掉太短的单词
    if len(word) < 2:
        return False
        
    # 过滤掉全大写的单词（通常是缩写）
    if word.isupper():
        return False
        
    # 过滤掉包含连续相同字母的单词（如 "hellooo"）
    if re.search(r'(.)\1{2,}', word):
        return False
        
    return True

class WordInfo:
    def __init__(self, word, chinese_word, definition, chinese_definition, examples, synonyms, antonyms):
        """
        单字信息类
        
        Args:
            word (str): 英文单词
            chinese_word (str): 中文翻译
            definition (str): 英文定义
            chinese_definition (str): 中文解释
            examples (list): 例句列表
            synonyms (list): 近义词列表
            antonyms (list): 反义词列表
        """
        self.word = word
        self.chinese_word = chinese_word
        self.definition = definition
        self.chinese_definition = chinese_definition
        self.examples = examples if isinstance(examples, list) else [examples]
        self.synonyms = synonyms if isinstance(synonyms, list) else []
        self.antonyms = antonyms if isinstance(antonyms, list) else []

    def __str__(self):
        """以文字格式显示单字信息"""
        return (
            f"📖 单字: {self.word} ({self.chinese_word})\n"
            f"🔍 定义: {self.definition}\n"
            f"📝 中文解释: {self.chinese_definition}\n"
            f"💡 例句: {'; '.join(self.examples)}\n"
            f"🔗 近义词: {', '.join(self.synonyms) if self.synonyms else '无'}\n"
            f"🚫 反义词: {', '.join(self.antonyms) if self.antonyms else '无'}"
        )

    def to_dict(self):
        """转换为字典格式（适合 JSON 存储或 API 传输）"""
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
        """转换为 Markdown 格式"""
        return f"""# **{self.word.capitalize()} ({self.chinese_word})**

        ## 📖 定义 (Definition)
        - {self.definition}

        ## 📝 中文解释 (Chinese Explanation)
        - {self.chinese_definition}

        ## 💡 例句 (Example Sentence)
        - {self.examples[0] if self.examples else 'No examples available'}

        ## 🔗 近义词 (Synonyms)
        - {", ".join(self.synonyms) if self.synonyms else "无"}

        ## 🚫 反义词 (Antonyms)
        - {", ".join(self.antonyms) if self.antonyms else "无"}
        """

def get_word_difficulty(word):
    """
    评估单词的难度
    
    Args:
        word (str): 要评估的单词
        
    Returns:
        float: 难度分数（0-1之间，越高越难）
    """
    # 获取单词的所有同义词集
    synsets = wordnet.synsets(word)
    if not synsets:
        return 1.0  # 如果找不到同义词集，认为是最难的
        
    # 计算难度分数
    difficulty_score = 0.0
    
    # 1. 基于词频的难度（在 Brown 语料库中的出现频率）
    word_freq = sum(1 for w in brown.words() if w.lower() == word.lower())
    freq_score = 1.0 - min(word_freq / 1000, 1.0)  # 归一化到 0-1
    difficulty_score += freq_score * 0.4  # 词频权重 40%
    
    # 2. 基于同义词数量的难度
    synonym_count = len(set(lemma.name() for syn in synsets for lemma in syn.lemmas()))
    syn_score = min(synonym_count / 10, 1.0)  # 归一化到 0-1
    difficulty_score += syn_score * 0.3  # 同义词数量权重 30%
    
    # 3. 基于定义长度的难度
    definition_length = sum(len(syn.definition().split()) for syn in synsets)
    def_score = min(definition_length / 50, 1.0)  # 归一化到 0-1
    difficulty_score += def_score * 0.3  # 定义长度权重 30%
    
    return min(difficulty_score, 1.0)

def load_processed_words():
    """
    加载已处理过的单词列表
    
    Returns:
        set: 已处理单词集合
    """
    try:
        if os.path.exists('processed_words.json'):
            with open('processed_words.json', 'r', encoding='utf-8') as f:
                return set(json.load(f))
    except Exception as e:
        print(f"⚠️ 無法加載已處理單詞列表: {str(e)}")
    return set()

def save_processed_word(word):
    """
    保存已处理的单词
    
    Args:
        word (str): 要保存的单词
    """
    processed_words = load_processed_words()
    processed_words.add(word.lower())
    try:
        with open('processed_words.json', 'w', encoding='utf-8') as f:
            json.dump(list(processed_words), f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ 無法保存已處理單詞: {str(e)}")

def extract_keyword(text, min_difficulty=0.7):
    """
    从文本中提取关键词，过滤已处理过的单词和简单单词
    
    Args:
        text (str): 输入文本
        min_difficulty (float): 最小难度要求（0-1之间），默认0.7
        
    Returns:
        str: 提取的关键词
    """
    # 加载已处理的单词
    processed_words = load_processed_words()
    
    # 加载 spaCy 模型
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    
    # 提取所有可能的单词
    candidates = []
    for token in doc:
        # 只考虑名词、动词和形容词
        if token.pos_ in ["NOUN", "VERB", "ADJ"]:
            word = token.text.lower()
            # 过滤已处理的单词、短单词和包含特殊字符的单词
            if (word not in processed_words and 
                len(word) >= 2 and 
                is_valid_english_word(word)):
                # 计算单词难度
                difficulty = get_word_difficulty(word)
                if difficulty >= min_difficulty:
                    candidates.append((word, difficulty))
    
    if not candidates:
        return "No suitable keywords found"
    
    # 按难度排序并选择最难的单词
    candidates.sort(key=lambda x: x[1], reverse=True)
    selected_word = candidates[0][0]
    
    # 保存已处理的单词
    save_processed_word(selected_word)
    
    return selected_word

def get_word_info(word):
    """
    获取单词的详细信息
    
    Args:
        word (str): 要查询的单词
        
    Returns:
        WordInfo: 包含单词详细信息的对象
    """
    synsets = wordnet.synsets(word)
    if not synsets:
        return None

    definition = synsets[0].definition()
    examples = synsets[0].examples()[:1]
    synonyms = set(lemma.name() for syn in synsets for lemma in syn.lemmas())
    antonyms = set(lemma.antonyms()[0].name() for syn in synsets for lemma in syn.lemmas() if lemma.antonyms())

    word_info = WordInfo(
        word=word,
        chinese_word="",  # 需要另外翻译获取
        definition=definition,
        chinese_definition="",  # 需要另外翻译获取
        examples=examples if examples else ["No examples available"],
        synonyms=list(synonyms)[:3],
        antonyms=list(antonyms)[:3]
    )
    
    return word_info 