import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipeline.speaker_hint_matcher import _LEFT_QUOTES, _RIGHT_QUOTES, DIALOGUE_PATTERNS

print("LEFT_QUOTES:")
for c in _LEFT_QUOTES:
    print(f"  U+{ord(c):04X}")

print("RIGHT_QUOTES:")
for c in _RIGHT_QUOTES:
    print(f"  U+{ord(c):04X}")

# Check pattern 0
pat = DIALOGUE_PATTERNS[0]
txt = 'a"b"c'  # simple test
matches = list(pat.finditer(txt))
print(f"\nSimple test 'a\"b\"c': {len(matches)} matches")

# Test with U+201C chars
txt2 = 'a\u201cb\u201dc'
matches2 = list(pat.finditer(txt2))
print(f"Test with U+201C: {len(matches2)} matches")

# Test with actual text from test data
from test_data_v6 import TEST_PARAGRAPHS
p1 = TEST_PARAGRAPHS[0]['paragraph']
matches3 = list(pat.finditer(p1))
print(f"P1 test: {len(matches3)} matches")
