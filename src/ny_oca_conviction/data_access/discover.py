from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from ny_oca_conviction.config import DEFAULT_SOURCE_PAGE_URL, ensure_project_layout
from ny_oca_conviction.utils.io import read_json, write_json

USER_AGENT = "juryrig/0.1 (+research-only; OCA-STAT discovery)"


class DiscoveryUnavailableError(RuntimeError):
    """Raised when the source page is blocked or otherwise unavailable."""


@dataclass(frozen=True)
class SourceRecord:
    source_name: str
    year: int
    source_page_url: str
    resolved_url: str
    link_text: str
    discovered_at: str


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._current_href = dict(attrs).get("href")
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href:
            text = "".join(self._current_text).strip()
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []


def _fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise DiscoveryUnavailableError(
            f"Source page returned HTTP {exc.code}; use manual browser discovery/download."
        ) from exc
    except URLError as exc:
        raise DiscoveryUnavailableError(
            "Source page was unavailable; use manual browser discovery/download."
        ) from exc


def discover_sources(source_page_url: str = DEFAULT_SOURCE_PAGE_URL) -> list[SourceRecord]:
    parser = AnchorParser()
    parser.feed(_fetch_html(source_page_url))

    discovered_at = datetime.now(UTC).isoformat()
    records: list[SourceRecord] = []
    seen_years: set[int] = set()
    for href, text in parser.links:
        if not text.isdigit() or len(text) != 4:
            continue
        year = int(text)
        if year in seen_years:
            continue
        seen_years.add(year)
        records.append(
            SourceRecord(
                source_name="oca_stat",
                year=year,
                source_page_url=source_page_url,
                resolved_url=urljoin(source_page_url, href),
                link_text=text,
                discovered_at=discovered_at,
            )
        )
    return sorted(records, key=lambda record: record.year)


def save_discovery(records: list[SourceRecord], path: Path | None = None) -> Path:
    paths = ensure_project_layout()
    output_path = path or paths.reference / "oca_stat_source_links.json"
    write_json(output_path, [asdict(record) for record in records])
    return output_path


def load_saved_discovery(path: Path | None = None) -> list[SourceRecord]:
    paths = ensure_project_layout()
    input_path = path or paths.reference / "oca_stat_source_links.json"
    if not input_path.exists():
        return []
    return [SourceRecord(**item) for item in read_json(input_path)]
