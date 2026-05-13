"""测试说话动词模式匹配"""
import re

test_cases = [
    '药老捋了捋胡须：',
    '药老摇头道。',
    '萧炎点头道：',
    '药老笑道：',
    '林雪拍了一下桌子。',
    '"萧炎，你太弱了！"药老摇头道。',
]

speech_pattern = r'([\u4e00-\u9fa5]{2,4})(?:道|说道|问|答道|喊|叫)(?:[，,。.!！?？：:]|$)'

for text in test_cases:
    match = re.search(speech_pattern, text)
    if match:
        print(f'MATCH: "{text}" -> name={match.group(1)} full={match.group()}')
    else:
        print(f'NO MATCH: "{text}"')
