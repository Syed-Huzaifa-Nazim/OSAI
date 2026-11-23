"""Verify a CDN interruption cannot duplicate or truncate JSONL rows."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


SOURCE = Path(__file__).resolve().parents[1] / "src/01_download_amazon.py"
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location("download_amazon", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response:
    def __init__(self, chunks, status):
        self.chunks = chunks
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield from self.chunks


class StreamResumeTest(unittest.TestCase):
    def test_resumes_at_complete_line(self):
        first = b'{"rating":1}\n'
        second = b'{"rating":2}\n'
        calls = []

        def get(url, headers, **kwargs):
            calls.append(headers)
            if len(calls) == 1:
                def broken():
                    yield first + second[:4]
                    raise requests.ConnectionError("interrupted")
                return Response(broken(), 200)
            return Response([second], 206)

        with patch.object(module.requests, "get", side_effect=get), patch.object(module.time, "sleep"):
            rows = list(module.stream_jsonl("https://example.test/data.jsonl"))
        self.assertEqual(rows, [{"rating": 1}, {"rating": 2}])
        self.assertEqual(calls[1]["Range"], f"bytes={len(first)}-")


if __name__ == "__main__":
    unittest.main()
