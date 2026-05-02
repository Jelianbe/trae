def evaluate_speaker_matcher(text, gt_dialogue_speakers, char_manager):
    """使用真实 SpeakerMatcher 管道，按顺序评估，集成L2语义排序"""
    from pipeline.semantic_ranker import get_semantic_ranker
    
    # 初始化L2语义排序器
    semantic_ranker = get_semantic_ranker(enable_l2=True)
    semantic_ranker.load_model()
    matcher = SpeakerMatcher(
        character_manager=char_manager,
        semantic_ranker=semantic_ranker,
        l2_threshold=0.55,
    )
    
    # 按章节分段处理
    lines = text.split('\n')
    current_chapter = 0
    prev_speaker = None
    correct = 0
    total = 0
    
    gt_map = {}
    for item in gt_dialogue_speakers:
        text_key = item["text"][:30]
        gt_map[text_key] = item["speaker"]
    
    chapter_lines = []
    
    def process_chapter(ch_lines, chapter_id):
        nonlocal correct, total, prev_speaker
        for line_text in ch_lines:
            line_text = line_text.strip()
            if not line_text:
                continue
            if '\u201c' not in line_text and '"' not in line_text and "'" not in line_text and '\u201d' not in line_text:
                continue
            
            gt_speaker = None
            for key, speaker in gt_map.items():
                if key in line_text:
                    gt_speaker = speaker
                    break
            if not gt_speaker:
                continue
            
            total += 1
            ctx = DialogueContext(
                text=line_text,
                chapter_id=chapter_id,
                prev_speaker=prev_speaker
            )
            result = matcher.match_speaker(ctx)
            matched_name = result.character.name if result else None
            
            if matched_name == gt_speaker:
                correct += 1
                prev_speaker = matched_name
            else:
                prev_speaker = gt_speaker
    
    for line in lines:
        if re.match(r'(?:第[一二三四五六七八九十\d]+[章节回卷]|#{1,6}\s*第[一二三四五六七八九十\d]+[章节回卷])', line):
            if chapter_lines:
                process_chapter(chapter_lines, current_chapter)
                current_chapter += 1
                chapter_lines = []
        chapter_lines.append(line)
    
    if chapter_lines:
        process_chapter(chapter_lines, current_chapter)
    
    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)