from __future__ import annotations

import csv
import re
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from time import monotonic
from zipfile import BadZipFile

from assistant import Assistant, InvalidAnswer
from knowledge import KnowledgeBase
from llm import LLMClient, ModelUnavailable
from schemas import ChatMessage, ChatRequest, ChatResponse
from settings import Settings

MAX_ANSWER_CHARS = 10_000
MODEL_BUDGET_SECONDS = 1_070
OUTPUT_NAME = "submission.csv"
TIMEOUT_ANSWER = "Техническая ошибка: превышен лимит времени обработки вопроса."
RESPONSE_ERROR = "Не удалось сформировать ответ с проверяемыми источниками. Это техническая ошибка обработки."
ROLE_RE = re.compile(r"(?m)^[ \t]*(Пользователь|Ассистент|User|Assistant):[ \t]*", re.IGNORECASE)


def parse_question(text: str) -> ChatRequest:
    roles = list(ROLE_RE.finditer(text))
    if (not roles or text[:roles[0].start()].strip()
            or roles[0][1].lower() not in {"пользователь", "user"}):
        return ChatRequest(question=text)
    turns: list[ChatMessage] = []
    for index, marker in enumerate(roles):
        end = roles[index + 1].start() if index + 1 < len(roles) else len(text)
        content = text[marker.end():end].strip()
        if content:
            role = "user" if marker[1].lower() in {"пользователь", "user"} else "assistant"
            turns.append(ChatMessage(role=role, content=content))
    for index in range(len(turns) - 1, -1, -1):
        if turns[index].role == "user":
            return ChatRequest(question=turns[index].content, history=turns[:index])
    return ChatRequest(question=text)


def load_questions(path: Path) -> list[tuple[str, ChatRequest]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"id", "question"}.issubset(reader.fieldnames):
            raise ValueError("В questions.csv нужны колонки id и question")
        rows = []
        identifiers = set()
        for row in reader:
            identifier, question = row.get("id"), row.get("question")
            if not identifier or not identifier.strip() or identifier in identifiers:
                raise ValueError(f"Пустой или повторяющийся ID в строке {reader.line_num}")
            if question is None or not question.strip():
                raise ValueError(f"Пустой вопрос в строке {reader.line_num}")
            identifiers.add(identifier)
            rows.append((identifier, parse_question(question.strip())))
    return rows


def render_answer(response: ChatResponse) -> str:
    text = response.answer.strip()
    if not response.citations:
        return text[:MAX_ANSWER_CHARS] or RESPONSE_ERROR

    references = []
    for index, citation in enumerate(response.citations, 1):
        paragraph = format_section(citation.section)
        quote = " ".join(citation.quote.split())
        if len(quote) > 180:
            shortened = quote[:179].rsplit(" ", 1)[0]
            quote = shortened + "…"
        references.append(f"[{index}] {citation.title}{paragraph} — «{quote}»")
    sources = "\n\nИсточники:\n" + "\n".join(references)
    if len(text) + len(sources) > MAX_ANSWER_CHARS:
        references = [
            f"[{index}] {citation.title}" + format_section(citation.section)
            for index, citation in enumerate(response.citations, 1)
        ]
        sources = "\n\nИсточники:\n" + "\n".join(references)
    available = MAX_ANSWER_CHARS - len(sources)
    if available <= 0:
        return (text + sources)[:MAX_ANSWER_CHARS]
    if len(text) > available:
        text = text[:max(0, available - 1)].rstrip() + "…"
    return text + sources


def format_section(section: str | None) -> str:
    if not section:
        return ""
    return f", {section}" if section.startswith(("ст.", "ч.", "п.")) else f", п. {section}"


def write_csv(path: Path, questions: list[tuple[str, ChatRequest]], answers: list[str]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["id", "answer"])
        writer.writerows((identifier, answer) for (identifier, _), answer in zip(questions, answers, strict=True))
    temporary.replace(path)


def generate_answer(assistant: Assistant, request: ChatRequest) -> str:
    try:
        return render_answer(assistant.answer_with_repair(request))
    except InvalidAnswer:
        return RESPONSE_ERROR


def run(settings: Settings, output: Path = Path(OUTPUT_NAME)) -> tuple[int, int]:
    if not settings.model_configured:
        raise ValueError("Платформа должна передать LLM_BASE_URL, LLM_API_KEY и LLM_MODEL (или их алиасы)")
    deadline = monotonic() + MODEL_BUDGET_SECONDS
    questions = load_questions(settings.data_dir / "questions.csv")
    knowledge = KnowledgeBase()
    knowledge.load(settings.data_dir / "knowledge-base.zip")
    assistant = Assistant(knowledge, LLMClient(settings, deadline=deadline))
    if not questions:
        write_csv(output, [], [])
        return 0, 0

    answers = [TIMEOUT_ANSWER] * len(questions)
    workers = max(1, min(settings.max_workers, 8, len(questions)))
    pool = ThreadPoolExecutor(max_workers=workers)
    pending = {}
    next_index = 0
    failed = 0
    authentication_error = None
    try:
        while monotonic() < deadline:
            while next_index < len(questions) and len(pending) < workers and authentication_error is None:
                future = pool.submit(generate_answer, assistant, questions[next_index][1])
                pending[future] = next_index
                next_index += 1
            if not pending or authentication_error is not None:
                break
            done, _ = wait(pending, timeout=max(0.0, deadline - monotonic()), return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                try:
                    answer = future.result()
                    answers[index] = answer
                    failed += answer == RESPONSE_ERROR
                except ModelUnavailable as exc:
                    if exc.authentication_error:
                        authentication_error = str(exc)
                    answers[index] = "Техническая ошибка: " + str(exc) + "."
                    failed += 1
                except Exception as exc:
                    print(f"Ошибка вопроса {index + 1}: {type(exc).__name__}", file=sys.stderr)
                    answers[index] = RESPONSE_ERROR
                    failed += 1
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        if authentication_error is not None:
            answers = [
                "Техническая ошибка: " + authentication_error + "." if answer == TIMEOUT_ANSWER else answer
                for answer in answers
            ]
        write_csv(output, questions, answers)
    if authentication_error:
        raise ModelUnavailable(authentication_error, authentication_error=True)
    return len(answers), failed + len(pending) + len(questions) - next_index


def main() -> int:
    try:
        total, errors = run(Settings.from_env())
    except (OSError, ValueError, BadZipFile, ModelUnavailable, csv.Error) as exc:
        print(f"Сабмит: {exc}", file=sys.stderr)
        return 1
    if total and errors == total:
        print(f"Сабмит: модель не обработала ни одного вопроса ({total})", file=sys.stderr)
        return 1
    print(f"Сабмит: {total} ответов в {OUTPUT_NAME}, технических ошибок: {errors}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
