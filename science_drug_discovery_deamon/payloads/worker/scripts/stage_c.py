#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
import random

sys.path.append("/Users/homer/Projects/BioTarget")
from extract_utils import extract_payload


def get_seed_smiles():
    return [
        "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
        "C1=CC=C(C=C1)S(=O)(=O)N",  # Benzenesulfonamide
        "CCOc1ccc(CC(=O)N(C)O)cc1",  # Ibuprofen-like
        "CCC1(CC)Cc2ccccc2-c2nc(NCCO)[nH]c(=O)c21",
        "CCCCCCCCCCCCCCCBr",
        "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C",  # Testosterone
    ]


def load_message():
    return json.loads(Path(os.environ["MIRROR_NEURON_MESSAGE_FILE"]).read_text())


def main():
    message = load_message()
    payload = extract_payload(message)
    disease = payload.get("disease", "Alzheimer")
    targets = payload.get("targets", [])
    structures = payload.get("structures", [])

    print(f"[*] Stage C: Generating candidates for {disease}", file=sys.stderr)

    # Select 3 random smiles to represent generated candidates since drugclip is mock
    candidates = random.sample(get_seed_smiles(), 3)

    print(
        json.dumps(
            {
                "disease": disease,
                "targets": targets,
                "structures": structures,
                "candidates": candidates,
            }
        )
    )


if __name__ == "__main__":
    main()
