"""Keyword extraction for interest tagging.

Scans free-text fields (motivation, questions, experience) and emits AI-domain tags.
Used by Analytics + Contact detail to derive interests when contacts didn't pick tags themselves.
"""
from __future__ import annotations
import re

# Map: tag -> regex pattern (case-insensitive). Add more as you learn the audience.
INTEREST_TAGS = {
    "LLM": r"\b(llm|large language model|gpt|claude|gemini|llama)\b",
    "Agent": r"\b(agent|agentic|autogpt|multi[- ]?agent)\b",
    "World Model": r"\b(world model|jepa|v-jepa)\b",
    "RAG": r"\b(rag|retrieval augmented)\b",
    "Vibe Coding": r"\b(vibe coding|cursor|copilot|claude code)\b",
    "Robotics / Embodied AI": r"\b(robot|robotics|embodied|sim[- ]?to[- ]?real|humanoid)\b",
    "Computer Vision": r"\b(vision|cv|image|video|nano banana|diffusion|sora|veo)\b",
    "RL": r"\b(reinforcement learning|\brl\b|ppo|dpo)\b",
    "Multimodal": r"\b(multimodal|multi[- ]modal|vlm|vla)\b",
    "MLOps / Infra": r"\b(mlops|kubernetes|infra|deployment|serving|inference)\b",
    "Healthcare AI": r"\b(health|medical|clinical|biomed|drug|hospital)\b",
    "FinTech / Quant": r"\b(quant|trading|finance|fintech|hedge fund|investment bank)\b",
    "Architecture / Design": r"\b(architect|architectural|design|cad|bim)\b",
    "Product / PM": r"\b(product manager|pm\b|product management|product associate)\b",
    "Founder / Startup": r"\b(founder|co[- ]?founder|startup|ceo|cto)\b",
    "Investor / VC": r"\b(investor|vc\b|venture|capital|fund)\b",
    "Research": r"\b(research|researcher|phd|postdoc|paper|publication)\b",
    "Networking": r"\b(network|networking|connect|community|social)\b",
    "Hiring / Career": r"\b(hire|hiring|career|job|recruit)\b",
    "Education / Teaching": r"\b(teach|teaching|professor|lecturer|education|tutor)\b",
}


def extract_interests(*texts: str) -> list[str]:
    text = " ".join(t for t in texts if t)
    if not text:
        return []
    found = []
    for tag, pat in INTEREST_TAGS.items():
        if re.search(pat, text, re.IGNORECASE):
            found.append(tag)
    return found


def top_interests(rows: list[dict], text_keys: list[str]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for r in rows:
        text = " ".join(str(r.get(k) or "") for k in text_keys)
        for tag in extract_interests(text):
            counter[tag] = counter.get(tag, 0) + 1
    return dict(sorted(counter.items(), key=lambda kv: -kv[1]))
