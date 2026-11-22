"""A computer-vision network used as the "eye" for pictures and video frames.

Why a network at all: simple measurements (sharpness, light, colour) capture only part of what makes a picture
look good or memorable. A convolutional network (ResNet) reads the actual content and texture.

Why it is pre-trained: a vision network learns to see from millions of photos. KonIQ-10k has about 10,000
pictures and LSVQ about 39,000 videos (we have 4 batches), far too few to teach a network to see from nothing.
So the network that was already trained on general photos (ImageNet) is used only as a fixed feature reader,
the standard approach in quality research (the KonIQ-10k authors did the same). Everything that turns those
features into a quality or memorability score is trained by us, on people's ratings (train_common.py).

The network is read at several depths: early layers respond to blur, noise and exposure, later layers to content.
Which network (ResNet-18 or ResNet-50) and which layers are used is not assumed: training reads all four layers
and compares the layer sets in LAYER_SETS on the choosing (validation) set; the winner is saved with the model.
Pictures are shrunk to `max_side` pixels on the long side but not cropped, because cropping would hide framing.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

#: backbone -> (torchvision name, ImageNet weights, channels of layer1..layer4)
BACKBONES = {
    "resnet50": ("resnet50", "IMAGENET1K_V2", (256, 512, 1024, 2048)),
    "resnet18": ("resnet18", "IMAGENET1K_V1", (64, 128, 256, 512)),
}
ALL_LAYERS = ("layer1", "layer2", "layer3", "layer4")
DEFAULT_LAYERS = ("layer2", "layer3", "layer4")
#: the layer sets compared on the choosing set when a model is trained (train_common.py)
LAYER_SETS = [("layer4",), ("layer3", "layer4"), ("layer2", "layer3", "layer4"), ALL_LAYERS]
_cache: dict[tuple, "Extractor"] = {}


def _channels(backbone: str, layer: str) -> int:
    return BACKBONES[backbone][2][ALL_LAYERS.index(layer)]


def image_dim(backbone: str, layers=DEFAULT_LAYERS) -> int:
    """Length of one picture's vector: mean and spread of every channel of every layer read."""
    return 2 * sum(_channels(backbone, l) for l in layers)


def columns(backbone: str, have=ALL_LAYERS, want=DEFAULT_LAYERS, video: bool = False) -> np.ndarray:
    """Which columns of a vector read with layers `have` belong to layers `want`.

    A picture's vector is, layer by layer, [mean of each channel, spread of each channel]. A video's vector is
    [mean over frames of the picture vector, spread over frames of it], so the same columns are taken from both halves.
    """
    idx, start = [], 0
    for layer in have:
        size = 2 * _channels(backbone, layer)
        if layer in want:
            idx.extend(range(start, start + size))
        start += size
    idx_arr = np.array(idx, dtype=int)
    return np.concatenate([idx_arr, idx_arr + start]) if video else idx_arr


def available() -> bool:
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


class Extractor:
    """Turns a picture into one list of numbers: mean and spread of three layers of the network."""

    def __init__(self, backbone: str = "resnet50", max_side: int = 512, pretrained: bool = True, layers=DEFAULT_LAYERS):
        import torch
        import torchvision
        from torchvision.models.feature_extraction import create_feature_extractor

        name, weights, _ = BACKBONES[backbone]
        torch.manual_seed(0)                                   # a network built without weights must be the same every time
        model = getattr(torchvision.models, name)(weights=weights if pretrained else None).eval()
        self.layers = tuple(l for l in ALL_LAYERS if l in layers)   # always in network order
        self.net = create_feature_extractor(model, {l: l for l in self.layers})
        self.torch = torch
        self.max_side = max_side
        self.dim = image_dim(backbone, self.layers)
        self.mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

    def _prepare(self, img: Image.Image):
        im = img.convert("RGB")
        w, h = im.size
        scale = self.max_side / max(w, h)
        im = im.resize((max(32, round(w * scale)), max(32, round(h * scale))), Image.BICUBIC)
        x = self.torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
        return (x - self.mean) / self.std

    def image_vector(self, img: Image.Image) -> np.ndarray:
        t = self.torch
        with t.no_grad():
            out = self.net(self._prepare(img))
            parts = []
            for key in self.layers:
                f = out[key]
                parts += [f.mean(dim=(2, 3)), f.std(dim=(2, 3), correction=0)]
            return t.cat(parts, dim=1)[0].numpy().astype(np.float32)

    def frames_vector(self, frames: list[Image.Image]) -> np.ndarray:
        """A video: the mean and the spread of its frames' vectors."""
        mat = np.stack([self.image_vector(f) for f in frames])
        return np.concatenate([mat.mean(axis=0), mat.std(axis=0)]).astype(np.float32)


def get_extractor(backbone: str, max_side: int, pretrained: bool = True, layers=DEFAULT_LAYERS) -> Extractor:
    key = (backbone, max_side, pretrained, tuple(l for l in ALL_LAYERS if l in layers))
    if key not in _cache:
        _cache[key] = Extractor(backbone, max_side, pretrained, key[3])
    return _cache[key]
