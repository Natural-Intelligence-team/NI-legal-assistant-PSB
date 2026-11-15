from collections import Counter
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from math import log1p
from pathlib import Path, PurePosixPath
import re
import unicodedata
from zipfile import ZipFile

from schemas import Document, Fragment, SearchRequest, SearchResult

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_CORPUS_BYTES = 64 * 1024 * 1024
FRAGMENT_CHARS = 1050
MAX_RESULTS = 14

WORD = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
CLAUSE = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:[.)])\s+(?=\S)", re.MULTILINE)
ARTICLE = re.compile(r"\bстатья\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE)
CONTRACT = re.compile(r"\b([а-яa-z]{1,4})\s*[-–‑−]\s*(\d{1,5})\s*[/\-–‑]\s*(\d{4})\b")
INSTRUCTION = re.compile(
    r"^\s*(?:ВНИМАНИЕ\s+ДЛЯ\s+ИИ|СИСТЕМНОЕ\s+СООБЩЕНИЕ|SYSTEM\s*:|\[SYSTEM\])",
    re.IGNORECASE,
)
STOP = set(
    "а бы был были в вам вас во все вы где да для до его ее если за и из или им их к как какая какие какой "
    "когда кто ли мне мы на нам нас не но о об он она они от по под при про с со так то у уже что это этот "
    "этого этот нужно можем можно должен должна должны вопрос пользователь ассистент договор договора "
    "договору рублей рф году года месяц какой каких этой этом сразу только там тут ей его же".split()
)
ENDINGS = sorted(set(
    "иями ями ами ого ему ому ыми ими ией иям иях ах ях ов ев ей ой ый ий ая яя ое ее ые ие ую юю ом ем ым ам ям "
    "ия ию ии ы и а я у ю е о".split()
), key=lambda value: (-len(value), value))
SYNONYMS = {
    "аванс": ("предоплат",),
    "акт": ("акту", "актом"),
    "гарант": ("гарантийн", "гарантия"),
    "гарантия": ("гарантийн",),
    "ноч": ("круглосуточно", "доступ"),
    "пропускать": ("доступ",),
    "дефект": ("недостатк",),
    "юротдел": ("юридическ", "отдел"),
    "проверить": ("приемк",),
    "запустить": ("инициатор",),
    "сдать": ("возвращает", "возврат", "акту"),
    "съезжать": ("возвращает", "арендатор"),
}


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower().replace("ё", "е")


def _stem(word: str) -> str:
    if len(word) >= 5 and re.fullmatch(r"[а-я]+", word):
        for ending in ENDINGS:
            if word.endswith(ending) and len(word) - len(ending) >= 4:
                return word[:-len(ending)]
    return word


def _words(text: str) -> list[str]:
    return [_stem(word) for word in WORD.findall(_normalize(text)) if len(word) > 1 and word not in STOP]


def _contracts(text: str) -> set[tuple[str, str, str]]:
    return {(prefix.translate(str.maketrans("aepc", "аерс")), number, year)
            for prefix, number, year in CONTRACT.findall(_normalize(text))}


def _bounded(text: str):
    remaining = text.strip()
    while len(remaining) > FRAGMENT_CHARS:
        window = remaining[:FRAGMENT_CHARS + 1]
        boundary = max(window.rfind("\n"), window.rfind(". ") + 1)
        if boundary < FRAGMENT_CHARS // 2:
            boundary = max(FRAGMENT_CHARS // 2, window.rfind(" "))
        yield remaining[:boundary].strip()
        remaining = remaining[boundary:].strip()
    if remaining:
        yield remaining


def _fragment_text(text: str, is_law: bool):
    spans: list[str] = []
    span_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if INSTRUCTION.match(line):
            spans.append("".join(span_lines))
            span_lines = []
        else:
            span_lines.append(line)
    spans.append("".join(span_lines))
    for span in spans:
        if is_law:
            article = ARTICLE.search(span)
            section = f"ст. {article[1]}" if article else None
            yield from ((section, piece) for piece in _bounded(span))
            continue
        sections = list(CLAUSE.finditer(span))
        if sections:
            yield from ((None, piece) for piece in _bounded(span[:sections[0].start()]))
            for index, match in enumerate(sections):
                end = sections[index + 1].start() if index + 1 < len(sections) else len(span)
                yield from ((match[1], piece) for piece in _bounded(span[match.start():end]))
        else:
            yield from ((None, piece) for piece in _bounded(span))


@dataclass
class Source:
    fragment_positions: list[int]
    title_words: set[str]
    entities: set[str]
    contracts: set[tuple[str, str, str]]
    group: str
    starts: date | None
    ends: date | None


def _date_match(text: str, pattern: str) -> date | None:
    match = re.search(pattern + r"\s*(\d{2})\.(\d{2})\.(\d{4})", text, re.IGNORECASE)
    if match is None:
        return None
    try:
        return date(int(match[3]), int(match[2]), int(match[1]))
    except ValueError:
        return None


def _describe(document: Document, is_law: bool) -> Source:
    title = _normalize(document.title)
    header = document.text[:1200]
    party = re.search(r"\b\d{4}\s+(.+)$", title) if title.startswith("договор ") else None
    group = "agreement_rules" if title.startswith("регламент согласования договоров") else ""
    starts = _date_match(header, r"(?:^|[.!?\n]\s*)действует с") if group else None
    ends = _date_match(header, r"редакция утратила силу с") if group else None
    starts = starts or (_date_match(header, r"редакция от") if group and ends else None)
    law_title = header.splitlines()[0] if is_law else ""
    identifier_context = "\n".join(header.splitlines()[:3])
    contracts = _contracts(title + "\n" + identifier_context) or _contracts(header)
    return Source([], set(_words(title + " " + law_title)),
                  set(_words(party[1])) if party else set(), contracts, group, starts, ends)


class KnowledgeBase:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.fragments: list[Fragment] = []
        self._sources: dict[str, Source] = {}
        self._terms: list[Counter[str]] = []
        self._lengths: list[int] = []
        self._idf: dict[str, float] = {}
        self._average_length = 1.0

    def load(self, archive: Path) -> None:
        documents: dict[str, Document] = {}
        sources: dict[str, Source] = {}
        fragments: list[Fragment] = []
        total_bytes = 0
        with ZipFile(archive) as source:
            for entry in sorted(source.infolist(), key=lambda item: item.filename):
                filename = PurePosixPath(entry.filename.replace("\\", "/"))
                if entry.is_dir() or filename.suffix.lower() != ".txt":
                    continue
                if filename.is_absolute() or ".." in filename.parts or ":" in filename.parts[0]:
                    raise ValueError(f"Небезопасный путь документа: {entry.filename}")
                total_bytes += entry.file_size
                if entry.file_size > MAX_DOCUMENT_BYTES or total_bytes > MAX_CORPUS_BYTES:
                    raise ValueError("Превышен допустимый размер базы документов")
                raw = source.read(entry)
                try:
                    body = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    raise ValueError(f"Документ не в UTF-8: {filename.name}") from None
                if not body.strip():
                    continue
                source_id = "doc-" + sha256(str(filename).encode("utf-8") + b"\x00" + raw).hexdigest()[:24]
                if source_id in documents:
                    raise ValueError(f"Повтор документа в архиве: {filename.name}")
                title = filename.stem.split("__", 1)[-1].replace("_", " ")
                document = Document(source_id=source_id, title=title, text=body)
                documents[source_id] = document
                is_law = filename.name.casefold().startswith("законы__")
                meta = _describe(document, is_law)
                sources[source_id] = meta
                for index, (section, piece) in enumerate(_fragment_text(body, is_law)):
                    fragment = Fragment(source_id=source_id, fragment_id=f"{source_id}-{index}",
                                        title=title, section=section, text=piece)
                    meta.fragment_positions.append(len(fragments))
                    fragments.append(fragment)
        if not documents:
            raise ValueError("В архиве нет непустых TXT-документов")

        terms = [Counter(_words(fragment.text)) for fragment in fragments]
        lengths = [sum(count.values()) for count in terms]
        frequencies: Counter[str] = Counter()
        for count in terms:
            frequencies.update(count.keys())
        self.documents = documents
        self._sources = sources
        self.fragments = fragments
        self._terms = terms
        self._lengths = lengths
        self._average_length = sum(lengths) / max(len(lengths), 1) or 1.0
        self._idf = {word: log1p((len(terms) - n + 0.5) / (n + 0.5)) for word, n in frequencies.items()}

    def search(self, request: SearchRequest) -> SearchResult:
        lines = [line.strip() for line in request.query.splitlines() if line.strip()]
        if not lines or not self.fragments:
            return SearchResult(status="not_found", fragments=[])
        current = set(_words(lines[-1]))
        history = set(_words("\n".join(lines[:-1]))) - current
        expansion = {alias for word in current for alias in SYNONYMS.get(word, ())} - current
        terms = {word: 0.2 for word in history}
        terms.update((word, 0.7) for word in expansion)
        terms.update((word, 1.0) for word in current)
        cited_ids: set[tuple[str, str, str]] = set()
        entity_words: set[str] = set()
        for line in reversed(lines):
            cited_ids = _contracts(line)
            if cited_ids:
                break
        for line in reversed(lines):
            words = set(_words(line))
            if any(source.entities and source.entities <= words for source in self._sources.values()):
                entity_words = words
                break

        scored = []
        for index, fragment in enumerate(self.fragments):
            frequencies = self._terms[index]
            source = self._sources[fragment.source_id]
            matched = terms.keys() & frequencies.keys()
            title_matches = current & source.title_words
            exact_id = bool(cited_ids & source.contracts)
            exact_entity = bool(source.entities and source.entities <= entity_words) and not cited_ids
            if not matched and not title_matches and not exact_id and not exact_entity:
                continue
            scale = 1.5 * (0.25 + 0.75 * self._lengths[index] / self._average_length)
            score = sum(self._idf[word] * terms[word] * frequencies[word] * 2.5 / (frequencies[word] + scale)
                        for word in sorted(matched))
            score += 0.8 * len(title_matches) + 0.45 * len(current & matched)
            if exact_id:
                score += 8.0
            if exact_entity:
                score += 7.0
            if source.group and source.ends and request.event_date is None:
                score *= 0.85
            scored.append((score, index))

        ranked = [index for _, index in sorted(scored, key=lambda pair: (-pair[0], pair[1]))]
        if not ranked:
            return SearchResult(status="not_found", fragments=[])

        allowed = {source_id for source_id, info in self._sources.items()
                   if self._edition_applies(info, request.event_date, request.event_date_end)}
        highest = self.fragments[ranked[0]]
        highest_meta = self._sources[highest.source_id]
        if highest_meta.group and request.event_date is not None and not any(
            meta.group == highest_meta.group and source_id in allowed for source_id, meta in self._sources.items()
        ):
            return SearchResult(status="edition_unavailable", fragments=[])
        ranked = [index for index in ranked if self.fragments[index].source_id in allowed]
        if not ranked:
            return SearchResult(status="not_found", fragments=[])

        selected = dict.fromkeys(ranked[:7])
        first_sources = tuple(dict.fromkeys(self.fragments[index].source_id for index in ranked[:5]))
        order = {index: rank for rank, index in enumerate(ranked)}
        for source_id in first_sources:
            meta = self._sources[source_id]
            if meta.group and meta.fragment_positions:
                selected.setdefault(meta.fragment_positions[0])
            for other_id, other in self._sources.items():
                if other_id == source_id or other_id not in allowed:
                    continue
                related = (meta.contracts & other.contracts
                           or (meta.group and meta.group == other.group)
                           or (meta.group and "комплаенс" in _normalize(self.documents[other_id].title))
                           or (other.group and "комплаенс" in _normalize(self.documents[source_id].title)))
                if related:
                    positions = sorted(other.fragment_positions, key=lambda index: order.get(index, len(ranked)))
                    for index in positions[:2]:
                        selected.setdefault(index)
                    if other.group and other.fragment_positions:
                        selected.setdefault(other.fragment_positions[0])
            if len(selected) >= MAX_RESULTS:
                break
        for index in ranked[:3]:
            fragment = self.fragments[index]
            for neighbor in (index - 1, index + 1):
                if 0 <= neighbor < len(self.fragments):
                    other = self.fragments[neighbor]
                    if other.source_id == fragment.source_id and self._same_section(fragment, other):
                        selected.setdefault(neighbor)
        for index in ranked:
            if len(selected) >= MAX_RESULTS:
                break
            selected.setdefault(index)
        return SearchResult(status="ok", fragments=[self.fragments[index] for index in list(selected)[:MAX_RESULTS]])

    @staticmethod
    def _edition_applies(source: Source, event_date: date | None, event_date_end: date | None) -> bool:
        return (event_date is None or not source.group
                or ((source.starts is None or source.starts <= (event_date_end or event_date))
                    and (source.ends is None or event_date < source.ends)))

    @staticmethod
    def _same_section(first: Fragment, second: Fragment) -> bool:
        return (first.section is not None and second.section is not None
                and first.section.split(".")[0] == second.section.split(".")[0])

    def get_document(self, source_id: str) -> Document | None:
        return self.documents.get(source_id)
