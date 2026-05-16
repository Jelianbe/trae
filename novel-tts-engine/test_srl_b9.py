from pipeline.nlp_basics import get_nlp
nlp = get_nlp()

r1 = nlp.extract_srl_arg0s('赵总监皱起眉头')
print(f'9.1: {r1}')
assert r1 == ['赵总监'], f'Expected ["赵总监"], got {r1}'

nlp._initialized = False
r2 = nlp.extract_srl_arg0s('赵总监')
print(f'9.2: {r2}')
assert r2 == [], f'Expected [], got {r2}'
nlp._initialized = True

r3 = nlp.extract_srl_arg0s('赵总监皱起眉头打开文件')
print(f'9.3: {r3}')

r5 = nlp.extract_srl_arg0s('')
print(f'9.5: {r5}')
assert r5 == []

print('变更9 全部通过')
