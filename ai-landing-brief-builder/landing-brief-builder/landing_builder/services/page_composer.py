from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Iterable

from landing_builder.domain.models import FAQItem, Page
from landing_builder.domain.schemas import PageCreateRequest

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_WORD_SPLIT_PATTERN = re.compile(r"[,;/]|\band\b|\bfor\b", re.IGNORECASE)
_CYRILLIC_TO_LATIN = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)

_TONE_HINTS: tuple[tuple[str, str], ...] = (
    ("direct", "direct"),
    ("clear", "plainspoken"),
    ("expert", "expert-led"),
    ("friendly", "approachable"),
    ("practical", "practical"),
    ("confident", "confident"),
)


def slugify(value: str) -> str:
    transliterated = value.lower().translate(_CYRILLIC_TO_LATIN)
    normalized = unicodedata.normalize("NFKD", transliterated).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_PATTERN.sub("-", normalized).strip("-")
    return slug or "landing-page"


def truncate_text(value: str, max_length: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_length:
        return cleaned

    candidate = cleaned[: max_length - 1].rsplit(" ", 1)[0].strip()
    return f"{candidate or cleaned[: max_length - 1].strip()}…"


def sentence_case(value: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


class PageComposer:
    def __init__(self, existing_slugs: Iterable[str] | None = None) -> None:
        self._existing_slugs = {slug.strip() for slug in existing_slugs or [] if slug.strip()}

    def build(
        self,
        payload: PageCreateRequest,
        *,
        slug_override: str | None = None,
        page_id: str | None = None,
        created_at: datetime | None = None,
        revision: int = 1,
        now: datetime | None = None,
    ) -> Page:
        audience = truncate_text(payload.audience, 72)
        offer = truncate_text(payload.offer, 82)
        niche = truncate_text(payload.niche, 48)
        tone = truncate_text(payload.tone, 48)
        business_name = truncate_text(payload.business_name, 80)
        call_to_action = truncate_text(payload.call_to_action, 80)
        timestamp = (now or datetime.now(timezone.utc)).replace(microsecond=0)

        return Page(
            id=page_id or Page.model_fields["id"].default_factory(),
            slug=slug_override or self._build_unique_slug(payload.business_name),
            revision=revision,
            created_at=created_at or timestamp,
            updated_at=timestamp,
            business_name=payload.business_name,
            niche=payload.niche,
            audience=payload.audience,
            offer=payload.offer,
            tone=payload.tone,
            call_to_action=payload.call_to_action,
            hero_title=truncate_text(
                f"{business_name}: {sentence_case(offer)} for {self._primary_audience_fragment(audience)}",
                200,
            ),
            hero_subtitle=truncate_text(
                self._build_hero_subtitle(
                    business_name=business_name,
                    niche=niche,
                    audience=audience,
                    offer=offer,
                    tone=tone,
                    call_to_action=call_to_action,
                ),
                400,
            ),
            benefits=self._build_benefits(
                business_name=business_name,
                audience=audience,
                niche=niche,
                offer=offer,
                tone=tone,
                call_to_action=call_to_action,
            ),
            faq=self._build_faq(
                business_name=business_name,
                audience=audience,
                offer=offer,
                niche=niche,
                call_to_action=call_to_action,
            ),
        )

    def _build_unique_slug(self, business_name: str) -> str:
        base_slug = slugify(business_name)
        candidate = base_slug
        suffix = 2

        while candidate in self._existing_slugs:
            candidate = f"{base_slug}-{suffix}"
            suffix += 1

        self._existing_slugs.add(candidate)
        return candidate

    @staticmethod
    def _tone_descriptor(tone: str) -> str:
        lowered = tone.lower()
        for needle, descriptor in _TONE_HINTS:
            if needle in lowered:
                return descriptor
        return truncate_text(lowered, 32)

    @staticmethod
    def _primary_audience_fragment(audience: str) -> str:
        first_chunk = _WORD_SPLIT_PATTERN.split(audience, maxsplit=1)[0]
        return truncate_text(first_chunk.strip(" ."), 60) or truncate_text(audience, 60)

    def _build_hero_subtitle(
        self,
        *,
        business_name: str,
        niche: str,
        audience: str,
        offer: str,
        tone: str,
        call_to_action: str,
    ) -> str:
        audience_focus = self._primary_audience_fragment(audience)
        tone_descriptor = self._tone_descriptor(tone)
        return (
            f"This draft frames {business_name} around {offer.lower()} for {audience_focus}, "
            f"keeps the message grounded in {niche.lower()}, and pushes toward a single next step: {call_to_action}. "
            f"The copy stays {tone_descriptor} so the page can be reviewed quickly before design or publishing work starts."
        )

    @classmethod
    def _build_benefits(
        cls,
        *,
        business_name: str,
        audience: str,
        niche: str,
        offer: str,
        tone: str,
        call_to_action: str,
    ) -> list[str]:
        audience_focus = cls._primary_audience_fragment(audience)
        tone_descriptor = cls._tone_descriptor(tone)
        offer_lower = offer.lower()
        niche_lower = niche.lower()
        return [
            truncate_text(
                f"The opening line gives {audience_focus} a concrete reason to care about {offer_lower}, instead of leading with vague product claims.",
                240,
            ),
            truncate_text(
                f"The supporting points stay anchored in {niche_lower}, so {business_name} sounds specific to its market instead of interchangeable with adjacent tools.",
                240,
            ),
            truncate_text(
                f"The draft keeps one clear action — {call_to_action} — and uses a {tone_descriptor} tone, which makes review easier before the copy is expanded or polished further.",
                240,
            ),
        ]

    @classmethod
    def _build_faq(
        cls,
        *,
        business_name: str,
        audience: str,
        offer: str,
        niche: str,
        call_to_action: str,
    ) -> list[FAQItem]:
        audience_focus = cls._primary_audience_fragment(audience)
        offer_lower = offer.lower()
        niche_lower = niche.lower()
        return [
            FAQItem(
                q=truncate_text(f"Who should recognize themselves in the first screen?", 240),
                a=truncate_text(
                    f"The page is written for {audience_focus}. The first screen should make that audience feel the draft understands the buying context around {offer_lower}.",
                    240,
                ),
            ),
            FAQItem(
                q=truncate_text(f"Why does the draft emphasize market context instead of feature volume?", 240),
                a=truncate_text(
                    f"Because credibility usually comes from sounding native to the {niche_lower} space. For {business_name}, that matters more than listing every possible capability on day one.",
                    240,
                ),
            ),
            FAQItem(
                q=truncate_text("What should happen before this becomes a real landing page?", 240),
                a=truncate_text(
                    f"Pressure-test the claims with real customer language, tighten weak phrases, and confirm that '{call_to_action}' is the next step you actually want visitors to take.",
                    240,
                ),
            ),
        ]
