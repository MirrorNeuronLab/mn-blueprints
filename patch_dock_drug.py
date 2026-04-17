import sys
import re

with open("drug_discovery/payloads/worker/scripts/dock_drug.py", "r") as f:
    content = f.read()

# Add load_context
if "def load_context()" not in content:
    content = content.replace("def load_message() -> dict:", """def load_context() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_CONTEXT_FILE"]).read_text())

def load_message() -> dict:""")

# Replace the log writes
main_body = """    context = load_context()
    job_id = context.get("job_id", "unknown_job")
    out_dir = f"/tmp/mirror_neuron_{job_id}"
    os.makedirs(out_dir, exist_ok=True)
    
    docking_log_file = os.path.join(out_dir, "docking.log")
    best_drugs_file = os.path.join(out_dir, "best_drugs.txt")
"""

if "context = load_context()" not in content:
    content = content.replace("    message = load_message()", main_body + "    message = load_message()")

content = content.replace('with open("/tmp/docking.log", "a")', 'with open(docking_log_file, "a")')
content = content.replace('output_file = "/tmp/best_drugs.txt"', 'output_file = best_drugs_file')

with open("drug_discovery/payloads/worker/scripts/dock_drug.py", "w") as f:
    f.write(content)
