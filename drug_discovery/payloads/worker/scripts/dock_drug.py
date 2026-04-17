#!/usr/bin/env python3
import json
import os
import sys
import random
import types
from pathlib import Path

# Mock drugclip to avoid ModuleNotFoundError since we only need run_gnina
sys.modules['drugclip'] = types.ModuleType('drugclip')
from extract_utils import extract_payload

sys.modules['drugclip.utils'] = types.ModuleType('drugclip.utils')
m = types.ModuleType('drugclip.utils.chemistry')
m.smiles_to_schnet_data = lambda *args, **kwargs: None
sys.modules['drugclip.utils.chemistry'] = m

# Make BioTarget available
sys.path.append("/Users/homer/Projects/BioTarget")

from biotarget.stages.stage_d_evaluation import run_gnina

def load_context() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_CONTEXT_FILE"]).read_text())

def load_message() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_MESSAGE_FILE"]).read_text())


def get_seed_smiles():
    return [
        "CC(=O)OC1=CC=CC=C1C(=O)O", # Aspirin
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", # Caffeine
        "C1=CC=C(C=C1)S(=O)(=O)N", # Benzenesulfonamide
        "CCOc1ccc(CC(=O)N(C)O)cc1", # Ibuprofen-like
        "CCC1(CC)Cc2ccccc2-c2nc(NCCO)[nH]c(=O)c21", 
        "CCCCCCCCCCCCCCCBr",
        "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C" # Testosterone
    ]

def main():
    context = load_context()
    job_id = context.get("job_id", "unknown_job")
    out_dir = f"/tmp/mirror_neuron_{job_id}"
    os.makedirs(out_dir, exist_ok=True)
    
    docking_log_file = os.path.join(out_dir, "docking.log")
    best_drugs_file = os.path.join(out_dir, "best_drugs.txt")
    message = load_message()
    payload = extract_payload(message)
    
    disease = payload.get("disease", "Unknown")
    pdb_path = payload.get("pdb_path")
    gene = payload.get("gene", "Unknown")
    
    print(f"[*] Docking drug for {disease} ({gene}) against {pdb_path}", file=sys.stderr)
    
    if not pdb_path or not os.path.exists(pdb_path):
        print(f"[!] Invalid PDB path: {pdb_path}", file=sys.stderr)
        sys.exit(1)
        
    # Get 1 random seed SMILES
    smiles_list = get_seed_smiles()
    smiles = random.choice(smiles_list)
    
    print(f"[*] Selected SMILES: {smiles}", file=sys.stderr)
    
    # Run GNINA docking
    score, success = run_gnina(pdb_path, smiles)
    with open(docking_log_file, "a") as f: f.write(f"Docking Score: {score}, Success: {success}\n")
    print(f"[*] Docking Score: {score}, Success: {success}", file=sys.stderr)
    
    # Check score
    if success and score < -5.0: # Arbitrary good score threshold
        output_file = best_drugs_file
        with open(output_file, "a") as f:
            f.write(f"Disease: {disease}, Gene: {gene}, PDB: {pdb_path}, SMILES: {smiles}, Score: {score}\n")
        print(f"[*] Saved good molecule to {output_file}", file=sys.stderr)
    
    # Prepare output payload to trigger the next round
    output = {
        "disease": disease
    }
    
    print(json.dumps(output))

if __name__ == "__main__":
    main()
