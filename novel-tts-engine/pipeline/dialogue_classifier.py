import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import os

try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False


@dataclass
class ClassifiedSentence:
    text: str
    sentence_type: str
    confidence: float
    is_dialogue: bool


class DialogueClassifier:
    DIALOGUE_PATTERNS = [
        re.compile(r'[""「」『』【】《》]'),
        re.compile(r'^[「『"].*[」』]'),
        re.compile(r'[""].*[""]'),
        re.compile(r'「[^」]*」'),
        re.compile(r'『[^』]*』'),
        re.compile(r'"[^"]*"'),
        re.compile(r'"[^"]*"'),
    ]
    
    DIALOGUE_MARKERS = ['"', '"', '「', '」', '『', '』', '【', '】']
    
    NARRATION_INDICATORS = [
        '心想', '暗道', '想到', '觉得', '认为', '感觉',
        '看到', '听见', '发现', '注意到', '观察到',
        '这时', '此时', '于是', '然后', '接着', '随后',
        '原来', '其实', '事实上', '实际上',
    ]
    
    DIALOGUE_INDICATORS = [
        '说道', '问道', '答道', '喊道', '叫道', '笑道',
        '说', '问', '答', '喊', '叫', '笑',
        '低声说', '大声说', '轻声说', '小声说',
        '激动地说', '平静地说', '愤怒地说',
    ]

    def __init__(self, model_path: str = None):
        self.model = None
        self._rule_coverage = 0
        
        if model_path and FASTTEXT_AVAILABLE:
            try:
                self.model = fasttext.load_model(model_path)
                print(f"FastText分类器加载成功: {model_path}")
            except Exception as e:
                print(f"FastText模型加载失败: {e}")

    def classify(self, text: str) -> ClassifiedSentence:
        text = text.strip()
        
        rule_result, confidence = self._rule_classify(text)
        
        if rule_result:
            self._rule_coverage += 1
            return ClassifiedSentence(
                text=text,
                sentence_type=rule_result,
                confidence=confidence,
                is_dialogue=(rule_result == 'dialogue')
            )
        
        if self.model and FASTTEXT_AVAILABLE:
            ml_result, ml_confidence = self._ml_classify(text)
            return ClassifiedSentence(
                text=text,
                sentence_type=ml_result,
                confidence=ml_confidence,
                is_dialogue=(ml_result == 'dialogue')
            )
        
        return ClassifiedSentence(
            text=text,
            sentence_type='narration',
            confidence=0.5,
            is_dialogue=False
        )

    def _rule_classify(self, text: str) -> Tuple[Optional[str], float]:
        for pattern in self.DIALOGUE_PATTERNS:
            if pattern.search(text):
                dialogue_content = self._extract_dialogue_content(text)
                if dialogue_content:
                    return 'dialogue', 0.95
        
        has_dialogue_marker = any(marker in text for marker in self.DIALOGUE_MARKERS)
        if has_dialogue_marker:
            return 'dialogue', 0.85
        
        for indicator in self.DIALOGUE_INDICATORS:
            if indicator in text and ('说' in indicator or '问' in indicator or '答' in indicator):
                return 'dialogue', 0.80
        
        for indicator in self.NARRATION_INDICATORS:
            if indicator in text:
                return 'narration', 0.75
        
        return None, 0.0

    def _extract_dialogue_content(self, text: str) -> Optional[str]:
        patterns = [
            (r'「([^」]*)」', 1),
            (r'『([^』]*)』', 1),
            (r'"([^"]*)"', 1),
            (r'"([^"]*)"', 1),
        ]
        
        for pattern, group in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(group)
        
        return None

    def _ml_classify(self, text: str) -> Tuple[str, float]:
        if not self.model:
            return 'narration', 0.5
        
        try:
            labels, probs = self.model.predict(text.replace('\n', ' '))
            
            label = labels[0].replace('__label__', '')
            confidence = float(probs[0])
            
            return label, confidence
        except Exception as e:
            print(f"ML分类失败: {e}")
            return 'narration', 0.5

    def classify_batch(self, texts: List[str]) -> List[ClassifiedSentence]:
        return [self.classify(text) for text in texts]

    def get_rule_coverage(self) -> float:
        return self._rule_coverage

    def train(self, train_file: str, model_output: str, epochs: int = 25, lr: float = 0.5):
        if not FASTTEXT_AVAILABLE:
            print("FastText不可用，无法训练模型")
            return False
        
        try:
            self.model = fasttext.train_supervised(
                input=train_file,
                epoch=epochs,
                lr=lr,
                wordNgrams=2,
                verbose=2
            )
            self.model.save_model(model_output)
            print(f"模型训练完成，保存到: {model_output}")
            return True
        except Exception as e:
            print(f"模型训练失败: {e}")
            return False


def classify_sentence(text: str) -> ClassifiedSentence:
    classifier = DialogueClassifier()
    return classifier.classify(text)


def classify_sentences(texts: List[str]) -> List[ClassifiedSentence]:
    classifier = DialogueClassifier()
    return classifier.classify_batch(texts)


def is_dialogue(text: str) -> bool:
    result = classify_sentence(text)
    return result.is_dialogue
