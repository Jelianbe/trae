"""测试语音模式正则匹配"""
import re

test_cases = [
    ('药老捋了捋胡须："至少三万金币。"', '药老'),
    ('药老摇头道', '药老'),
    ('"萧炎，你太弱了！"药老摇头道。', '药老'),
    ('药老从戒指中飘出', '药老'),
    ('药老的声音在他脑海中响起', '药老'),
    ('萧炎看向药老', '药老'),
    ('药老看向萧炎', '药老'),
]

char_name = '药老'
patterns = [
    rf'{char_name}的声音',
    rf'{char_name}在脑海',
    rf'{char_name}心中',
    rf'{char_name}传音',
    rf'{char_name}从.+?(?:飘出|走出|走来|出现)',
    rf'{char_name}(?:的声音)?在.+?(?:响起|回荡)',
    rf'{char_name}看向.+?(?:道|说)',
    rf'{char_name}(?:.+?)?(?:捋了捋胡须|摇头|点头|叹息|叹气|笑道|冷冷道|沉声道)(?:.+?)?(?:道|说)',
    rf'{char_name}(?:.+?)?(?:道|说)：',
]

for text, expected in test_cases:
    print(f'文本: {text}')
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            print(f'  ✅ 匹配: {pattern[:40]}... -> {match.group()}')
    print()
