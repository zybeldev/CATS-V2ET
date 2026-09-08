from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from typing import Callable
from urllib.request import Request, urlopen
from uuid import UUID

from cats.retrieval.models import EvidenceDocument


@dataclass(frozen=True)
class PublicEvidenceRequest:
    url: str
    source_name: str
    financial_instrument_id: UUID | None = None
    observed_at: datetime | None = None


class PublicWebEvidenceSource:
    """Minimal public-web evidence ingestion boundary for V2ET.

    This adapter fetches public text, strips simple HTML markup, and returns an
    EvidenceDocument with source metadata. Retrieved content is evidence only;
    it never becomes an instruction or an executable action.

    For public web evidence, ``observed_at`` represents the source publication
    or source-observation time when it can be established. The adapter first
    honors an explicitly supplied value and otherwise attempts conservative
    extraction from common publication-date metadata. ``retrieved_at`` remains
    the separate time at which CATS acquired the source.
    """

    _DATE_MARKERS = {
        "article:published_time",
        "datepublished",
        "date",
        "pubdate",
        "publishdate",
        "publish-date",
        "publication_date",
        "publication-date",
        "parsely-pub-date",
    }

    def __init__(self, fetcher: Callable[[str], str] | None = None):
        self.fetcher = fetcher or self._default_fetcher

    @staticmethod
    def _default_fetcher(url: str) -> str:
        # Use ordinary browser-style request headers. Many public news sites
        # reject generic programmatic user agents even when the page itself is
        # publicly accessible. This remains a simple HTTP GET; it does not
        # attempt to bypass authentication, paywalls, or other access controls.
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "text/plain;q=0.8,*/*;q=0.5"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        )
        with urlopen(request, timeout=15) as response:  # nosec B310 - explicit public URL adapter
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    @staticmethod
    def _to_text(raw: str) -> str:
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = unescape(text)
        return " ".join(text.split())

    @classmethod
    def _extract_source_date(cls, raw: str) -> tuple[datetime | None, str]:
        """Extract a publication/source date from common public-page metadata.

        The parser is intentionally conservative and dependency-free. It does
        not infer a publication date from arbitrary body text.
        """

        # JSON-LD / embedded structured data is common on financial news pages.
        json_ld_patterns = (
            r'(?is)["\']datePublished["\']\s*:\s*["\']([^"\']+)["\']',
            r'(?is)["\']dateCreated["\']\s*:\s*["\']([^"\']+)["\']',
        )
        for pattern in json_ld_patterns:
            match = re.search(pattern, raw)
            if match:
                parsed = cls._parse_datetime(match.group(1))
                if parsed is not None:
                    return parsed, "STRUCTURED_DATA"

        # Meta and time tags: parse attributes independent of attribute order.
        for tag in re.findall(r"(?is)<(?:meta|time)\b[^>]*>", raw):
            attrs = {
                key.lower(): unescape(value).strip()
                for key, value in re.findall(
                    r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*[\"']([^\"']*)[\"']",
                    tag,
                )
            }
            marker = (
                attrs.get("property")
                or attrs.get("name")
                or attrs.get("itemprop")
                or ""
            ).lower()
            value = attrs.get("content") or attrs.get("datetime")
            if not value:
                continue
            if marker in cls._DATE_MARKERS or tag.lower().startswith("<time"):
                parsed = cls._parse_datetime(value)
                if parsed is not None:
                    return parsed, "HTML_METADATA"

        return None, "UNKNOWN"

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        candidate = unescape(value).strip()
        if not candidate:
            return None

        iso_candidate = candidate
        if iso_candidate.endswith("Z"):
            iso_candidate = iso_candidate[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(iso_candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass

        try:
            parsed = parsedate_to_datetime(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None

    def ingest(self, request: PublicEvidenceRequest) -> EvidenceDocument:
        raw = self.fetcher(request.url)
        text = self._to_text(raw)
        if not text:
            raise ValueError("Public evidence source returned no usable text")

        if request.observed_at is not None:
            source_date = request.observed_at
            source_date_origin = "REQUEST_SUPPLIED"
        else:
            source_date, source_date_origin = self._extract_source_date(raw)

        metadata = {
            "source_type": "PUBLIC_WEB",
            "url": request.url,
            "source_date_origin": source_date_origin,
            "source_date_status": "KNOWN" if source_date is not None else "UNKNOWN",
        }
        if source_date is not None:
            metadata["source_date"] = source_date.isoformat()

        return EvidenceDocument(
            text=text,
            source_name=request.source_name,
            external_reference=request.url,
            financial_instrument_id=request.financial_instrument_id,
            observed_at=source_date,
            retrieved_at=datetime.now(timezone.utc),
            metadata=metadata,
        )
