"""解析新建文本文档.txt中的测试用例，转换为统一格式"""
import re, json

def parse_new_cases(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    cases = []
    seen_ids = set()

    blocks = content.strip().split('\n\n')
    current_case = {}
    current_id = None

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if not block.startswith('#'):
            continue

        lines = block.split('\n')
        case_id = None
        fields = {}
        current_field = None
        current_value = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('# ') and not case_id:
                case_id = stripped[2:].strip()
                continue

            for prefix in ['旁白上下文：', '旁白上下文:', '对话内容：', '对话内容:', 
                          '期望说话人：', '期望说话人:', '旁白后文：', '旁白后文:',
                          '易错点：', '易错点:']:
                if stripped.startswith(prefix):
                    if current_field and current_value:
                        val = '\n'.join(current_value).strip()
                        if val and val != '(无)':
                            if current_field in fields:
                                if isinstance(fields[current_field], list):
                                    fields[current_field].append(val)
                                else:
                                    fields[current_field] = [fields[current_field], val]
                            else:
                                fields[current_field] = val
                    current_field = prefix.rstrip('：').rstrip(':')
                    val_after = stripped[len(prefix):].strip()
                    current_value = [val_after] if val_after else []
                    break
            else:
                if current_field and stripped:
                    current_value.append(stripped)

        if current_field and current_value:
            val = '\n'.join(current_value).strip()
            if val and val != '(无)':
                if current_field in fields:
                    if isinstance(fields[current_field], list):
                        fields[current_field].append(val)
                    else:
                        fields[current_field] = [fields[current_field], val]
                else:
                    fields[current_field] = val

        if case_id and case_id not in seen_ids:
            seen_ids.add(case_id)
            fields['case_id'] = case_id
            cases.append(fields)

    return cases

def classify_category(case_id):
    if case_id.startswith('A'): return 'non_dialogue'
    if case_id.startswith('B'): return 'non_dialogue'
    if case_id.startswith('C'): return 'dialogue'
    if case_id.startswith('D'): return 'unknown_speaker'
    if case_id.startswith('E'): return 'dialogue'
    if case_id.startswith('F'): return 'non_dialogue'
    return 'unknown'

def convert_to_unified(cases):
    unified = []
    
    for c in cases:
        case_id = c['case_id']
        category = classify_category(case_id)
        
        context = c.get('旁白上下文', '')
        post_context = c.get('旁白后文', '')
        if isinstance(context, list): context = context[0] if context else ''
        if isinstance(post_context, list): post_context = post_context[0] if post_context else ''
        
        # Build full paragraph
        paragraph_parts = [context]
        dialogue_content = c.get('对话内容', '')
        expected_speaker_raw = c.get('期望说话人', '')
        if isinstance(expected_speaker_raw, list): expected_speaker_raw = expected_speaker_raw[0] if expected_speaker_raw else ''
        pitfall = c.get('易错点', '')
        if isinstance(pitfall, list): pitfall = pitfall[0] if pitfall else ''
        
        # Parse dialogue content - might be a JSON array string like ["a", "b"] or a single string
        dialogue_texts = []
        if dialogue_content:
            # Handle case where dialogue_content became a list due to duplicate fields
            if isinstance(dialogue_content, list):
                dialogue_content = dialogue_content[0] if dialogue_content else ''
            # Try to parse as JSON array
            dc = dialogue_content.strip()
            if dc.startswith('['):
                try:
                    import json
                    dialogue_texts = json.loads(dc)
                except:
                    dialogue_texts = [dc]
            else:
                # Split by quoted segments
                quoted_parts = re.findall(r'"([^"]*)"', dc)
                if quoted_parts:
                    dialogue_texts = quoted_parts
                else:
                    dialogue_texts = [dc]
        
        # Parse expected speakers
        expected_speakers = []
        if expected_speaker_raw:
            es = expected_speaker_raw.strip()
            # Check if it's a JSON-like list format: [item1, item2, ...]
            if es.startswith('[') and es.endswith(']'):
                try:
                    # Try standard JSON first
                    expected_speakers = json.loads(es)
                except json.JSONDecodeError:
                    # Manual split for non-standard format like [郭垣, 孙项明, 郭垣, 孙项明]
                    inner = es[1:-1]
                    # Split by commas, but be careful with nested brackets
                    parts = []
                    depth = 0
                    current = ''
                    for ch in inner:
                        if ch in '（(':
                            depth += 1
                        elif ch in '）)':
                            depth -= 1
                        if ch == ',' and depth == 0:
                            parts.append(current.strip())
                            current = ''
                        else:
                            current += ch
                    if current.strip():
                        parts.append(current.strip())
                    expected_speakers = [p.strip().strip('"').strip("'") for p in parts if p.strip()]
            elif '、' in es or (',' in es and '旁白' not in es and '（' not in es):
                parts = re.split(r'[、,]', es)
                expected_speakers = [p.strip() for p in parts if p.strip()]
            else:
                expected_speakers = [es]
        
        # Build paragraph with embedded quotes
        full_paragraph = context
        if dialogue_texts:
            for dt in dialogue_texts:
                if dt not in full_paragraph:
                    quoted = f'"{dt}"'
                    if not post_context:
                        full_paragraph += quoted
                    else:
                        full_paragraph += ' ' + quoted
        
        if post_context:
            full_paragraph += post_context
        
        # Build dialogues list
        dialogues = []
        for i, dt in enumerate(dialogue_texts):
            spk = expected_speakers[i] if i < len(expected_speakers) else expected_speakers[-1] if expected_speakers else '未知'
            
            # Normalize speaker values
            if '旁白' in spk or '非对话' in spk:
                spk = '旁白（非对话）'
            elif spk in ('(无)', '无'):
                spk = '未知'
            elif '未知角色' in spk or '未知' in spk:
                spk = '未知'
            elif '（或' in spk:
                # Extract the first/primary option before "（或"
                spk = spk.split('（或')[0].strip()
            elif '（未具名' in spk:
                # Extract the primary before description
                spk = spk.split('（未具名')[0].strip()
            # Remove commentary after speaker name (e.g. "萧炎，其中..." → "萧炎")
            if '，其中' in spk:
                spk = spk.split('，其中')[0].strip()
            # Handle "speaker，commentary-with-quotes" patterns
            if '为同一角色' in spk or '与"' in spk or '与\u201c' in spk:
                # Split on Chinese comma, take first part
                parts = spk.split('，', 1)
                spk = parts[0].strip()
            
            dialogues.append({
                'text': dt,
                'speaker': spk
            })
        
        # If no dialogue content but there's a context, it's a pure non-dialogue test
        if not dialogue_texts and context:
            dialogues = []
        
        unified.append({
            'id': case_id,
            'source': 'new',
            'category': category,
            'paragraph': full_paragraph,
            'dialogues': dialogues,
            'note': pitfall,
        })
    
    return unified

if __name__ == '__main__':
    cases = parse_new_cases(r'd:\trae\novel-tts-engine\analysis_reports\新建 文本文档.txt')
    unified = convert_to_unified(cases)
    
    print(f"Parsed {len(cases)} unique cases from new test file")
    print(f"Converted to {len(unified)} unified entries")
    
    # Category stats
    from collections import Counter
    cats = Counter(c['category'] for c in unified)
    print(f"\nCategory distribution:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")
    
    # Count dialogues
    total_dialogues = sum(len(c['dialogues']) for c in unified)
    non_dialogue_count = sum(1 for c in unified if len(c['dialogues']) == 0)
    print(f"\nTotal unified entries: {len(unified)}")
    print(f"Total expected dialogues: {total_dialogues}")
    print(f"Non-dialogue test entries: {non_dialogue_count}")
    
    # Show a few samples
    print("\n--- Sample entries ---")
    for c in unified[:3]:
        print(f"\nID: {c['id']} | Category: {c['category']}")
        print(f"  Paragraph: {c['paragraph'][:100]}...")
        print(f"  Dialogues: {c['dialogues']}")
        print(f"  Note: {c['note']}")
    
    # Output as Python code
    output_path = r'd:\trae\novel-tts-engine\analysis_reports\评估脚本\new_cases_parsed.py'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('"""Parsed new test cases from 新建 文本文档.txt"""\n')
        f.write('NEW_TEST_CASES = [\n')
        for i, c in enumerate(unified):
            f.write('  {\n')
            f.write(f'    "id": {json.dumps(c["id"], ensure_ascii=False)},\n')
            f.write(f'    "source": "new",\n')
            f.write(f'    "category": {json.dumps(c["category"], ensure_ascii=False)},\n')
            f.write(f'    "paragraph": {json.dumps(c["paragraph"], ensure_ascii=False)},\n')
            f.write(f'    "dialogues": {json.dumps(c["dialogues"], ensure_ascii=False, indent=4).replace(chr(10), chr(10)+"    ")},\n')
            f.write(f'    "note": {json.dumps(c["note"], ensure_ascii=False)},\n')
            f.write('  },\n')
        f.write(']\n')
    
    print(f"\nWritten to: {output_path}")
