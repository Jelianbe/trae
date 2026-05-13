import sys, re
sys.path.insert(0, '.')

# 测试修复后的身份词提取正则
pattern1 = r'(?:对着|朝向|向着|跟着|对着|向着|跟|向|对)([\u4e00-\u9fa5]{2,4})(?:说道|问道|喊道|叫道|说|道|问|喊|叫|呼唤)'

test_cases = [
    '林轩推开客栈的门，对着掌柜说道："来一间上房。"',
    '小翠端着茶走进书房，轻声道："小姐，该用茶了。"',
    '他对着黑衣人喊道："把东西交出来！"',
    '骑士队长向首领报告："前线战况紧急。"',
]

print("身份词提取正则测试（修复后）:")
for text in test_cases:
    matches = re.findall(pattern1, text)
    print(f"  {text[:50]}... -> {matches}")
