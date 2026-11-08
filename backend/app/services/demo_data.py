"""Seeded demo dataset: "Verdant Roast", a fictional speciality coffee brand.

PLACEHOLDER CONTENT. Every string here is written by hand, not scraped and not
model-generated. It exists so the full nine-stage pipeline can be walked end to
end with no live scraping and no LLM spend, which is what makes the system
demonstrable in a defence.

The competitor names and URLs are invented and use the reserved ``.example``
TLD; they are not real businesses.

This mirrors ``frontend/src/lib/mock/demo-data.ts``. Keep the two in step.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

DEMO_PROJECT_ID = "demo-verdant-roast"
DEMO_USER_ID = "demo-user-0001"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime | None = None) -> str:
    return (moment or _now()).isoformat()


def _days_ago(days: int) -> str:
    return iso(_now() - timedelta(days=days))


def _minutes_ago(minutes: int) -> str:
    return iso(_now() - timedelta(minutes=minutes))


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------- project


def demo_project() -> dict[str, Any]:
    return {
        "id": DEMO_PROJECT_ID,
        "owner_id": DEMO_USER_ID,
        "brand_name": "Verdant Roast",
        "brand_website": "https://verdantroast.example",
        "brand_description": (
            "Small-batch speciality coffee roaster selling direct to consumers and to "
            "independent cafes, with a subscription tier and a single flagship storefront."
        ),
        "industry": "ecommerce",
        "target_audience": (
            "Urban home-brewing enthusiasts aged 25-40 who buy whole bean monthly, plus "
            "independent cafe owners sourcing wholesale."
        ),
        "objectives": [
            "Grow direct subscription revenue",
            "Win share of voice against larger regional roasters",
            "Convert cafe wholesale enquiries faster",
        ],
        "status": "awaiting_review",
        "current_stage": 5,
        "competitor_count": 3,
        "gap_count": 7,
        "is_demo": True,
        "created_at": _days_ago(6),
        "updated_at": _minutes_ago(12),
    }


def demo_competitors() -> list[dict[str, Any]]:
    return [
        {
            "id": "demo-comp-1",
            "project_id": DEMO_PROJECT_ID,
            "name": "Northbrew Coffee Co.",
            "landing_page_url": "https://northbrew.example",
            "social_handles": [
                {"platform": "instagram", "handle": "@northbrewco"},
                {"platform": "tiktok", "handle": "@northbrew"},
            ],
            "notes": "Largest regional player. Heavy paid social spend.",
            "created_at": _days_ago(6),
        },
        {
            "id": "demo-comp-2",
            "project_id": DEMO_PROJECT_ID,
            "name": "Meridian Beans",
            "landing_page_url": "https://meridianbeans.example",
            "social_handles": [
                {"platform": "instagram", "handle": "@meridianbeans"},
                {"platform": "linkedin", "handle": "meridian-beans"},
            ],
            "notes": "Strong wholesale/B2B motion, weak consumer brand.",
            "created_at": _days_ago(6),
        },
        {
            "id": "demo-comp-3",
            "project_id": DEMO_PROJECT_ID,
            "name": "Ottoline Roasters",
            "landing_page_url": "https://ottoline.example",
            "social_handles": [
                {"platform": "instagram", "handle": "@ottolineroasters"},
                {"platform": "youtube", "handle": "@ottoline"},
            ],
            "notes": "Editorial content leader. Publishes brew guides weekly.",
            "created_at": _days_ago(6),
        },
    ]


# ---------------------------------------------------------- stage 2/3 sources

#: Source templates the mock Scout returns. ``competitor_index`` maps onto
#: whichever competitors the project actually declared.
_SOURCE_TEMPLATES: list[dict[str, Any]] = [
    {
        "competitor_index": 0,
        "kind": "landing_page",
        "path": "/subscribe",
        "title": "{competitor} - Subscription landing page",
        "excerpt": (
            "Choose your grind, choose your cadence. Skip, pause or cancel any time. Free "
            "shipping over $35. 14,000 subscribers and counting."
        ),
        "chunk_count": 24,
    },
    {
        "competitor_index": 2,
        "kind": "landing_page",
        "path": "/guides/v60",
        "title": "{competitor} - The V60 brew guide",
        "excerpt": (
            "A 1,900-word illustrated guide covering grind size, bloom timing, and water "
            "temperature, with an embedded four-minute video walkthrough."
        ),
        "chunk_count": 41,
    },
    {
        "competitor_index": 0,
        "kind": "social_post",
        "path": "/p/harvest-origin",
        "title": "{competitor} - Harvest origin reel (Instagram)",
        "excerpt": (
            "Reel showing the Huila harvest with farmer interviews. 42k views, 3.1k likes, "
            "180 comments - their best-performing post of the quarter."
        ),
        "chunk_count": 6,
    },
    {
        "competitor_index": 1,
        "kind": "landing_page",
        "path": "/wholesale",
        "title": "{competitor} - Wholesale enquiry page",
        "excerpt": (
            "Wholesale pricing tiers published openly, with a downloadable spec sheet and a "
            "24-hour response guarantee on enquiries."
        ),
        "chunk_count": 18,
    },
    {
        "competitor_index": None,
        "kind": "review",
        "path": "https://reviews.example/{brand_slug}",
        "title": "Customer reviews - {brand}",
        "excerpt": (
            "Recurring theme across 62 reviews: customers love the product but repeatedly ask "
            '"which one should I buy?" and mention the site is hard to navigate.'
        ),
        "chunk_count": 62,
    },
    {
        "competitor_index": None,
        "kind": "forum_thread",
        "path": "https://forum.example/thread/regional-roasters",
        "title": "Forum thread - Best in the category?",
        "excerpt": (
            "Thread with 240 replies. The two category leaders are named 31 and 27 times "
            "respectively; {brand} is mentioned twice, both times favourably."
        ),
        "chunk_count": 33,
    },
    {
        "competitor_index": 2,
        "kind": "news_article",
        "path": "https://trade-news.example/content-studio-raise",
        "title": "Trade press - {competitor} raises to expand content studio",
        "excerpt": (
            "{competitor} is doubling its editorial team, citing organic search as its "
            "lowest-cost acquisition channel at roughly a third of paid social."
        ),
        "chunk_count": 12,
    },
]


def build_sources(project_id: str, competitors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What the mock Scout Agent 'collects'.

    Templates are bound to the project's real competitor rows so titles, URLs
    and ``competitor_id`` references all resolve in the UI.
    """
    brand = "the brand"
    sources: list[dict[str, Any]] = []

    for template in _SOURCE_TEMPLATES:
        index = template["competitor_index"]
        competitor: dict[str, Any] | None = None
        if index is not None and competitors:
            competitor = competitors[index % len(competitors)]

        competitor_name = competitor["name"] if competitor else brand
        base_url = (
            competitor.get("landing_page_url", "https://competitor.example")
            if competitor
            else "https://reviews.example"
        )
        path: str = template["path"]
        url = path if path.startswith("http") else f"{base_url.rstrip('/')}{path}"

        sources.append(
            {
                "id": _new_id("src"),
                "project_id": project_id,
                "competitor_id": competitor["id"] if competitor else None,
                "kind": template["kind"],
                "url": url.format(brand_slug="brand"),
                "title": template["title"].format(competitor=competitor_name, brand=brand),
                "excerpt": template["excerpt"].format(competitor=competitor_name, brand=brand),
                "status": "embedded",
                "chunk_count": template["chunk_count"],
                "scraped_at": iso(),
            }
        )

    return sources


