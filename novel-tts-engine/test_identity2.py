import re

# Test the fixed regex
pattern1 = r'(?:对着|朝向|向着|跟着|对着|向着|跟|向|对)([\u4e00-\u9fa5]{2,4}?)(?:说道|问道|喊道|叫道|说|道|问|喊|叫|呼唤)'

test_cases = [
    '林轩推开客栈的门，对着掌柜说道',
    '掌柜抬头看了看他，笑道',
    '他对着黑衣人喊道',
]

print("=== Identity word extraction test ===")
for text in test_cases:
    matches = re.findall(pattern1, text)
    print(f"  '{text}' -> {matches}")
