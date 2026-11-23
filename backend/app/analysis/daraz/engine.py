"""Daraz listing vs competitor listing: plain-language gaps that can raise search rank and sales.

The rule that keeps gaps concrete: RESULTS are never gaps. Rank, number sold, number of reviews and rating are
what a seller wants to raise; nobody can act on "get more reviews". They are shown in a "Where you stand" header.
Only LEVERS (things a seller can change: price, discount, badges, title, photos, description, options) can be gaps,
and a lever becomes a gap only when it passes all five checks:

  1. it is on the fixed lever list (LEVERS below, decided before any analysis);
  2. it is proven on Daraz jewellery data: inside each search word, listings with more / less of it rank higher or
     sell more, across the 25 words (Wilcoxon), corrected for testing many levers (Benjamini-Hochberg)
     -> models/daraz_evidence.json, built by Development/data_collection/daraz/test_effects.py;
  3. you are outside the normal range of the top 20 listings for your search word (outside their middle half);
  4. it comes with a concrete target (the top listings' typical value and range);
  5. it shows real top listings as examples.

What customers say comes from the review models (team model + our Model A, reviews.py): complaints in the competitor's reviews are openings for
you, even when your own listing has no reviews yet. Your own reviews are compared only from MIN_REVIEWS reviews up.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from scipy.stats import fisher_exact

from app.services import demo_data
from app.services.repository import new_id

logger = logging.getLogger("optistratix.analysis.daraz")

EVIDENCE = Path(__file__).parent / "models" / "daraz_evidence.json"
MIN_REVIEWS = 10      # fewer reviews than this on one side: reviews are not compared
MIN_GROUP = 3         # a reason needs at least 3 reviews to be shown (same convention as Instagram)
P_SHOWN, P_STRONG = 0.05, 0.01
CONFIDENCE = {"Low": 0.3, "Medium": 0.6, "High": 0.9}
STOP = {"for", "with", "and", "the", "of", "women", "girls", "set"}

# lever -> (gap kind, database category, plain title when it is a gap, what to do, how to show a value)
LEVERS: dict[str, dict[str, Any]] = {
    "price_vs_word": {"good": "Your price is lower than your competitor's", "kind": "daraz_price", "cat": "pricing", "title": "Your price is higher than most top listings",
                      "name": "price", "fmt": "rs"},
    "discount_pct": {"good": "A bigger discount than your competitor", "kind": "daraz_offer", "cat": "pricing", "title": "Show a bigger discount", "name": "discount", "fmt": "pct"},
    "has_discount": {"good": "You show a discount", "kind": "daraz_offer", "cat": "pricing", "title": "Show a discount on your price", "name": "a discount", "fmt": "yes"},
    "free_shipping": {"good": "You offer free shipping", "kind": "daraz_offer", "cat": "conversion", "title": "Offer free shipping", "name": "free shipping", "fmt": "yes"},
    "voucher": {"good": "You have a voucher", "kind": "daraz_offer", "cat": "conversion", "title": "Add a voucher", "name": "a voucher", "fmt": "yes"},
    "coins": {"good": "You offer a coins discount", "kind": "daraz_offer", "cat": "conversion", "title": "Join the Daraz coins discount", "name": "a coins discount", "fmt": "yes"},
    "daraz_choice": {"good": "You have the Daraz Choice badge", "kind": "daraz_offer", "cat": "conversion", "title": "Join Daraz Choice", "name": "the Daraz Choice badge", "fmt": "yes"},
    "title_words": {"good": "A more detailed title", "kind": "daraz_title", "cat": "seo", "title": "Write a longer, more detailed title", "name": "words in the title", "fmt": "n"},
    "title_has_search_word": {"good": "Your title has the search word", "kind": "daraz_title", "cat": "seo", "title": "Put the search word in your title", "name": "the search word in the title", "fmt": "yes"},
    "image_count": {"good": "More photos than your competitor", "kind": "daraz_photos", "cat": "content", "title": "Add more photos", "name": "photos", "fmt": "n"},
    "photo_worn": {"good": "Your main photo shows the jewellery worn", "kind": "daraz_photos", "cat": "content", "title": "Show the jewellery being worn in the main photo", "name": "a main photo showing it worn", "fmt": "yes"},
    "photo_face": {"good": "Your main photo shows a face", "kind": "daraz_photos", "cat": "content", "title": "Show a model's face in the main photo", "name": "a face in the main photo", "fmt": "yes"},
    "description_words": {"good": "A fuller description", "kind": "daraz_content", "cat": "content", "title": "Write a fuller description", "name": "words in the description", "fmt": "n"},
    "bullet_count": {"good": "More bullet points", "kind": "daraz_content", "cat": "content", "title": "Add bullet points to the description", "name": "bullet points", "fmt": "n"},
    "variant_count": {"good": "More colour / size options", "kind": "daraz_content", "cat": "positioning", "title": "Offer more colour or size options", "name": "colour / size options", "fmt": "n"},
}
TIPS = {
    "price_vs_word": "If your cost allows, bring your price into this range, or show a discount on your current price.",
    "discount_pct": "Show the original price and a discount in this range (Daraz shows it on the search page).",
    "has_discount": "Set an original price and a sale price, so Daraz shows a discount badge on the search page.",
    "free_shipping": "Turn on free shipping in Seller Center (or join a free-shipping campaign).",
    "voucher": "Create a store voucher in Seller Center; it shows as a badge on the search page.",
    "coins": "Join the Daraz coins programme in Seller Center.",
    "daraz_choice": "Check in Seller Center whether this product can join Daraz Choice.",
    "title_words": "Add the material, plating, style, occasion and what is included (for example: earrings + tikka).",
    "title_has_search_word": "Use the exact words buyers type, near the start of your title.",
    "image_count": "Add photos from more angles, worn on a model, close-ups of the stones, and the packaging.",
    "photo_worn": "Make the first photo a picture of the jewellery being worn.",
    "photo_face": "Use a main photo where the model's face is visible with the jewellery.",
    "description_words": "Describe the material, size, weight, plating, care and what comes in the box.",
    "bullet_count": "List the key facts as short bullet points: material, size, colour, what is included.",
    "variant_count": "Offer the same design in more colours or sizes as options on one listing.",
}


@lru_cache(maxsize=1)
def evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}


def available() -> bool:
    return bool(evidence().get("levers"))


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def candidate_words(title: str) -> list[str]:
    """Dataset search words whose meaningful words are all in the title, most specific first."""
    tw = set(_words(title))
    found = []
    for word in evidence().get("benchmarks", {}):
        if word.startswith("_"):
            continue
        need = [w for w in _words(word) if w not in STOP] or _words(word)
        if all(w in tw for w in need):
            found.append((len(need), len(_words(word)), word))
    return [w for *_, w in sorted(found, reverse=True)]


def pick_search_word(title: str) -> str | None:
    """The best-matching dataset search word for a title (the caller may prefer one where the listing ranks)."""
    words = candidate_words(title)
    return words[0] if words else None


#: The direction each lever's advice is written for, fixed before the analysis. A lever proven the OTHER way
#: (for example "a face in the main photo" going with fewer sales, seen in only 8 search words) is reported in the
#: thesis but never turned into advice.
EXPECTED = {key: ("less is better" if key == "price_vs_word" else "more is better") for key in LEVERS}


def proven(key: str) -> dict[str, Any] | None:
    """The lever's proven result (rank first, then sold), or None. Conflicting or unexpected directions are not used."""
    levers = evidence().get("levers", {})
    hits = [levers.get(f"{key}|{o}") for o in ("rank", "sold")]
    hits = [h for h in hits if h and h.get("proven") and h.get("direction") == EXPECTED.get(key)]
    if not hits or len({h["direction"] for h in hits}) > 1:
        return None
    return {**hits[0], "outcomes": [("rank higher" if h["outcome"] == "search rank" else "sell more") for h in hits]}


