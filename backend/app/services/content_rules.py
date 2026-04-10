"""Content Rules — AI 티 방지 + 홍보성 필터링.

Two layers:
1. PROMPT_RULES: injected into the Claude prompt to prevent AI-isms at generation time
2. validate_content(): post-generation check that catches anything Claude still produces
"""
import re
import logging

logger = logging.getLogger(__name__)

# ─── AI tells: patterns that scream "this was written by AI" ────────────────

# Characters and patterns to auto-replace
AI_TELL_REPLACEMENTS = {
    "—": " - ",         # em-dash → regular dash (the #1 AI tell)
    "–": "-",           # en-dash → hyphen
    "\u200b": "",       # zero-width space
    "…": "...",         # unicode ellipsis → three dots (more human)
}

# Phrases that are dead giveaways for AI-generated content
AI_TELL_PHRASES = [
    # Structure / filler
    r"\bIn this (article|post|guide)\b",
    r"\bIn conclusion\b",
    r"\bLet'?s dive (in|into)\b",
    r"\bWithout further ado\b",
    r"\bIt'?s worth noting\b",
    r"\bAt the end of the day\b",
    r"\bMoving forward\b",
    r"\bThat being said\b",
    r"\bHaving said that\b",
    r"\bIt goes without saying\b",
    r"\bWhether you'?re a .+ or a .+\b",
    r"\bIn today'?s .+ landscape\b",
    r"\bIn the (ever-evolving|rapidly changing)\b",
    r"\bLook no further\b",
    r"\bBuckle up\b",
    r"\bFasten your seatbelts?\b",

    # Overused transitions
    r"\bFurthermore\b",
    r"\bMoreover\b",
    r"\bAdditionally\b",
    r"\bConsequently\b",
    r"\bNevertheless\b",

    # Hype / marketing
    r"\bA game[- ]?changer\b",
    r"\bRevolutioniz(e|es|ed|ing)\b",
    r"\bTransformativ(e|ely)\b",
    r"\bUnleash(es|ed|ing)?\b",
    r"\bEmpower(s|ed|ing)?\b",
    r"\bSeamless(ly)?\b",
    r"\bCutting[- ]?edge\b",
    r"\bNext[- ]?gen(eration)?\b",
    r"\bBest[- ]?in[- ]?class\b",
    r"\bState[- ]?of[- ]?the[- ]?art\b",
    r"\bWorld[- ]?class\b",
    r"\bUnparalleled\b",
    r"\bUnprecedented\b",
    r"\bRobust\b",
    r"\bLeverage\b",
    r"\bSynergy\b",
    r"\bHolistic(ally)?\b",
    r"\bParadigm\b",
    r"\bDisrupt(s|ed|ing|ive)?\b",
    r"\bEcosystem\b",
    r"\bScalable\b",
    r"\bDemocratiz(e|es|ed|ing)\b",
    r"\bFrictionless\b",
    r"\bTurnkey\b",
    r"\b10x\b",

    # Fake enthusiasm
    r"\bI'?m (so |really )?excited to\b",
    r"\bI can'?t wait to\b",
    r"\bThis is (truly |absolutely )?(amazing|incredible|fantastic)\b",
    r"\bAbsolutely\b",  # when used as emphasis filler
    r"\bLiterally\b",   # AI overuses this

    # Format tells
    r"^(Hey|Hi) (there|everyone|folks|Reddit|gamers)!",  # generic greeting opener
    r"\bHappy coding!?\b",
    r"\bHappy (game ?)?dev(eloping|ving)?!?\b",
    r"\bWhat do you (all )?think\?\s*$",  # generic closing question
]

# ─── Promotional density rules ──────────────────────────────────────────────

VERSE8_PROMO_TERMS = [
    r"\bverse8\b",
    r"\bverse 8\b",
    r"\bverse8\.io\b",
]

# Maximum ratio of promotional sentences to total sentences
MAX_PROMO_RATIO = 0.30  # 30% max — 70% should be value/community content


# ─── Prompt injection for Claude ────────────────────────────────────────────

