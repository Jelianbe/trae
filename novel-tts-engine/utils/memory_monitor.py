import psutil

def get_memory_usage() -> float:
    return psutil.Process().memory_info().rss / 1024 / 1024 / 1024

def check_memory_limit(limit_gb: float = 3.0) -> bool:
    return get_memory_usage() < limit_gb
