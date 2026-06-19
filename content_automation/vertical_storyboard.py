from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryboardFrame:
    template: str
    pattern: str
    role: str
    cue: str
    metric_value: str
    metric_label: str
    evidence: str
    story_point: str
    visual_metaphor: str
    contrast: str
    must_show: tuple[str, ...]
    avoid: tuple[str, ...]


def build_storyboard_frame(*, title: str, text: str, index: int) -> StoryboardFrame:
    joined = f"{title} {text}".lower()
    if _has_any(joined, ("exit", "экзит", "продать", "оценк", "valuation", "агрегатор", "х3", "x3", "x4", "x5")):
        return StoryboardFrame(
            template="valuation",
            pattern="asset_exit",
            role="payoff",
            cue="Exit math",
            metric_value="X3-5",
            metric_label="profit multiple",
            evidence="cashflow turns into asset value",
            story_point="The seller stops thinking only about monthly cashflow and sees the brand as an asset that can be sold.",
            visual_metaphor="A seller operations dashboard transforms into a buyer valuation board with annual profit multiplied into exit value.",
            contrast="daily operator grind vs sellable business asset",
            must_show=("annual profit", "x3-x5 multiple", "asset valuation", "buyer checklist", "exit readiness"),
            avoid=("random product photo", "generic office people", "empty chart"),
        )
    if _has_any(joined, ("cash", "кэш", "операцион", "устал", "daily", "ppc", "acos")):
        return StoryboardFrame(
            template="problem",
            pattern="operator_trap",
            role="problem reveal",
            cue="Operator trap",
            metric_value="CHECK",
            metric_label="hidden workload",
            evidence="busy work hides the real asset goal",
            story_point="The seller is stuck managing daily PPC, ACOS, stock, and cashflow instead of building enterprise value.",
            visual_metaphor="A first-person Amazon operator control board covered with daily tasks, red circles, and a blocked path toward asset value.",
            contrast="busy cashflow dashboard vs clear exit path",
            must_show=("PPC/ACOS task list", "cashflow widget", "inventory warning", "blocked asset-value lane"),
            avoid=("celebration scene", "abstract growth arrows", "dark command center"),
        )
    if _has_any(joined, ("$1", "exactly one dollar", "bump the price", "one dollar", "один доллар")):
        return StoryboardFrame(
            template="lever",
            pattern="price_lever",
            role="price move",
            cue="$1 price lever",
            metric_value="$1",
            metric_label="controlled bump",
            evidence="small move, measured risk",
            story_point="A tiny price move only works when the seller can see the margin lift and demand risk side by side.",
            visual_metaphor="A seller interface mockup where price changes from $23.99 to $24.99 while Buy Box, margin, and velocity stay visible.",
            contrast="blind price increase vs controlled measured lever",
            must_show=("before price", "after price", "Buy Box state", "margin calculator", "velocity signal"),
            avoid=("random discount tag", "unmeasured profit claim", "large headline inside image"),
        )
    if _has_any(joined, ("sales drop", "price sensitive", "demand", "velocity", "price", "цена", "спрос")):
        return StoryboardFrame(
            template="decision",
            pattern="demand_decision",
            role="decision point",
            cue="Demand reaction",
            metric_value="A/B",
            metric_label="price test",
            evidence="decision depends on measured response",
            story_point="A small operator move has to be judged by demand, velocity, conversion, and Buy Box signals.",
            visual_metaphor="A/B price-test screen with two outcomes, red break marker, green hold zone, and annotated Buy Box panel.",
            contrast="guessing price moves vs measured decision",
            must_show=("two price options", "velocity chart", "conversion rate", "Buy Box state", "stop/keep decision"),
            avoid=("random storefront", "unlabeled graph", "large headline inside image"),
        )
    if _has_any(joined, ("profit", "sku", "margin", "fba", "прибыл", "марж", "юнит", "unit")):
        return StoryboardFrame(
            template="proof",
            pattern="unit_economics",
            role="proof",
            cue="Margin check",
            metric_value="+$",
            metric_label="unit economics",
            evidence="proof beats theory",
            story_point="The point becomes credible when the viewer can see the unit economics and margin movement.",
            visual_metaphor="A marked-up SKU economics sheet with price, FBA fee, daily units, margin, and profit total connected by arrows.",
            contrast="surface revenue vs actual contribution margin",
            must_show=("SKU card", "selling price", "FBA fee", "margin percent", "daily units", "profit total"),
            avoid=("decorative dashboard", "people shaking hands", "fake brand logos"),
        )
    if _has_any(joined, ("system", "checklist", "систем", "подготов", "листинг", "бренд")):
        return StoryboardFrame(
            template="checklist",
            pattern="operator_checklist",
            role="operator checklist",
            cue="System checklist",
            metric_value="READY",
            metric_label="exit prep",
            evidence="systems make the asset sellable",
            story_point="The viewer needs a concrete checklist for turning listings and operations into a sellable brand system.",
            visual_metaphor="A first-person audit board: listing quality, reviews, SOPs, margins, inventory, and buyer diligence checked one by one.",
            contrast="loose listings vs buyer-ready system",
            must_show=("listing checklist", "review quality", "SOP status", "margin proof", "inventory health"),
            avoid=("generic todo list", "thin empty cards", "random warehouse"),
        )
    cues = ("Audit point", "Hidden lever", "Margin check", "Operator move", "Proof frame")
    return StoryboardFrame(
        template="analysis",
        pattern="audit_point",
        role="analysis",
        cue=cues[index % len(cues)],
        metric_value="CHECK",
        metric_label="operator signal",
        evidence="make the hidden lever visible",
        story_point="Make the practical Amazon operator consequence visible rather than merely illustrating the spoken sentence.",
        visual_metaphor="A first-person teardown of an Amazon seller screen with red annotations pointing to the hidden lever.",
        contrast="surface-level listing view vs expert teardown",
        must_show=("listing panel", "seller metric cards", "red annotations", "operator note"),
        avoid=("generic business people", "decorative filler", "dark dashboard"),
    )