# ------------------------------------------------------------- stage 4 gaps

_GAP_TEMPLATES: list[dict[str, Any]] = [
    {
        "title": "No educational content, while the category leader publishes weekly",
        "description": (
            "A competitor runs a weekly long-form guide series that ranks on the highest-intent "
            "informational queries in the category. This brand publishes no educational content "
            "at all, so it is absent from the search results where buyers first form a preference."
        ),
        "category": "content",
        "priority": "critical",
        "confidence": 0.91,
        "opportunity": (
            "A focused guide series targeting the same query cluster, differentiated by tying "
            "each guide to a specific product."
        ),
        "source_indices": [1, 6],
    },
    {
        "title": "Subscription value proposition is not stated on the landing page",
        "description": (
            "The leading competitor leads with flexibility - skip, pause, cancel - and social "
            "proof in the form of subscriber count. This brand mentions its subscription only in "
            "footer navigation, with no terms, cadence options or reassurance above the fold."
        ),
        "category": "conversion",
        "priority": "critical",
        "confidence": 0.88,
        "opportunity": (
            "A dedicated subscription page carrying cadence options, the cancellation policy, "
            "and review-sourced social proof."
        ),
        "source_indices": [0],
    },
    {
        "title": "Buyers cannot tell which product to choose",
        "description": (
            "The single most repeated theme across 62 customer reviews is uncertainty about "
            "which product to buy. No comparison table or guided finder exists on the site, so "
            "the decision is left entirely to the customer."
        ),
        "category": "conversion",
        "priority": "high",
        "confidence": 0.86,
        "opportunity": "A three-question product finder plus a comparison table on every product page.",
        "source_indices": [4],
    },
    {
        "title": "Origin storytelling is absent from social",
        "description": (
            "A competitor's best-performing content of the quarter was a farm-origin reel with "
            "supplier interviews. This brand sources from comparable suppliers but publishes only "
            "product photography, forfeiting the highest-engagement format in the category."
        ),
        "category": "social_engagement",
        "priority": "high",
        "confidence": 0.82,
        "opportunity": (
            "A recurring origin series built from existing supplier relationships, at low "
            "production cost."
        ),
        "source_indices": [2],
    },
    {
        "title": "Wholesale pricing is gated while a competitor publishes it openly",
        "description": (
            "A competitor publishes wholesale tiers and a downloadable spec sheet, and commits "
            "publicly to a 24-hour response. This brand requires a contact form with no pricing "
            "indication, filtering out buyers comparing options before making contact."
        ),
        "category": "pricing",
        "priority": "high",
        "confidence": 0.79,
        "opportunity": (
            "Publish indicative tier pricing and a spec sheet; keep the enquiry form for volume "
            "negotiation only."
        ),
        "source_indices": [3],
    },
    {
        "title": "Negligible share of voice in category discussion",
        "description": (
            "In the largest category discussion thread, the two leaders are named 31 and 27 "
            "times; this brand twice. Both mentions are positive, which suggests the constraint "
            "is awareness rather than sentiment."
        ),
        "category": "positioning",
        "priority": "medium",
        "confidence": 0.74,
        "opportunity": (
            "Community participation, supported by the educational content from the first gap."
        ),
        "source_indices": [5],
    },
    {
        "title": "No email capture beyond checkout",
        "description": (
            "Every competitor analysed runs a newsletter with a first-order incentive. This "
            "brand captures an address only at the point of purchase, so non-converting traffic "
            "is lost entirely."
        ),
        "category": "audience",
        "priority": "medium",
        "confidence": 0.71,
        "opportunity": "A guide-gated email capture, reusing the content from the first gap.",
        "source_indices": [0],
    },
]