# ------------------------------------------------------------------ wording
def show(value: Any, fmt: str) -> str:
    if value is None:
        return "not known"
    if fmt == "yes":
        return "yes" if value else "no"
    if fmt == "rs":
        return f"Rs {value:,.0f}"
    if fmt == "pct":
        return f"{value:.0f}%"
    return f"{value:,.0f}"


def _why(ev: dict[str, Any], name: str) -> str:
    more = "more" if ev["direction"] == "more is better" else "less"
    if ev.get("kind") == "yesno":
        more = "with" if ev["direction"] == "more is better" else "without"
        lead = f"listings {more} {name}"
    elif name == "price":
        lead = "cheaper listings" if more == "less" else "more expensive listings"
    else:
        lead = f"listings with {more} {name}"
    return (f"On Daraz, for {ev['words_positive'] if ev['direction'] == 'more is better' else ev['words_tested'] - ev['words_positive']} "
            f"of {ev['words_tested']} jewellery search words, {lead} {' and '.join(ev['outcomes'])}.")


def _how(ev: dict[str, Any], where: str) -> list[str]:
    """Plain words for the screen; the statistics behind it are in the project report (data_collection/daraz)."""
    return [f"We studied 2,000 real Daraz search results: the top 80 listings for each of {ev['words_tested']} "
            "jewellery search words, with their rank and sales. This pattern held across most of those searches, "
            "so it is not chance.",
            f"Your listing is compared with the top 20 listings for {where} today: a gap is shown only when you are "
            "outside their usual range."]