def build_storyboard_image_prompt(
    *,
    frame: StoryboardFrame,
    title: str,
    subtitle: str,
    terms: list[str],
    language: str,
) -> str:
    text_rule = (
        "Do not include Russian text. Use short English UI labels, SKU tags, values, arrows, and object annotations only when they clarify the evidence."
        if language == "en"
        else "Use short Russian UI labels, SKU tags, values, arrows, and object annotations only when they clarify the evidence."
    )
    return (
        "Create a central square first-person Amazon interface teardown image for a vertical Amazon seller expert video. "
        "It will be placed inside an HTML/CSS Hyperframes card; Hyperframes adds the headline, metric chip, and evidence caption. "
        "Do not design a full poster, thumbnail, slide, or complete card. "
        "No big headline text, no subtitles, no logos, no watermarks, no social-media thumbnail copy. "
        f"{text_rule} "
        "The picture must advance the story, not merely decorate the sentence. "
        f"Storyboard role: {frame.role}. Story point: {frame.story_point} "
        f"Visual metaphor: {frame.visual_metaphor} Contrast to show: {frame.contrast}. "
        f"Must show: {', '.join(frame.must_show)}. Avoid: {', '.join(frame.avoid)}. "
        "Make it feel like the expert is showing a real screen or printed interface board from their point of view. "
        "Use realistic but generic Amazon-style product listing interfaces, seller dashboard modules, Buy Box panels, conversion cards, BSR charts, review stars, price blocks, trust-signal checklists, unit-economics panels, product thumbnails, and metric cards only when they serve the storyboard role. "
        "Add 2-4 useful moodboard-style annotations: red hand-drawn circle, arrow, bracket, underline, check mark, cross mark, or sticky-note callout. "
        "Make the image information-rich: include 4-7 small evidence details such as SKU card, Buy Box state, margin note, price tag, BSR line, conversion percentage, fee tier marker, trust checklist, review count, or before/after value. "
        "Keep the top-right and bottom edge visually clean for HTML overlays, but keep the main interface dense enough to teach something. "
        "Use a clean bright off-white workspace, light paper surfaces, pale gray UI cards, thin navy lines, realistic UI spacing, and muted red/orange annotation accents. "
        "Avoid dark dashboards, black blocks, heavy machinery, dense shadows, and cargo-heavy compositions. "
        "Make it feel practical, premium, editorial, realistic, and easy to scan, like a consultant marking up an Amazon seller screen. "
        f"Scene title for context only: {title}. Subtitle for context only: {subtitle}. Visual anchors: {', '.join(terms)}."
    )


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)
