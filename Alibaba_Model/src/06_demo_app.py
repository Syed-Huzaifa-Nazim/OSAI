"""Paste two attached-review listing payloads for a presentation demo."""
from __future__ import annotations

import argparse
import json

from common import load_predictor
from importlib import import_module

# Numeric script names are loaded by path rather than normal Python imports.
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("gap_inference", Path(__file__).with_name("05_gap_inference.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
AlibabaGapAnalyzer = module.AlibabaGapAnalyzer
reviews = module.reviews
pain_points = module.pain_points


def compare(own_json, competitor_json):
    own, competitor = json.loads(own_json), json.loads(competitor_json)
    analyzer = AlibabaGapAnalyzer(load_predictor())
    gaps = analyzer.compare(own, competitor)
    return {"own_review_count": len(reviews(own)), "competitor_review_count": len(reviews(competitor)),
            "own_pain_points": pain_points(reviews(own)), "competitor_pain_points": pain_points(reviews(competitor)),
            "gaps_opportunities": gaps}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--own", help="Own product JSON file")
    parser.add_argument("--competitor", help="Competitor product JSON file")
    args = parser.parse_args()
    if args.cli:
        if not args.own or not args.competitor:
            parser.error("--cli requires --own and --competitor")
        print(json.dumps(compare(Path(args.own).read_text(), Path(args.competitor).read_text()), indent=2))
    else:
        import gradio as gr
        with gr.Blocks() as demo:
            gr.Markdown("# Alibaba gap analysis\nPaste two `ecommerce_products` JSON records with attached reviews.")
            own = gr.Code(label="Own listing JSON", language="json")
            competitor = gr.Code(label="Competitor listing JSON", language="json")
            output = gr.JSON(label="Grounded gaps")
            gr.Button("Compare").click(compare, [own, competitor], output)
        demo.launch()

