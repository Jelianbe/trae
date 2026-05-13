"""Fix JSON test file: replace ASCII " with Chinese quotes in Chinese text context"""
import re

path = 'D:/trae/novel-tts-engine/analysis_reports/新建 文本文档 (5).txt'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.strip()
if content.startswith('```json'):
    content = content[7:]
if content.endswith('```'):
    content = content[:-3]

# Find all " positions and their context
# Convert to char array for in-place modification
chars = list(content)
result = []
CHINESE = re.compile(r'[\u4e00-\u9fa5]')
CN_PUNCT = re.compile(r'[\u4e00-\u9fa5。，！？、；：）\)]')

i = 0
while i < len(chars):
    c = chars[i]
    if c != '"':
        result.append(c)
        i += 1
        continue
    
    prev = chars[i-1] if i > 0 else ''
    prev2 = chars[i-2] if i >= 2 else ''
    nxt = chars[i+1] if i < len(chars)-1 else ''
    
    is_json_start = (prev in ':,' and content[i-1:i+1] in (':"', ',"')) or prev in '[{('
    is_json_end = (nxt in ',}\n\r]')
    is_double_quote = (nxt == '"')  # followed by another "
    
    # Chinese left quote: prev is non-sentence-ender punctuation + Chinese follows
    # (到："你) or (说："你) → LEFT
    # But (。"他) → RIGHT (after sentence end)
    is_cn_left = bool(CN_PUNCT.match(prev) and prev not in '。！？') and bool(CHINESE.match(nxt))
    # Chinese right quote: Chinese/punctuation before, non-JSON-non-quote char after
    is_cn_right = bool(CN_PUNCT.match(prev)) and not is_json_end and nxt not in '"' and nxt not in '，,。'
    
    if is_json_start or is_json_end:
        result.append('"')
    elif is_double_quote and bool(CN_PUNCT.match(prev)):
        result.append('\u201d')
    elif is_cn_left:
        result.append('\u201c')
    elif is_cn_right:
        result.append('\u201d')
    else:
        result.append('"')
    i += 1

fixed = ''.join(result)

import json
try:
    data = json.loads(fixed)
    print(f"Valid JSON: {len(data)} paragraphs")
    
    from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS
    total = 0
    for item in data:
        text = item['paragraph']
        count = sum(1 for pat in DIALOGUE_PATTERNS for _ in pat.finditer(text))
        expected = len(item['dialogues'])
        total += count
        if count != expected:
            print(f"  P{item['id']}: found={count} exp={expected}")
    print(f"Total: {total}/73")
    
    # Fix paragraphs missing leading opening quote
    # These are paragraphs where dialogue starts at the beginning
    # but the text doesn't start with "
    for item in data:
        text = item['paragraph']
        if text and not text.startswith('\u201c'):
            # Check if the first dialogue should have an opening quote
            # by looking at the first character that IS a dialogue
            from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS
            matches = list(DIALOGUE_PATTERNS[0].finditer(text))
            if matches:
                # Insert opening quote at the start
                text = '\u201c' + text
                # Also need to add closing quote 
                # Find where this first dialogue ends
                first_match = matches[0]
                dlg_text = first_match.group(2)
                # The dialogue starts at position 0 (after inserting ")
                # The closing " should be right before the match end
                end = first_match.end()
                # Actually, DIALOGUE_PATTERNS[0] includes the quotes
                # So we just need to ensure the opening " is at position 0
                item['paragraph'] = text
    
    # Also fix paragraphs that START with " (Chinese left quote) but the
    # DIALOGUE_PATTERNS should catch them
    
    print(f"Total text dialogues match test:")
    total = 0
    from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS as DP
    for item in data:
        count = sum(1 for pat in DP for _ in pat.finditer(item['paragraph']))
        total += count
    print(f"  {total}/{sum(len(i['dialogues']) for i in data)}")
    
    # Write fixed version
    with open(path, 'w', encoding='utf-8') as f:
        f.write('```json\n')
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n```')
    print("Written to file")
    
except json.JSONDecodeError as e:
    print(f"JSON error at line {fixed[:e.pos].count(chr(10))}: {e}")
    ctx = fixed[max(0,e.pos-60):e.pos+60]
    print(f"Context: {repr(ctx)}")
