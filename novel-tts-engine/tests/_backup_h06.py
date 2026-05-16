import os
import shutil
from datetime import datetime

src_dir = r"d:\trae\novel-tts-engine"
backup_dir = os.path.join(src_dir, "backups", f"backup_H06_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

os.makedirs(backup_dir, exist_ok=True)

files_to_backup = [
    os.path.join("pipeline", "speaker_matcher.py"),
    os.path.join("utils", "config.py"),
    os.path.join("tests", "test_urban_long_text.py"),
    os.path.join("tests", "baseline_rules_speaker.py"),
]

for rel_path in files_to_backup:
    src_path = os.path.join(src_dir, rel_path)
    dst_path = os.path.join(backup_dir, os.path.basename(rel_path))
    shutil.copy2(src_path, dst_path)
    print(f"Copied: {rel_path}")

print(f"\nBackup created at: {backup_dir}")
