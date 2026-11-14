import csv
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import httpx

from assistant import InvalidAnswer, _parse_answer, extract_event_date
from llm import LLMClient, ModelUnavailable
from schemas import Fragment, SearchResult
from settings import Settings
from solution import load_questions, parse_question, run


class QuestionTests(unittest.TestCase):
    def test_read_last_user_turn_and_keep_previous_assistant_as_data(self):
        parsed = parse_question("Пользователь: Первый вопрос\nАссистент: Неверный факт\n"
                                "Пользователь: Уточнение\nпродолжение\nАссистент: Чужой ответ")
        self.assertEqual(parsed.question, "Уточнение\nпродолжение")
        self.assertEqual(parsed.history[0].content, "Первый вопрос")
        self.assertEqual([message.role for message in parsed.history], ["user", "assistant"])

    def test_new_partial_date_does_not_inherit_old_date(self):
        old = ["Вопрос на 20.03.2025"]
        self.assertEqual(extract_event_date("А 14 апреля 2025?", old), date(2025, 4, 14))
        self.assertEqual(extract_event_date("А в августе 2024?", old), None)
        self.assertEqual(extract_event_date("А сколько дней?", old), date(2025, 3, 20))

    def test_duplicate_id_rejected(self):
        with TemporaryDirectory() as directory:
            file = Path(directory) / "questions.csv"
            file.write_text("id,question\n1,first\n1,second\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "повторяющийся"):
                load_questions(file)


class GroundingTests(unittest.TestCase):
    def test_whitespace_is_recovered_as_exact_source_span(self):
        fragment = Fragment(source_id="doc", fragment_id="point", title="Договор", section="1.1",
                            text="Срок оплаты —\r\nтридцать дней с даты передачи.")
        search = SearchResult(status="ok", fragments=[fragment])
        claim = {"text": "Срок оплаты составляет тридцать дней.",
                 "citations": [{"fragment_id": "point",
                                "quote": "Срок оплаты — тридцать дней с даты передачи."}]}
        answer = _parse_answer(json.dumps({"status": "answered", "claims": [claim], "missing": []}), search)
        self.assertIn(answer.citations[0].quote, fragment.text)
        self.assertEqual(answer.citations[0].source_id, "doc")
        self.assertIn("[1]", answer.answer)
        with self.assertRaises(InvalidAnswer):
            _parse_answer(json.dumps({"status": "answered", "answer": claim["text"],
                                      "citations": [answer.citations[0].model_dump()]}), search)


class SubmissionTests(unittest.TestCase):
    def test_batch_preserves_input_ids_and_produces_grounded_csv_with_mock_transport(self):
        supplied_history = []

        def respond(request):
            payload = json.loads(request.content)
            case = json.loads(payload["messages"][1]["content"])
            supplied_history.append((case["question"], case["history"]))
            fragment = case["fragments"][0]
            reply = {"status": "answered", "missing": [], "claims": [{
                "text": "Покупатель оплачивает товар в течение 30 дней.",
                "citations": [{"fragment_id": fragment["fragment_id"], "quote": fragment["text"]}],
            }]}
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}}]})

        with TemporaryDirectory() as directory:
            folder = Path(directory)
            with (folder / "questions.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["id", "question"])
                writer.writerow(["010", "Каков срок оплаты товара?"])
                writer.writerow(["a,b", "Пользователь: Что с оплатой товара?\n"
                                        "Ассистент: Уточните запрос.\n"
                                        "Пользователь: Каков срок оплаты?"])
            with ZipFile(folder / "knowledge-base.zip", "w") as archive:
                archive.writestr("документы компании__Договор № П-10-2024.txt",
                                 "ДОГОВОР ПОСТАВКИ\n4.2. Покупатель оплачивает товар "
                                 "в течение 30 дней с даты передачи.")
            settings = Settings(base_url="http://example.test/v1", api_key="test-only",
                                model="mock", data_dir=folder, max_workers=1)
            with patch("solution.LLMClient", side_effect=lambda cfg, deadline:
                       LLMClient(cfg, httpx.MockTransport(respond), deadline=deadline)):
                self.assertEqual(run(settings, folder / "submission.csv"), (2, 0))
            with (folder / "submission.csv").open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, ["id", "answer"])
                rows = list(reader)
            self.assertEqual([row["id"] for row in rows], ["010", "a,b"])
            self.assertTrue(all("Договор" in row["answer"] and len(row["answer"]) <= 10_000 for row in rows))
            self.assertEqual(supplied_history[0][1], [])
            self.assertEqual(supplied_history[1][0], "Каков срок оплаты?")
            self.assertEqual([item["role"] for item in supplied_history[1][1]], ["user", "assistant"])

    def test_missing_configuration_fails_before_reading_data(self):
        with self.assertRaisesRegex(ValueError, "LLM_BASE_URL"):
            run(Settings())

    def test_invalid_token_is_not_retried(self):
        attempts = 0

        def unauthorized(request):
            nonlocal attempts
            attempts += 1
            return httpx.Response(401, json={"token": "test-key"})

        settings = Settings(base_url="http://example.test/v1", api_key="test-key", model="mock")
        with self.assertRaises(ModelUnavailable) as failure:
            LLMClient(settings, httpx.MockTransport(unauthorized)).generate([])
        self.assertEqual(attempts, 1)
        self.assertTrue(failure.exception.authentication_error)
        self.assertNotIn("test-key", str(failure.exception))
