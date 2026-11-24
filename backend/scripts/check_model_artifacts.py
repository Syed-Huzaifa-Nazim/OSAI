"""Fail the image build when Daraz or Instagram weights are incomplete."""

from app.core.model_check import _files, _file_problem

for label, (path, minimum_size) in _files().items():
    problem = _file_problem(path, minimum_size)
    if problem:
        raise SystemExit(f"{label}: {problem}")
    print(f"Model artifact ready: {label}")
