import sys
import types

# Mock drugclip
sys.modules['drugclip'] = types.ModuleType('drugclip')
sys.modules['drugclip.utils'] = types.ModuleType('drugclip.utils')
m = types.ModuleType('drugclip.utils.chemistry')

def mock_smiles_to_schnet_data(sm, return_dict=False):
    import numpy as np
    num_atoms = 5
    return {
        "z": np.random.randint(1, 10, size=(num_atoms,)),
        "pos": np.random.randn(num_atoms, 3)
    }

m.smiles_to_schnet_data = mock_smiles_to_schnet_data
sys.modules['drugclip.utils.chemistry'] = m

sys.path.append("/Users/homer/Projects/BioTarget")

from biotarget.stages.stage_c_generative import stage_c_generative_ai

class DummyDrugCLIP:
    def text_encoder(self, texts):
        import torch
        return torch.randn(len(texts), 128)
    def graph_encoder(self, z, pos, batch):
        import torch
        num_graphs = batch.max().item() + 1
        return torch.randn(num_graphs, 128)

print("Starting test...")
cands, graphs = stage_c_generative_ai("Alzheimer", DummyDrugCLIP(), "cpu", 5)
print(f"Generated {len(cands)} candidates.")
