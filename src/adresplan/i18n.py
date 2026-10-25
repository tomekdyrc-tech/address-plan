"""User-facing language: Polish source text with an English catalogue.

Polish strings stay in the code as message ids; ``tr`` returns the English text when the
active language is English. The language is a context variable, set per HTTP request or
CLI run, so pure functions such as exports follow the caller without extra parameters.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache
from importlib.resources import files
from typing import Literal, cast

Language = Literal["pl", "en"]
LANGUAGES: tuple[Language, ...] = ("pl", "en")
DEFAULT_LANGUAGE: Language = "pl"

_active: ContextVar[Language] = ContextVar("language", default=DEFAULT_LANGUAGE)

# English lookups without a catalogue entry; tests assert this stays empty.
missing: set[str] = set()


@cache
def catalog() -> dict[str, str]:
    raw = files("adresplan").joinpath("locale/en.json").read_text(encoding="utf-8")
    return cast(dict[str, str], json.loads(raw))


def language() -> Language:
    return _active.get()


def parse_language(value: str | None) -> Language | None:
    text = (value or "").strip().lower()
    return text if text in LANGUAGES else None


def set_language(value: Language) -> None:
    _active.set(value)


@contextmanager
def use_language(value: Language) -> Iterator[None]:
    token = _active.set(value)
    try:
        yield
    finally:
        _active.reset(token)


def tr(text: str, /, **values: object) -> str:
    """Translate Polish ``text`` to the active language, then fill ``{name}`` fields."""
    if _active.get() == "en":
        translated = catalog().get(text)
        if translated is None:
            missing.add(text)
        else:
            text = translated
    return text.format(**values) if values else text


def tr_all(*texts: str) -> tuple[str, ...]:
    """Translate a row of labels, e.g. table headers."""
    return tuple(tr(text) for text in texts)


def preferred_language(accept_language: str | None) -> Language:
    """Polish unless the browser's first choice is a language other than Polish."""
    first = (accept_language or "").split(",")[0].split(";")[0].strip().lower()
    if not first or first == "*" or first.startswith("pl"):
        return DEFAULT_LANGUAGE
    return "en"