def _display(name: str) -> str:
    """'a voucher' -> 'Voucher', 'words in the title' -> 'Words in the title'."""
    for lead in ("a ", "an ", "the "):
        if name.startswith(lead):
            name = name[len(lead):]
    return name[:1].upper() + name[1:]


def _picture_examples(top: list[dict[str, Any]], n: int = 3) -> list[dict[str, Any]]:
    """Top listings as picture examples for the card (same shape as an Instagram example post)."""
    out = []
    for r in top[:n]:
        if not r.get("item_url"):
            continue
        img = r.get("image") or ""
        out.append({"who": "competitor", "postUrl": r["item_url"],
                    "imageUrl": ("https:" + img) if img.startswith("//") else img, "date": None, "format": "image",
                    "likes": None, "comments": None,
                    "caption": f"#{r['rank']} for this search" + (f" · Rs {r['price']:,.0f}" if r.get("price") else "")
                               + f" · {r['name'][:80]}"})
    return out


def _gap(project_id: str, title: str, description: str, tip: str, category: str, how_sure: str,
         evidence_rows: list[dict[str, Any]], details: dict[str, Any]) -> dict[str, Any]:
    return {"id": new_id("gap"), "project_id": project_id, "title": title[:200], "description": description,
            "category": category, "priority": "medium", "confidence": CONFIDENCE[how_sure],
            "evidence": evidence_rows, "opportunity": tip, "decision": "pending", "created_at": demo_data.iso(),
            "details": {**details, "howSure": how_sure}}


def _examples(top: list[dict[str, Any]], n: int = 3) -> list[dict[str, Any]]:
    return [{"source_id": r["item_id"], "source_url": r["item_url"], "source_title": f"Rank {r['rank']} for this search",
             "quote": f"{r['name'][:120]} · Rs {r['price']:,.0f}" if r.get("price") else r["name"][:120], "relevance": 1.0}
            for r in top[:n] if r.get("item_url")]


# ------------------------------------------------------------------ main
def benchmark(word: str | None, live_top: list[dict[str, Any]]) -> dict[str, Any]:
    """Top-20 values: the search-row levers from the live results, the page levers from the dataset."""
    b = dict((evidence().get("benchmarks") or {}).get(word or "", {}) or (evidence().get("benchmarks") or {}).get("_all", {}))
    if len(live_top) >= 10:
        import numpy as np
        for key in ("discount_pct",):
            v = np.array([r[key] or 0 for r in live_top], dtype=float)
            b[key] = {"median": float(np.median(v)), "q1": float(np.quantile(v, .25)), "q3": float(np.quantile(v, .75)), "n": len(v)}
        for key in ("free_shipping", "voucher", "coins", "daraz_choice"):
            b[key] = {"share": sum(bool(r[key]) for r in live_top) / len(live_top), "n": len(live_top)}
        b["has_discount"] = {"share": sum((r["discount_pct"] or 0) > 0 for r in live_top) / len(live_top), "n": len(live_top)}
        prices = np.array([r["price"] for r in live_top if r.get("price")], dtype=float)
        if len(prices):
            b["price"] = {"median": float(np.median(prices)), "q1": float(np.quantile(prices, .25)), "q3": float(np.quantile(prices, .75))}
    return b


