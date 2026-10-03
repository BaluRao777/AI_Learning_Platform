"""Runs the official diffusers SANA DreamBooth-LoRA trainer with a lower-memory image cache.

The official example (examples/dreambooth/train_dreambooth_lora_sana.py, diffusers v0.40.0)
converts every training image to a float32 tensor up front. For 3,803 images at 1024x1024
that is about 48 GB and the process was killed by the kernel OOM killer on the 62 GB
workstation. This wrapper changes nothing in the training loop, model, loss or optimiser:

  * the preloaded images are kept as uint8 tensors (4x smaller), and
  * the same ToTensor + Normalize([0.5], [0.5]) maths is applied per item when a batch is built.

Everything else is the unmodified official script, loaded from training/third_party/diffusers.
"""
import importlib.util
import os
import sys

from torchvision import transforms as tv_transforms

SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "third_party", "diffusers", "examples", "dreambooth", "train_dreambooth_lora_sana.py",
)


class _Uint8Transforms:
    """torchvision.transforms, except ToTensor keeps uint8 and Normalize is deferred."""

    def __getattr__(self, name):
        return getattr(tv_transforms, name)

    @staticmethod
    def ToTensor():
        return tv_transforms.PILToTensor()

    @staticmethod
    def Normalize(mean, std):
        return tv_transforms.Lambda(lambda tensor: tensor)


def main():
    spec = importlib.util.spec_from_file_location("official_sana_lora_trainer", SCRIPT)
    official = importlib.util.module_from_spec(spec)
    sys.modules["official_sana_lora_trainer"] = official
    spec.loader.exec_module(official)

    official.transforms = _Uint8Transforms()
    original_getitem = official.DreamBoothDataset.__getitem__

    def getitem(self, index):
        example = original_getitem(self, index)
        # ToTensor: uint8 -> float in [0, 1]; Normalize([0.5], [0.5]): (x - 0.5) / 0.5
        example["instance_images"] = example["instance_images"].float().div(255.0).sub(0.5).div(0.5)
        return example

    official.DreamBoothDataset.__getitem__ = getitem
    # The official script reads a module-level `args` (set in its __main__ block).
    official.args = official.parse_args()
    official.main(official.args)


if __name__ == "__main__":
    main()
