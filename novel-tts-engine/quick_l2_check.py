import sys, os
sys.path.insert(0, '.')
from pipeline.semantic_ranker import get_semantic_ranker, reset_semantic_ranker

reset_semantic_ranker()
ranker = get_semantic_ranker(enable_l2=True)
ranker.load_model()
print(f"L2 available: {ranker.is_available()}")
print(f"Backend: {ranker._backend}")