def build_gaps(project_id: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What the mock Insight Agent 'finds'.

    Evidence is bound to the project's real source rows, so every citation in
    the UI links to something that exists.
    """
    gaps: list[dict[str, Any]] = []

    for template in _GAP_TEMPLATES:
        evidence: list[dict[str, Any]] = []
        for position, source_index in enumerate(template["source_indices"]):
            if not sources:
                break
            source = sources[source_index % len(sources)]
            evidence.append(
                {
                    "source_id": source["id"],
                    "source_url": source["url"],
                    "source_title": source["title"],
                    "quote": source["excerpt"],
                    "relevance": round(0.94 - position * 0.06, 2),
                }
            )

        gaps.append(
            {
                "id": _new_id("gap"),
                "project_id": project_id,
                "title": template["title"],
                "description": template["description"],
                "category": template["category"],
                "priority": template["priority"],
                "user_priority": None,
                "confidence": template["confidence"],
                "evidence": evidence,
                "opportunity": template["opportunity"],
                "decision": "pending",
                "reviewer_note": None,
                "created_at": iso(),
            }
        )

    return gaps


# ------------------------------------------------------- stage 6 strategy

_INITIATIVE_TEMPLATES: list[dict[str, Any]] = [
    {
        "match": "content",
        "title": "Launch a weekly guide series tied to specific products",
        "rationale": (
            "A competitor has proven the format converts in this category and has stated organic "
            "search costs it roughly a third of paid social. Entering the same query cluster with "
            "guides tied to specific products differentiates on the one axis a competitor cannot "
            "copy - the product itself."
        ),
        "actions": [
            "Pull the 20 highest-volume informational queries for the region and cluster them.",
            "Publish one 1,200-1,800 word guide per week, each anchored to one product.",
            "Embed a short video walkthrough in the top four guides; phone-shot is sufficient.",
            "Add an inline email capture offering the full guide set as a PDF.",
            "Review ranking movement at week 8 and reallocate to the winning cluster.",
        ],
        "channel": "Organic search / owned content",
        "effort": "high",
        "expected_impact": (
            "Entry into the informational query cluster that currently sends zero traffic; "
            "compounding rather than paid-dependent."
        ),
        "timeline_weeks": 12,
    },
    {
        "match": "conversion",
        "title": "Build a dedicated subscription page that states the offer",
        "rationale": (
            "The subscription is currently discoverable only from the footer. The leading "
            "competitor leads with flexibility and subscriber-count social proof, and its "
            "subscription page is its primary conversion surface."
        ),
        "actions": [
            "Create /subscribe with cadence options and the cancellation policy stated plainly.",
            "Pull three review quotes about product quality as social proof.",
            "Add the subscription entry point to primary navigation and every product page.",
            "Instrument the funnel so drop-off between page view and first order is measurable.",
        ],
        "channel": "Website / conversion",
        "effort": "medium",
        "expected_impact": "Removes the discoverability barrier on the highest-value revenue line.",
        "timeline_weeks": 4,
    },
    {
        "match": "social_engagement",
        "title": "Run a monthly origin story series on social",
        "rationale": (
            "Origin content was a competitor's highest-engagement post of the quarter, and this "
            "brand already holds the supplier relationships needed to produce it."
        ),
        "actions": [
            "Identify two suppliers willing to be filmed this quarter.",
            "Produce one reel per month: on-site footage plus a short supplier interview.",
            "Cross-post to a second platform; link each reel to the matching product.",
            "Track saves and shares rather than likes - they predict purchase intent better here.",
        ],
        "channel": "Organic social",
        "effort": "medium",
        "expected_impact": (
            "Enters the highest-engagement format in the category using assets already available."
        ),
        "timeline_weeks": 8,
    },
    {
        "match": "audience",
        "title": "Add a guide-gated email capture and welcome sequence",
        "rationale": (
            "Non-converting traffic is currently lost entirely. The guide series produces an "
            "asset worth trading an email address for, so the two initiatives compound."
        ),
        "actions": [
            "Offer the collected guides as a single PDF behind an email capture.",
            "Write a three-email welcome sequence ending on a first-order offer.",
            "Report open and conversion rates monthly.",
        ],
        "channel": "Email",
        "effort": "low",
        "expected_impact": "Captures demand that currently leaves without a trace.",
        "timeline_weeks": 3,
    },
    {
        "match": "pricing",
        "title": "Publish indicative wholesale pricing",
        "rationale": (
            "A competitor publishes tiers openly and commits to a 24-hour response. Gating price "
            "filters out buyers who are still comparing, which is most of them."
        ),
        "actions": [
            "Publish indicative tier pricing and a downloadable spec sheet.",
            "Keep the enquiry form for volume negotiation only.",
            "Track enquiry volume before and after, and review at week 6.",
        ],
        "channel": "Website / B2B",
        "effort": "low",
        "expected_impact": "Reduces friction for buyers who compare before making contact.",
        "timeline_weeks": 2,
    },
]

#: A deliberately unfundable initiative. The mock Critic rejects it whenever no
#: budget is declared, which is what gives the transparency panel something
#: real to show in a demo.
_PAID_INITIATIVE: dict[str, Any] = {
    "match": "positioning",
    "title": "Launch a paid retargeting programme across social",
    "rationale": "Retarget visitors who did not convert on the subscription page.",
    "actions": [
        "Set a $4,000 monthly budget across two platforms.",
        "Build audiences from site visitors in the last 30 days.",
        "Rotate three creative variants.",
    ],
    "channel": "Paid social",
    "effort": "high",
    "expected_impact": "Paid retargeting will increase subscription conversion.",
    "timeline_weeks": 6,
}


def build_strategy_draft(
    project_id: str,
    project: dict[str, Any],
    accepted_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    """The Strategist's first draft, before the Critic sees it.

    Initiatives are selected by matching templates against the categories of the
    gaps the human actually accepted, so a reviewer who drops everything except
    pricing gets a pricing strategy rather than a fixed script.
    """
    accepted_categories = {gap.get("category") for gap in accepted_gaps}
    brand = project.get("brand_name", "the brand")

    initiatives: list[dict[str, Any]] = []
    for template in _INITIATIVE_TEMPLATES:
        if template["match"] not in accepted_categories:
            continue
        linked = [gap["id"] for gap in accepted_gaps if gap.get("category") == template["match"]]
        initiatives.append(
            {
                "id": _new_id("init"),
                "title": template["title"],
                "rationale": template["rationale"],
                "actions": list(template["actions"]),
                "channel": template["channel"],
                "effort": template["effort"],
                "expected_impact": template["expected_impact"],
                "timeline_weeks": template["timeline_weeks"],
                "linked_gap_ids": linked,
                "revised_from_draft": False,
            }
        )

    # Always include the paid initiative so the Critic has something to reject
    # when no budget was declared. This is the mock making its own behaviour
    # visible, not a recommendation.
    initiatives.append(
        {
            "id": _new_id("init"),
            "title": _PAID_INITIATIVE["title"],
            "rationale": _PAID_INITIATIVE["rationale"],
            "actions": list(_PAID_INITIATIVE["actions"]),
            "channel": _PAID_INITIATIVE["channel"],
            "effort": _PAID_INITIATIVE["effort"],
            "expected_impact": _PAID_INITIATIVE["expected_impact"],
            "timeline_weeks": _PAID_INITIATIVE["timeline_weeks"],
            "linked_gap_ids": [],
            "revised_from_draft": False,
        }
    )

    if not initiatives:
        initiatives.append(
            {
                "id": _new_id("init"),
                "title": "Close the accepted gaps in priority order",
                "rationale": (
                    "The accepted gaps did not match any templated initiative, so this is a "
                    "generic placeholder. A live Strategist would generate against the gaps "
                    "directly."
                ),
                "actions": ["Review the accepted gaps and sequence them by effort."],
                "channel": "Mixed",
                "effort": "medium",
                "expected_impact": "Addresses whatever the reviewer prioritised.",
                "timeline_weeks": 6,
                "linked_gap_ids": [gap["id"] for gap in accepted_gaps],
                "revised_from_draft": False,
            }
        )

    return {
        "title": f"{brand} - Competitive Recovery Strategy",
        "executive_summary": (
            f"{brand} competes on product quality but loses on discoverability and decision "
            f"support. Analysis identified gaps across {len(accepted_categories)} categories, of "
            f"which the reviewer prioritised {len(accepted_gaps)}. The initiatives below address "
            "those directly, weighted toward owned channels because no paid budget was declared "
            "at intake."
        ),
        "initiatives": initiatives,
        "addressed_gap_ids": [gap["id"] for gap in accepted_gaps],
    }


# ------------------------------------------------------ stage 8/9 templates


def build_document_sections(
    project: dict[str, Any],
    gaps: list[dict[str, Any]],
    strategy: dict[str, Any],
    reviews: list[dict[str, Any]],
    source_count: int,
) -> list[dict[str, Any]]:
    """Assembles the stage-8 document from what the run actually produced."""
    brand = project.get("brand_name", "The brand")
    accepted = [gap for gap in gaps if gap.get("decision") == "accepted"]
    initiatives = strategy.get("initiatives", [])
    feedback = strategy.get("critic_feedback", [])
    major = [item for item in feedback if item.get("severity") == "major"]
    revised = [item for item in initiatives if item.get("revised_from_draft")]

    return [
        {
            "id": "sec-summary",
            "order": 1,
            "heading": "Executive Summary",
            "body": strategy.get("executive_summary", ""),
        },
        {
            "id": "sec-position",
            "order": 2,
            "heading": "Competitive Position",
            "body": (
                f"{project.get('competitor_count', 0)} competitors were analysed across "
                f"{source_count} sources. The analysis identified {len(gaps)} gaps between "
                f"{brand} and that competitor set, spanning "
                f"{len({gap.get('category') for gap in gaps})} categories."
            ),
        },
        {
            "id": "sec-gaps",
            "order": 3,
            "heading": "Prioritised Gaps",
            "body": (
                f"The reviewer accepted {len(accepted)} of {len(gaps)} gaps at the first human "
                "checkpoint. Accepted gaps: "
                + ("; ".join(gap["title"] for gap in accepted) or "none")
                + "."
            ),
        },
        {
            "id": "sec-initiatives",
            "order": 4,
            "heading": "Strategic Initiatives",
            "body": (
                f"{len(initiatives)} initiatives were generated by the Strategist and reviewed by "
                f"the Critic, which logged {len(feedback)} interventions ({len(major)} major) and "
                f"materially revised {len(revised)}. "
                + " ".join(
                    f"{index + 1}. {item['title']} ({item['channel']}, {item['timeline_weeks']} weeks)."
                    for index, item in enumerate(initiatives)
                )
            ),
        },
        {
            "id": "sec-plan",
            "order": 5,
            "heading": "Implementation Plan",
            "body": (
                "Sequenced by effort so the cheapest wins land first: "
                + " ".join(
                    f"{item['title']} - {item['timeline_weeks']} weeks ({item['effort']} effort)."
                    for item in sorted(
                        initiatives,
                        key=lambda entry: {"low": 0, "medium": 1, "high": 2}.get(
                            entry.get("effort", "medium"), 1
                        ),
                    )
                )
            ),
        },
        {
            "id": "sec-validation",
            "order": 6,
            "heading": "Validation Trail",
            "body": (
                f"Every claim in this document traces to one of {source_count} collected sources, "
                f"cited inline in the insights view. {len(reviews)} human review"
                f"{'' if len(reviews) == 1 else 's'} were recorded: "
                + (
                    "; ".join(
                        f"stage {review['stage']} - {review['decision']}" for review in reviews
                    )
                    or "none"
                )
                + f". The Critic logged {len(feedback)} interventions against the first draft."
            ),
        },
    ]


_SUGGESTION_TEMPLATES: list[dict[str, Any]] = [
    {
        "kind": "blog",
        "title": "How-to guide anchored to your flagship product",
        "angle": (
            "First entry in the weekly series. Anchors a method to a specific product rather "
            "than staying generic."
        ),
        "target_keywords": ["how to guide", "beginner walkthrough"],
        "channel": "Blog / organic search",
        "estimated_effort_hours": 6,
    },
    {
        "kind": "seo_brief",
        "title": "SEO brief for the commercial-intent query cluster",
        "angle": "Commercial-intent cluster feeding the new conversion page.",
        "target_keywords": ["best subscription", "compare options"],
        "channel": "Organic search",
        "estimated_effort_hours": 3,
    },
    {
        "kind": "social_post",
        "title": "Origin reel with a supplier interview",
        "angle": "Matches the format that outperformed everything else on the competitor account.",
        "target_keywords": [],
        "channel": "Instagram / TikTok",
        "estimated_effort_hours": 8,
    },
    {
        "kind": "email",
        "title": "Welcome sequence triggered by the guide download",
        "angle": "Three emails ending on a first-order offer.",
        "target_keywords": [],
        "channel": "Email",
        "estimated_effort_hours": 4,
    },
    {
        "kind": "ad_copy",
        "title": "Search ad variants for the product finder",
        "angle": (
            "Three variants for when a paid budget exists. Held back deliberately - the Critic "
            "rejected paid spend this quarter."
        ),
        "target_keywords": ["which product", "product finder"],
        "channel": "Paid search",
        "estimated_effort_hours": 2,
    },
]


def build_suggestions(project_id: str, strategy: dict[str, Any]) -> list[dict[str, Any]]:
    """Stage 9: maps content assets onto the approved initiatives."""
    initiatives = strategy.get("initiatives", [])
    suggestions: list[dict[str, Any]] = []

    for index, template in enumerate(_SUGGESTION_TEMPLATES):
        linked = initiatives[index % len(initiatives)]["id"] if initiatives else None
        suggestions.append(
            {
                "id": _new_id("sug"),
                "project_id": project_id,
                "kind": template["kind"],
                "title": template["title"],
                "angle": template["angle"],
                "linked_initiative_id": linked,
                "target_keywords": list(template["target_keywords"]),
                "channel": template["channel"],
                "estimated_effort_hours": template["estimated_effort_hours"],
                "status": "dismissed" if template["kind"] == "ad_copy" else "suggested",
                "body": None,
                "created_at": iso(),
            }
        )

    return suggestions


def draft_suggestion_body(suggestion: dict[str, Any]) -> str:
    """Placeholder body for a drafted asset."""
    keywords = ", ".join(suggestion.get("target_keywords") or []) or "Not applicable"
    return "\n".join(
        [
            f"# {suggestion['title']}",
            "",
            f"**Angle.** {suggestion['angle']}",
            "",
            f"**Channel.** {suggestion['channel']}",
            "",
            f"**Target keywords.** {keywords}",
            "",
            "---",
            "",
            "This is placeholder copy from the demo generator. In a live run the Scalability",
            "Agent drafts this against the approved strategy and the retrieved competitor",
            "corpus, citing the same evidence trail used earlier in the pipeline.",
        ]
    )


def demo_pipeline_state(project_id: str, source_count: int, gap_count: int) -> dict[str, Any]:
    """The demo project's pipeline, pre-run up to the first human checkpoint.

    Stages 1-4 are complete and stage 5 is awaiting a person, which is the state
    worth opening on: it shows the pipeline stopped, waiting, exactly as the
    trust story describes.
    """

    def stage(
        stage_id: int,
        status: str,
        *,
        message: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        done = status == "complete"
        return {
            "id": stage_id,
            "status": status,
            "progress": 100 if done else 0,
            "started_at": _days_ago(1) if status != "idle" else None,
            "completed_at": _days_ago(1) if done else None,
            "message": message,
            "error": None,
            "metrics": metrics,
        }

    def metrics(items: int, ms: int, tokens: int | None, cost: float | None) -> dict[str, Any]:
        return {
            "items_processed": items,
            "duration_ms": ms,
            "tokens_used": tokens,
            "cost_usd": cost,
        }

    stages = {
        "1": stage(1, "complete", metrics=metrics(3, 0, None, None)),
        "2": stage(
            2,
            "complete",
            message=f"{source_count} sources collected",
            metrics=metrics(source_count, 184_000, 42_100, 0.421),
        ),
        "3": stage(
            3,
            "complete",
            message="196 chunks embedded into the project collection",
            metrics=metrics(196, 96_000, 61_400, 0.184),
        ),
        "4": stage(
            4,
            "complete",
            message=f"{gap_count} gaps identified",
            metrics=metrics(gap_count, 71_000, 38_900, 0.583),
        ),
        "5": stage(
            5,
            "awaiting_human",
            message="Waiting for you to prioritise the identified gaps",
        ),
        "6": stage(6, "idle"),
        "7": stage(7, "idle"),
        "8": stage(8, "idle"),
        "9": stage(9, "idle"),
    }

    return {
        "project_id": project_id,
        "current_stage": 5,
        "stages": stages,
        "blocked_on": 5,
        "updated_at": _minutes_ago(12),
    }


def demo_integrations() -> list[dict[str, Any]]:
    """Registry rows standing in for teammates' separately-built modules."""
    return [
        {
            "id": "int-1",
            "feature_key": "seo-audit",
            "name": "SEO Audit Module",
            "description": (
                "Teammate-built module. Runs a technical SEO audit against the brand site and "
                "folds the findings into the gap list."
            ),
            "status": "available",
            "connected_at": None,
            "config": None,
        },
        {
            "id": "int-2",
            "feature_key": "social-scheduler",
            "name": "Social Scheduler",
            "description": (
                "Teammate-built module. Pushes approved stage-9 content assets into a posting "
                "calendar."
            ),
            "status": "available",
            "connected_at": None,
            "config": None,
        },
        {
            "id": "int-3",
            "feature_key": "sentiment-tracker",
            "name": "Review Sentiment Tracker",
            "description": (
                "Teammate-built module. Continuous sentiment scan over review sources, feeding "
                "the Insight Agent."
            ),
            "status": "coming_soon",
            "connected_at": None,
            "config": None,
        },
    ]
