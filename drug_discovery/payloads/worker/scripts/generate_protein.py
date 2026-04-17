#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Make BioTarget available
sys.path.append("/Users/homer/Projects/BioTarget")

from extract_utils import extract_payload

from biotarget.stages.stage_a_discovery import stage_a_target_discovery
from biotarget.stages.stage_b_structure import stage_b_structure_generation

def load_message() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_MESSAGE_FILE"]).read_text())


def main():
    message = load_message()
    payload = extract_payload(message)
    
    disease = payload.get("disease", "Alzheimer")
    print(f"[*] Generating protein for disease: {disease}", file=sys.stderr)
    
    # Run BioTarget logic
    targets = stage_a_target_discovery(disease)
    
    # For speed, just take the top 1 target
    if not targets:
        print(f"[!] No targets found for {disease}", file=sys.stderr)
        sys.exit(1)
        
    top_target = targets[0]
    print(f"[*] Top target: {top_target['gene']} ({top_target['protein_id']})", file=sys.stderr)
    
    structures = stage_b_structure_generation([top_target], engine="openfold3")
    if not structures:
        print("[!] No structure generated", file=sys.stderr)
        sys.exit(1)
        
    structure = structures[0]
    pdb_path = structure["path"]
    
    # Ensure it's an absolute path so the next worker can find it
    # We are running locally, so resolving to absolute path is fine.
    # Actually, we should check if pdb_path is absolute. It is usually relative to cwd.
    # BioTarget saves to ./runs/structures/... so let's resolve it.
    
    import shutil
    shared_dir = "/tmp/biotarget_shared"
    os.makedirs(shared_dir, exist_ok=True)
    shared_pdb = os.path.join(shared_dir, os.path.basename(pdb_path))
    shutil.copy(pdb_path, shared_pdb)
    abs_pdb_path = shared_pdb

    
    # Prepare output payload
    output = {
        "disease": disease,
        "gene": structure.get("gene", "Unknown"),
        "pdb_path": abs_pdb_path
    }
    
    # We just print the JSON object as the output body.
    # MirrorNeuron `executor` will capture stdout and package it as the body of the output_message_type.
    # Actually, wait... MirrorNeuron expects `stdout` of an executor to either be raw text that gets put in `sandbox.stdout`, OR we can just `print(json.dumps(output))`.
    print(json.dumps(output))

if __name__ == "__main__":
    main()
