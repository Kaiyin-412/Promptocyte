"""Local adversarial prompt normalization with an explainable audit trail."""
from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote

CONFUSABLES = {"袉": "I", "Ι": "I", "і": "i", "ο": "o", "а": "a", "ｅ": "e"}
INVISIBLE_ARTIFACTS = {"鈥", "�"}
BASE64_TOKEN = re.compile(r"(?<![A-Za-z0-9+/=])(?:[A-Za-z0-9+/]{16,}={0,2})(?![A-Za-z0-9+/=])")
SUSPICIOUS_WORDS = {"ignore", "previous", "instructions", "override", "system", "prompt", "reveal", "developer", "unrestricted", "bypass", "safety", "hidden"}
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "5": "s", "@": "a", "$": "s"})


@dataclass(frozen=True)
class NormalizedPrompt:
    original: str
    value: str
    transformations: list[str]
    decoded_content_detected: bool


def _meaningful_text(value: str) -> bool:
    return len(value.strip()) >= 4 and "\x00" not in value and sum(char.isprintable() or char.isspace() for char in value) / max(len(value), 1) >= 0.9 and sum(char.isalpha() for char in value) >= 3


def _decode_base64(value: str) -> tuple[str, bool]:
    decoded = False
    def replace(match: re.Match[str]) -> str:
        nonlocal decoded
        token = match.group(0)
        if len(token) % 4:
            return token
        try:
            candidate = base64.b64decode(token, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return token
        if _meaningful_text(candidate):
            decoded = True
            return candidate
        return token
    return BASE64_TOKEN.sub(replace, value), decoded


def normalize_prompt(prompt: str) -> NormalizedPrompt:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    transformations: list[str] = []
    value = unicodedata.normalize("NFKC", prompt)
    if value != prompt: transformations.append("unicode_nfkc")
    mapped = "".join(CONFUSABLES.get(char, char) for char in value)
    if mapped != value: transformations.append("unicode_confusable_mapped")
    value = mapped
    cleaned = "".join(" " if char in "\n\r\t" else "" if unicodedata.category(char) in {"Cf", "Cc"} or char in INVISIBLE_ARTIFACTS else char for char in value)
    if cleaned != value: transformations.append("invisible_characters_removed")
    value = cleaned
    decoded_url = unquote(value)
    if decoded_url != value: transformations.append("url_decoded")
    value, decoded = _decode_base64(decoded_url)
    if decoded: transformations.append("base64_decoded")
    def leet(match: re.Match[str]) -> str:
        word, candidate = match.group(0), match.group(0).lower().translate(LEET)
        if any(char in "0135@$" for char in word) and candidate in SUSPICIOUS_WORDS:
            transformations.append("character_substitution_normalized")
            return candidate
        return word
    value = re.sub(r"\b[\w@$]+\b", leet, value)
    lowered = value.lower()
    if lowered != value: transformations.append("lowercase")
    normalized = re.sub(r"\s+", " ", lowered).strip()
    if normalized != lowered.strip(): transformations.append("whitespace_normalized")
    return NormalizedPrompt(prompt, normalized, transformations, decoded)