CONTENT_RULES_PROMPT = """
## CONTENT RULES (MANDATORY — violation = rejection)

### Anti-AI-Detection Rules
- NEVER use em-dash (—) or en-dash (–). Use regular hyphen (-) or rewrite the sentence.
- NEVER start with "Hey everyone!", "Hey there!", "Hi folks!" or similar generic greetings. Start naturally like a real Reddit/forum user would.
- NEVER use transition words: Furthermore, Moreover, Additionally, Consequently, Nevertheless.
- NEVER use the phrase "Whether you're a X or a Y".
- NEVER use "Let's dive in", "Without further ado", "It's worth noting", "At the end of the day".
- NEVER end with "What do you think?" or "Happy coding!" or generic closing questions.
- NEVER use "I'm excited to", "I can't wait to share".
- Write like a real person typing on Reddit — short paragraphs, casual punctuation, occasional typos-level naturalness.
- Use contractions (don't, can't, it's, that's). Never write "do not" or "cannot" in casual contexts.
- Vary sentence length. Mix short punchy sentences with longer ones.

### Anti-Promotion Rules
- Maximum 30% of content can mention Verse8. The rest must be genuine value/discussion.
- NEVER write content that reads like an ad or press release.
- Lead with value, insight, or a genuine response to the topic. Mention Verse8 only where naturally relevant.
- If the post is a reply/comment, address the original poster's question/point FIRST before any mention of Verse8.
- It's OK to not mention Verse8 at all if it doesn't fit naturally.

### Format Rules
- Reddit: No headers (# or ##). Just plain text with paragraph breaks.
- Reddit comments: Keep under 150 words. Be concise.
- Reddit posts: Keep under 300 words.
- itch.io: Can be slightly longer (up to 500 words) and use basic formatting.
"""


# ─── Post-generation validation ─────────────────────────────────────────────

def validate_content(text: str) -> dict:
    """
    Validate generated content against rules.
    Returns {"valid": bool, "issues": [...], "cleaned": str}
    """
    if not text:
        return {"valid": False, "issues": ["Empty content"], "cleaned": ""}

    issues = []
    cleaned = text

    # 1. Auto-fix replacements (em-dash, en-dash, etc.)
    for old, new in AI_TELL_REPLACEMENTS.items():
        if old in cleaned:
            issues.append(f"Auto-replaced '{old}' → '{new}'")
            cleaned = cleaned.replace(old, new)

    # 2. Check for AI tell phrases
    for pattern in AI_TELL_PHRASES:
        match = re.search(pattern, cleaned, re.IGNORECASE | re.MULTILINE)
        if match:
            issues.append(f"AI-tell detected: '{match.group()}'")

    # 3. Check promotional density
    sentences = [s.strip() for s in re.split(r'[.!?]+', cleaned) if s.strip()]
    if sentences:
        promo_count = 0
        for sentence in sentences:
            for term in VERSE8_PROMO_TERMS:
                if re.search(term, sentence, re.IGNORECASE):
                    promo_count += 1
                    break
        ratio = promo_count / len(sentences)
        if ratio > MAX_PROMO_RATIO:
            issues.append(
                f"Promotional density too high: {promo_count}/{len(sentences)} "
                f"sentences ({ratio:.0%}) mention Verse8 (max {MAX_PROMO_RATIO:.0%})"
            )

    # 4. Check word count
    word_count = len(cleaned.split())
    if word_count > 500:
        issues.append(f"Too long: {word_count} words (max 500)")

    # 5. Check for markdown headers in Reddit content (AI tell)
    if re.search(r'^#{1,3}\s', cleaned, re.MULTILINE):
        issues.append("Contains markdown headers (## or #) — remove for Reddit")

    # 6. Check for excessive exclamation marks (AI enthusiasm)
    excl_count = cleaned.count('!')
    if excl_count > 3:
        issues.append(f"Too many exclamation marks: {excl_count} (max 3)")

    valid = len([i for i in issues if not i.startswith("Auto-replaced")]) == 0

    return {
        "valid": valid,
        "issues": issues,
        "cleaned": cleaned,
        "word_count": word_count,
    }
