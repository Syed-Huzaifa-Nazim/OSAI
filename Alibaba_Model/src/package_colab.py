"""Build the self-contained folder ZIP accepted by train_colab_t4.ipynb."""
from __future__ import annotations

from zipfile import ZIP_DEFLATED, ZipFile

from common import ROOT


def run():
    target = ROOT / "alibaba_colab_upload.zip"
    includes = [ROOT / "config.yaml", ROOT / "requirements.txt", ROOT / "README.md", ROOT / "Models_detail.md"]
    includes += list((ROOT / "src").glob("*.py"))
    includes += list((ROOT / "data/alibaba_validation").glob("*.csv"))
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in includes:
            archive.write(path, arcname=f"Alibaba_Model/{path.relative_to(ROOT).as_posix()}")
    return target


if __name__ == "__main__":
    print(run())