def analyze(project_id: str, me: dict[str, Any], rival: dict[str, Any], word: str | None,
            live: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """me / rival: one listing each (levers + results + analysed reviews). live: search results for `word`."""
    top = [r for r in live if r["rank"] <= 20 and not r.get("sponsored")]
    bench = benchmark(word, top)
    word_median_price = None
    if live:
        prices = sorted(r["price"] for r in live if r.get("price"))
        word_median_price = prices[len(prices) // 2] if prices else None
    for side in (me, rival):
        if side.get("price") and word_median_price:
            side["price_vs_word"] = side["price"] / word_median_price
        if word:
            need = [w for w in _words(word) if w not in STOP] or _words(word)
            side["title_has_search_word"] = all(w in _words(side.get("title")) for w in need)
        side.setdefault("title_words", len(_words(side.get("title"))))

    gaps: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    strengths: list[dict[str, Any]] = []
    where = f'"{word}"' if word else "similar jewellery"

    for key, spec in LEVERS.items():
        ev = proven(key)
        u, c = me.get(key), rival.get(key)
        b = bench.get(key)
        if ev is None or u is None or b is None:
            continue
        better = 1 if ev["direction"] == "more is better" else -1
        if spec["fmt"] == "yes":
            share = b.get("share", 0.0)
            you_short = (not u) if better == 1 else bool(u)
            market_does = share >= 0.5
            # "they do better" = your competitor has it and you do not (for a lever where having it helps)
            they_do = c is not None and ((bool(c) and not u) if better == 1 else (not c and bool(u)))
            typical = f"{share:.0%} have it"
            outside = you_short and (they_do or market_does)
            # ahead = you have it and your competitor does not (both having it is not a strength)
            ahead = (not you_short) and c is not None and ((not bool(c)) if better == 1 else bool(c))
        else:
            q1, q3, med = b["q1"], b["q3"], b["median"]
            if key == "price_vs_word" and word_median_price:
                p = bench.get("price") or {}
                typical = f"Rs {p.get('q1', q1 * word_median_price):,.0f} to Rs {p.get('q3', q3 * word_median_price):,.0f}"
                q1v, q3v = (p.get("q1") or q1 * word_median_price) / word_median_price, (p.get("q3") or q3 * word_median_price) / word_median_price
            else:
                typical = f"{show(q1, spec['fmt'])} to {show(q3, spec['fmt'])} (typical {show(med, spec['fmt'])})"
                q1v, q3v = q1, q3
            outside = (u < q1v) if better == 1 else (u > q3v)
            they_do = c is not None and ((c > u) if better == 1 else (c < u))
            ahead = c is not None and not outside and ((u > c) if better == 1 else (u < c))
        shown_u = show(me.get("price") if key == "price_vs_word" else u, spec["fmt"])
        shown_c = show(rival.get("price") if key == "price_vs_word" else c, spec["fmt"])
        row = {"key": key, "kind": spec["kind"], "title": spec["good"] if ahead else spec["title"], "you_text": shown_u, "competitor_text": shown_c,
               "typical": typical, "why": _why(ev, spec["name"]), "tip": TIPS[key]}
        if outside:
            sure = "High" if ev["p_corrected"] < P_STRONG else "Medium"
            title = spec["title"] + (": your competitor does better" if they_do else "")
            desc = (f"{_why(ev, spec['name'])} You: {shown_u}. Your competitor: {shown_c}. "
                    f"Top 20 listings for {where}: {typical}.")
            extra = ""
            if key == "title_has_search_word" and bench.get("title_words_majority"):
                extra = " Words most top titles use: " + ", ".join(bench["title_words_majority"][:8]) + "."
            gaps.append(_gap(project_id, title, desc + extra, "Try this: " + TIPS[key], spec["cat"], sure, _examples(top),
                             {"kind": spec["kind"], "market": not they_do,
                              "numbers": [{"label": _display(spec["name"]), "you": shown_u,
                                           "competitor": shown_c, "typical": typical}],
                              "examples": _picture_examples(top),
                              "technical": _how(ev, where)}))
            row["group"] = "do_more"
        elif ahead:
            # shown once, under "Where you're ahead" (not repeated in the check-up)
            strengths.append({"kind": spec["kind"], "label": spec["good"],
                              "detail": f"You: {shown_u}. Your competitor: {shown_c}. Top 20 listings: {typical}."})
            continue
        else:
            # within the usual range of the top listings: nothing to change, whatever the competitor does
            row["group"] = "fine"
            row["title"] = _display(spec["name"])
            row["why"] = ("Same as most of the top 20 listings, so no change is needed." if spec["fmt"] == "yes"
                          else "Within the usual range of the top 20 listings, so no change is needed.")
            row["tip"] = ""
        rows.append(row)

    r_gaps, r_info = _reviews(project_id, me, rival)
    gaps.extend(r_gaps)
    strengths.extend(r_info.pop("strengths", []))
    standing = {"search_word": word, "you": _standing(me), "competitor": _standing(rival),
                "top_listings": len(live)}
    if not any(g["details"]["kind"] != "daraz_reviews" for g in gaps):
        standing["note"] = ("Good news: your price, photos, options, title and offers are already as good as the top "
                            "listings. From here, rank grows mostly with more sales and good reviews over time.")
    return gaps, {"standing": standing, "comparison": rows, "strengths": strengths, "reviews": r_info,
                  "levers_proven": [k for k in LEVERS if proven(k)]}


def _standing(side: dict[str, Any]) -> dict[str, Any]:
    return {"rank": side.get("rank"), "sold": side.get("sold"), "reviews": side.get("review_count"),
            "rating": side.get("rating"), "price": side.get("price"), "title": side.get("title")}


# ------------------------------------------------------------------ what customers say
def _reason_counts(analysed: list[dict[str, Any]], polarity: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in analysed:
        for x in r.get("reasons", []):
            if x["polarity"] == polarity:
                out.setdefault(x["aspect"], []).append(r["review"])
    return out


NICE = {"Design_Comfort": "design and comfort", "As_Described": "matching the description", "Size_Capacity": "size",
        "Display_Camera": "display",
        # Model A (jewellery reasons)
        "colour_fade": "colour fading", "breakage": "breaking", "as_pictured": "not matching the photos",
        "wrong_or_missing": "wrong or missing items", "size_fit": "size", "comfort": "comfort (weight, allergy)",
        "price_value": "value for money", "design": "the design"}


#: What a seller can do when buyers complain about a reason (used for the competitor's complaints).
REASON_TIPS = {
    "wrong_or_missing": "Check the colour and number of pieces before sending, and write \"every order is checked before dispatch\" in your description.",
    "size_fit": "Give exact sizes (cm, ring size, length) in the title or description, and add a photo with a ruler or size chart.",
    "as_pictured": "Use real photos of the actual piece, not catalogue pictures, and say \"real pictures\" in your listing.",
    "colour_fade": "If your plating lasts, say so (for example anti-tarnish or gold-plated), and add care tips to the description.",
    "breakage": "Pack every piece firmly, and show close-ups of the hook, lock and stones in your photos.",
    "quality": "Show close-ups of the material and finishing, and name the material clearly in the title and description.",
    "comfort": "Mention the weight (light-weight) and that it is skin-friendly, if true.",
    "delivery": "Dispatch quickly and show the delivery time clearly.",
    "packaging": "Use a box and bubble wrap, and show your packaging in the last photo.",
    "seller": "Reply to buyer messages and reviews quickly and politely.",
    "price_value": "Show what is included and why it is worth the price, or add a small discount.",
    "design": "Show the design clearly from several angles.",
}


def _nice(aspect: str) -> str:
    return NICE.get(aspect, aspect.replace("_", " ").lower())


#: Size words or measurements in a title/description: the listing already answers "what size is it?".
SIZE_INFO = re.compile(r"\d+(\.\d+)?\s*(cm|mm|inch|inches|\")|\b(size|length|diameter|width|adjustable)\b", re.I)

#: The gap title when the competitor's buyers complain about something your listing does not answer either.
ANSWER_TITLE = {"size_fit": "Give the exact size in your listing"}


def _listing_answers(side: dict[str, Any], aspect: str) -> bool | None:
    """Does this listing's title or description already answer the complaint? None = cannot be read from a listing."""
    text = f"{side.get('title') or ''} {side.get('description') or ''}"
    if aspect == "size_fit":
        return bool(SIZE_INFO.search(text))
    return None


def _listing_example(side: dict[str, Any], who: str) -> list[dict[str, Any]]:
    if not side.get("url"):
        return []
    return [{"who": who, "postUrl": side["url"], "imageUrl": side.get("image") or "", "date": None, "format": "image",
             "likes": None, "comments": None,
             "caption": ("Your listing" if who == "you" else "Your competitor's listing") + f" · {str(side.get('title') or '')[:80]}"}]


def _reviews(project_id: str, me: dict[str, Any], rival: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Review gaps are always about YOUR listing:
    1. your buyers complain about something more than your competitor's buyers do (Fisher test), or
    2. your competitor's buyers complain about something your own listing does not answer either (for example no
       size given). A competitor complaint you do not share is a strength, not a gap."""
    mine, theirs = me.get("analysed_reviews") or [], rival.get("analysed_reviews") or []
    enough_mine, enough_theirs = len(mine) >= MIN_REVIEWS, len(theirs) >= MIN_REVIEWS
    info: dict[str, Any] = {"you": len(mine), "competitor": len(theirs), "compared": enough_mine and enough_theirs}
    gaps: list[dict[str, Any]] = []
    strengths: list[dict[str, Any]] = []
    combined = any(r.get("reason_model") for r in mine + theirs)
    tech = ["We read the newest reviews (up to 40) of both listings with our review models: one says whether a review "
            "is happy or unhappy, the other what it is about (size, quality, delivery...)."
            + (" On 150 reviews checked by a person, about 4 in 5 of the complaints it found were right." if combined else "")]
    cu, cc = _reason_counts(mine, "negative"), _reason_counts(theirs, "negative")

    # 1. your own buyers, compared with your competitor's
    if info["compared"]:
        neg_u = sum(r["sentiment"] == "negative" for r in mine)
        neg_c = sum(r["sentiment"] == "negative" for r in theirs)
        p = float(fisher_exact([[neg_u, len(mine) - neg_u], [neg_c, len(theirs) - neg_c]], alternative="greater")[1])
        if p < P_SHOWN:
            gaps.append(_gap(
                project_id, "More of your reviews are unhappy than your competitor's",
                f"{neg_u} of your last {len(mine)} reviews are unhappy; {neg_c} of your competitor's last {len(theirs)}. "
                "Unhappy reviews lower the rating buyers see on the search page.",
                "Try this: read your unhappy reviews below, fix the most common problem, and reply to each one politely.",
                "social_engagement", "High" if p < P_STRONG else "Medium",
                [{"source_id": me.get("item_id") or "", "source_url": me.get("url") or "", "source_title": "Your review",
                  "quote": r["review"][:240], "relevance": 1.0} for r in mine if r["sentiment"] == "negative"][:3],
                {"kind": "daraz_reviews", "numbers": [{"label": "Unhappy reviews", "you": f"{neg_u} of {len(mine)}",
                                                        "competitor": f"{neg_c} of {len(theirs)}", "typical": None}],
                 "examples": _listing_example(me, "you"), "technical": tech}))
    if enough_mine:
        for aspect, texts in sorted(cu.items(), key=lambda kv: -len(kv[1])):
            k_c = len(cc.get(aspect, []))
            if len(texts) < MIN_GROUP:
                continue
            p = (float(fisher_exact([[len(texts), len(mine) - len(texts)], [k_c, len(theirs) - k_c]], alternative="greater")[1])
                 if enough_theirs else 1.0)
            if p >= P_SHOWN:
                # your own buyers say it, but not more often than your competitor's: worth fixing, not a proven gap
                theirs_part = (f" Your competitor's buyers say it about as often ({k_c} of {len(theirs)})."
                               if enough_theirs else "")
                gaps.append(_gap(
                    project_id, f"Some of your buyers complain about {_nice(aspect)}",
                    f"{len(texts)} of your last {len(mine)} reviews complain about {_nice(aspect)}.{theirs_part} "
                    "Fixing it can lift your rating above your competitor's.",
                    "Try this: " + REASON_TIPS.get(aspect, f"fix {_nice(aspect)} first."),
                    "positioning", "Low",
                    [{"source_id": me.get("item_id") or "", "source_url": me.get("url") or "", "source_title": "Your review",
                      "quote": t[:240], "relevance": 1.0} for t in texts[:3]],
                    {"kind": "daraz_reviews", "unproven": True,
                     "numbers": [{"label": f"Reviews about {_nice(aspect)}", "you": f"{len(texts)} of {len(mine)}",
                                  "competitor": f"{k_c} of {len(theirs)}" if enough_theirs else None, "typical": None}],
                     "examples": _listing_example(me, "you"), "technical": tech}))
                continue
            gaps.append(_gap(
                project_id, f"Your buyers complain about {_nice(aspect)}",
                f"{len(texts)} of your last {len(mine)} reviews complain about {_nice(aspect)}; only {k_c} of your "
                f"competitor's last {len(theirs)} do.",
                "Try this: " + REASON_TIPS.get(aspect, f"fix {_nice(aspect)} first; it is what your buyers mention most."),
                "positioning", "High" if p < P_STRONG else "Medium",
                [{"source_id": me.get("item_id") or "", "source_url": me.get("url") or "", "source_title": "Your review",
                  "quote": t[:240], "relevance": 1.0} for t in texts[:3]],
                {"kind": "daraz_reviews", "numbers": [{"label": f"Reviews about {_nice(aspect)}",
                                                        "you": f"{len(texts)} of {len(mine)}", "competitor": f"{k_c} of {len(theirs)}", "typical": None}],
                 "examples": _listing_example(me, "you"), "technical": tech}))

    # 2. your competitor's buyers: a gap only if your own listing does not answer it either
    if enough_theirs:
        for aspect, texts in sorted(cc.items(), key=lambda kv: -len(kv[1])):
            if len(texts) < MIN_GROUP:
                continue
            k_u = len(cu.get(aspect, []))
            if enough_mine:
                if k_u / len(mine) < len(texts) / len(theirs):
                    strengths.append({"kind": "daraz_reviews", "label": f"Fewer complaints about {_nice(aspect)}",
                                      "detail": f"{k_u} of your last {len(mine)} reviews, against {len(texts)} of your "
                                                f"competitor's last {len(theirs)}."})
                continue                                 # as many or more: part 1 already decides
            if _listing_answers(me, aspect) is not False:
                continue                                 # answered already, or nothing a listing can show
            gaps.append(_gap(
                project_id, ANSWER_TITLE.get(aspect, f"Answer {_nice(aspect)} in your listing"),
                f"{len(texts)} of your competitor's last {len(theirs)} reviews complain about {_nice(aspect)}, and your "
                f"title and description do not mention it. Buyers comparing the two listings pick the one that answers this.",
                "Try this: " + REASON_TIPS.get(aspect, f"say clearly how your listing handles {_nice(aspect)}."),
                "positioning", "Medium",
                [{"source_id": rival.get("item_id") or "", "source_url": rival.get("url") or "", "source_title": "Competitor's buyer",
                  "quote": t[:240], "relevance": 1.0} for t in texts[:3]],
                {"kind": "daraz_reviews", "numbers": [{"label": f"Reviews about {_nice(aspect)}",
                                                        "you": "not mentioned in your listing", "competitor": f"{len(texts)} of {len(theirs)} complain", "typical": None}],
                 "examples": _listing_example(rival, "competitor"), "technical": tech}))
    if not enough_mine:
        info["note"] = (f"You have {len(mine)} review{'s' if len(mine) != 1 else ''} we could read; your own reviews are "
                        f"compared once you have {MIN_REVIEWS}.")
    info["praise"] = {a: len(t) for a, t in _reason_counts(theirs, "positive").items() if len(t) >= MIN_GROUP}
    info["strengths"] = strengths
    return gaps, info
