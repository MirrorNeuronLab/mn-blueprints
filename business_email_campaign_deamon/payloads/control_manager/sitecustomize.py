from pathlib import Path
import sys

skills_dir = Path(__file__).resolve().parent / "mn_skills"
if skills_dir.exists():
    sys.path.insert(0, str(skills_dir))

shared_skills_dir = Path(__file__).resolve().parent.parent / "_shared_skills"
if shared_skills_dir.exists():
    sys.path.insert(0, str(shared_skills_dir))
