"""Fast local preprocessing that exposes common prompt-obfuscation attempts.

This is a security-analysis representation, not text shown back to an LLM.  The
original prompt is retained separately for auditability.
"""
from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote


# Narrow mappings for documented/common confusable bypasses.  Broad transliteration
# would create false positives for legitimate non-English input.
CONFUSABLES = {"袉": "I", "Ι": "I", "і": "i", "ο": "o", "а": "a", "ｅ": "e"}
INVISIBLE_ARTIFACTS = {"鈥", "�"}  # Common mojibake forms of invisible punctuation.
BASE64_TOKEN = re.compile(r"(?<![A-Za-z0-9+/=])(?:[A-Za-z0-9+/]{16,}={0,2})(?![A-Za-z0-9+/=])")
SUSPICIOUS_WORDS = {"ignore", "previous", "instructions", "override", "system", "prompt", "reveal", "developer", "unrestricted", "bypass", "safety", "hidden"}
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "5": "s", "@": "a", "$": "s"})


@dataclass(frozen=True)
class NormalizationResult:
    original_prompt: str
    normalized_prompt: str
    decoded_content_detected: bool
    transformations: list[str]

    @property
    def transformation_detected(self) -> bool:
        return bool(self.transformations)


def _meaningful_text(value: str) -> bool:
    """Reject binary/random Base64 decoded data before it enters security analysis."""
    if len(value.strip()) < 4 or "\x00" in value:
        return False
    printable = sum(char.isprintable() or char.isspace() for char in value)
    letters = sum(char.isalpha() for char in value)
    return printable / max(len(value), 1) >= 0.9 and letters >= 3


def _decode_base64_tokens(value: str) -> tuple[str, bool]:
    decoded = False
    def replace(match: re.Match[str]) -> str:
        nonlocal decoded
        token = match.group(0)
        if len(token) % 4:  # Valid Base64 needs padding to a 4-byte boundary.
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


def _safe_leet_normalize(value: str) -> tuple[str, bool]:
    """Only replace numbers/symbols when they resolve to known attack vocabulary."""
    changed = False
    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        word = match.group(0)
        if not any(char in "0135@$" for char in word):
            return word
        candidate = word.lower().translate(LEET)
        if candidate in SUSPICIOUS_WORDS:
            changed = True
            return candidate
        return word
    return re.sub(r"\b[\w@$]+\b", replace, value), changed


def normalize_prompt(prompt: str) -> NormalizationResult:
    """Normalize without network/API calls and record every material transformation."""
    original = prompt
    transformations: list[str] = []
    value = unicodedata.normalize("NFKC", prompt)
    if value != prompt:
        transformations.append("unicode_nfkc")

    mapped = "".join(CONFUSABLES.get(char, char) for char in value)
    if mapped != value:
        transformations.append("unicode_confusable_mapped")
    value = mapped

    # Format/control characters include zero-width joiners/spaces; retain normal line
    # breaks as whitespace but remove non-printing control characters.
    cleaned = "".join(
        " " if char in "\n\r\t" else ""
        if unicodedata.category(char) in {"Cf", "Cc"} else ""
        if char in INVISIBLE_ARTIFACTS else char
        for char in value
    )
    if cleaned != value:
        transformations.append("invisible_characters_removed")
    value = cleaned

    url_decoded = unquote(value)
    if url_decoded != value:
        transformations.append("url_decoded")
    value = url_decoded

    value, decoded = _decode_base64_tokens(value)
    if decoded:
        transformations.append("base64_decoded")

    value, leet_changed = _safe_leet_normalize(value)
    if leet_changed:
        transformations.append("character_substitution_normalized")

    lowered = value.lower()
    if lowered != value:
        transformations.append("lowercase")
    value = re.sub(r"\s+", " ", lowered).strip()
    if value != lowered.strip():
        transformations.append("whitespace_normalized")
    return NormalizationResult(original, value, decoded, transformations)
