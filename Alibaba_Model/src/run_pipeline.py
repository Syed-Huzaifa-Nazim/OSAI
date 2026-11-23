"""Run download, EDA, training, validation, and an end-to-end comparison."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import ROOT


def run(skip_download=False, skip_train=False, device="auto"):
    steps = []
    if not skip_download:
        steps.append("01_download_amazon.py")
    steps.append("02_eda_and_preprocess.py")
    if not skip_train:
        steps.append("03_train_model.py")
    steps.extend(["04_validate_alibaba.py", "05_gap_inference.py"])
    for script in steps:
        command = [sys.executable, str(ROOT / "src" / script)]
        if script == "03_train_model.py":
            command += ["--device", device]
        print("Running", script, flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    args = parser.parse_args()
    run(args.skip_download, args.skip_train, args.device)

