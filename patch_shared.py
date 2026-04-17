import sys

# Patch generate_protein.py
with open("drug_discovery/payloads/worker/scripts/generate_protein.py", "r") as f:
    content = f.read()

content = content.replace("abs_pdb_path = os.path.abspath(pdb_path)", """
    import shutil
    shared_dir = "/tmp/biotarget_shared"
    os.makedirs(shared_dir, exist_ok=True)
    shared_pdb = os.path.join(shared_dir, os.path.basename(pdb_path))
    shutil.copy(pdb_path, shared_pdb)
    abs_pdb_path = shared_pdb
""")

with open("drug_discovery/payloads/worker/scripts/generate_protein.py", "w") as f:
    f.write(content)
