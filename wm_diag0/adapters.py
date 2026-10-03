"""Own-backbone visual/temporal contracts. Production loader is blocked.

These adapters are executable with artificial codecs, not substitutes for
checkpoint-specific LeWM/DINO implementations. Real bindings require a successor.
"""
import numpy as np
from .core import Features, frozen, native_terminal_score


class ArtificialVisualAdapter:
    def __init__(self, contract, encoder, predictor, *, domain):
        if domain != 'artificial':
            raise PermissionError('Released-model adapter binding not authenticated')
        self.contract, self.encoder, self.predictor = contract, encoder, predictor

    def encode(self, visual_history):
        if len(visual_history) != self.contract.history_length:
            raise ValueError('Native visual history length')
        f = np.asarray(self.encoder(visual_history))
        if f.shape != self.contract.feature_shape:
            raise ValueError('Native feature layout, no patch collapse')
        return frozen(f)

    def predict(self, visual_history, bank, source_id):
        root = self.encode(visual_history)
        values = np.stack([self.predictor(root, c.actions, self.contract.positions)
                           for c in bank.candidates])
        f = Features(frozen(values), self.contract, bank.identity, source_id, 'predicted')
        f.validate(bank)
        return f

    def original_score(self, consequences, goal_features):
        if consequences.contract != self.contract or self.contract.native_score_id not in ('terminal_mse','terminal_sum'):
            raise ValueError('S0 must be checkpoint-native, explicitly bound')
        return native_terminal_score(consequences, goal_features)


class LeWMAdapter(ArtificialVisualAdapter):
    def __init__(self, contract, *args, **kwargs):
        if contract.backbone != 'lewm' or len(contract.feature_shape) != 1:
            raise ValueError('LeWM native vector contract')
        super().__init__(contract, *args, **kwargs)


class DinoWMAdapter(ArtificialVisualAdapter):
    def __init__(self, contract, *args, **kwargs):
        if contract.backbone != 'dinowm_noprop' or len(contract.feature_shape) != 2:
            raise ValueError('DINO native patch/feature contract')
        super().__init__(contract, *args, **kwargs)
