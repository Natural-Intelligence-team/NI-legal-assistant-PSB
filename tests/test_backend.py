"""Contract and integration checks using local fake retrieval/model responses."""

import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import httpx
from fastapi.testclient import TestClient

from api import create_app
from knowledge import KnowledgeBase
from llm import LLMClient, ModelUnavailable
from schemas import ChatRequest, ChatResponse, Document, SearchResult
from settings import Settings


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [json.loads(block) for block in re.findall(
    r"```json\s*\n(.*?)```", (ROOT / "docs" / "DATA_FORMAT.md").read_text(encoding="utf-8"), re.S)]
SEARCH = SearchResult.model_validate(EXAMPLES[0])
QUESTION = ChatRequest.model_validate(EXAMPLES[1])
ANSWER = ChatResponse.model_validate(EXAMPLES[2])


class TestKnowledge(KnowledgeBase):
    def __init__(self, result=SEARCH):
        super().__init__()
        self.result = result
        self.queries = []
        fragment = SEARCH.fragments[0]
        self.documents[fragment.source_id] = Document(
            source_id=fragment.source_id, title=fragment.title, text=fragment.text)

    def search(self, request):
        self.queries.append(request.query)
        return self.result


class TestModel:
    def __init__(self, content=None):
        self.content = json.dumps(structured_answer()) if content is None else content
        self.messages = []

    def generate(self, messages):
        self.messages.append(messages)
        return self.content


def structured_answer():
    return {
        "status": ANSWER.status,
        "claims": [{"text": ANSWER.answer, "citations": [
            {"fragment_id": item.fragment_id, "quote": item.quote} for item in ANSWER.citations]}],
        "missing": [],
    }


class ApiTests(unittest.TestCase):
    def make_client(self, knowledge=None, model=None):
        store = knowledge if knowledge is not None else KnowledgeBase()
        return TestClient(create_app(knowledge=store, llm=model, settings=Settings()))

    def test_api_starts_without_data_and_reports_no_basis(self):
        with self.make_client() as client:
            self.assertEqual(client.get("/health").json()["documents"], 0)
            result = client.post("/api/chat", json=QUESTION.model_dump())
            self.assertEqual(result.status_code, 503)
            self.assertIn("баз", result.json()["error"].lower())

    def test_question_to_answer_and_open_source_match_frontend_contract(self):
        with self.make_client(TestKnowledge(), TestModel()) as client:
            result = client.post("/api/chat", json=QUESTION.model_dump())
            self.assertEqual(result.status_code, 200)
            expected = ANSWER.model_copy(update={"answer": ANSWER.answer + " [1]"})
            self.assertEqual(result.json(), expected.model_dump())
            citation = result.json()["citations"][0]
            document = client.get("/api/documents/" + citation["source_id"])
            self.assertEqual(document.status_code, 200)
            self.assertIn(citation["quote"], document.json()["text"])

    def test_unknown_document_has_error_field(self):
        with self.make_client() as client:
            result = client.get("/api/documents/missing")
            self.assertEqual(result.status_code, 404)
            self.assertEqual(set(result.json()), {"error"})

    def test_invalid_question_has_error_field(self):
        with self.make_client() as client:
            for value in ({"question": " "}, {"question": 5}, {"history": []}):
                with self.subTest(value=value):
                    result = client.post("/api/chat", json=value)
                    self.assertEqual(result.status_code, 422)
                    self.assertEqual(set(result.json()), {"error"})

    def test_search_statuses_do_not_call_model(self):
        for status, expected in [("not_found", "insufficient"), ("date_required", "clarify"),
                                 ("edition_unavailable", "insufficient")]:
            with self.subTest(status=status):
                model = TestModel()
                knowledge = TestKnowledge(SearchResult(status=status, fragments=[]))
                with self.make_client(knowledge, model) as client:
                    result = client.post("/api/chat", json=QUESTION.model_dump())
                self.assertEqual(result.json()["status"], expected)
                self.assertEqual(model.messages, [])

    def test_history_is_explicit_and_not_shared_between_requests(self):
        knowledge, model = TestKnowledge(), TestModel()
        with self.make_client(knowledge, model) as client:
            request = QUESTION.model_dump()
            request["history"] = [{"role": "user", "content": "Первый договор"}]
            client.post("/api/chat", json=request)
            client.post("/api/chat", json=QUESTION.model_dump())
        self.assertIn("Первый договор", knowledge.queries[0])
        self.assertNotIn("Первый договор", knowledge.queries[1])
        self.assertEqual(json.loads(model.messages[1][1]["content"])["history"], [])

    def test_unknown_source_or_fake_quote_is_rejected(self):
        for field, value in [("fragment_id", "wrong"), ("quote", "Условие, отсутствующее в документе")]:
            with self.subTest(field=field):
                answer = structured_answer()
                answer["claims"][0]["citations"][0][field] = value
                with self.make_client(TestKnowledge(), TestModel(json.dumps(answer))) as client:
                    result = client.post("/api/chat", json=QUESTION.model_dump())
                self.assertEqual(result.status_code, 503)

    def test_substantive_answer_requires_citation(self):
        answer = structured_answer()
        answer["claims"][0]["citations"] = []
        with self.make_client(TestKnowledge(), TestModel(json.dumps(answer))) as client:
            self.assertEqual(client.post("/api/chat", json=QUESTION.model_dump()).status_code, 503)

    def test_invalid_model_json_is_a_technical_error(self):
        with self.make_client(TestKnowledge(), TestModel("plain text")) as client:
            result = client.post("/api/chat", json=QUESTION.model_dump())
            self.assertEqual(result.status_code, 503)
            self.assertIn("error", result.json())

    def test_cors_for_direct_local_frontend_connection(self):
        with self.make_client() as client:
            result = client.options("/api/chat", headers={
                "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
            self.assertEqual(result.headers["access-control-allow-origin"], "http://localhost:5173")

    def test_load_archive_and_open_the_same_source_across_reloads(self):
        body = "1. Условия договора\r\n1.1. Текст пункта."
        with TemporaryDirectory() as directory:
            path = Path(directory)
            with ZipFile(path / "knowledge-base.zip", "w") as archive:
                archive.writestr("документы компании__Договор.txt", body.encode("utf-8"))
            store = KnowledgeBase()
            store.load(path / "knowledge-base.zip")
            source_id = next(iter(store.documents))
            with TestClient(create_app(settings=Settings(data_dir=path))) as client:
                self.assertEqual(client.get("/health").json()["documents"], 1)
                response = client.get(f"/api/documents/{source_id}")
                self.assertEqual(response.json(), {"source_id": source_id, "title": "Договор", "text": body})


class ModelClientTests(unittest.TestCase):
    def test_transport_uses_configured_model_path_and_key(self):
        def handle(request):
            self.assertEqual(request.url.path, "/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            self.assertEqual(json.loads(request.content)["model"], "test-model")
            return httpx.Response(200, json={"choices": [{"message": {"content": "response"}}]})

        settings = Settings(base_url="http://model.local/v1", api_key="test-key", model="test-model")
        client = LLMClient(settings, httpx.MockTransport(handle))
        self.assertEqual(client.generate([]), "response")
        self.assertNotIn("test-key", repr(settings))

    def test_missing_config_does_not_send_request(self):
        with self.assertRaises(ModelUnavailable):
            LLMClient(Settings()).generate([])

    def test_http_failure_does_not_expose_service_key(self):
        settings = Settings(base_url="http://model.local/v1", api_key="test-key", model="test-model")
        transport = httpx.MockTransport(lambda request: httpx.Response(401, text="test-key"))
        with self.assertRaises(ModelUnavailable) as error:
            LLMClient(settings, transport).generate([])
        self.assertNotIn("test-key", str(error.exception))

    def test_environment_aliases_override_local_primary_names(self):
        with patch("settings.dotenv_values", return_value={
                "LLM_BASE_URL": "http://local.test/v1", "LLM_API_KEY": "local-key",
                "LLM_MODEL": "local-model"}), patch.dict("os.environ", {
                "OPENAI_BASE_URL": "http://proxy.local/v1", "OPENAI_API_KEY": "test-key",
                "GEN_MODEL": "test-model"}, clear=True):
            result = Settings.from_env()
        self.assertEqual(result.base_url, "http://proxy.local/v1")
        self.assertEqual(result.api_key, "test-key")
        self.assertEqual(result.model, "test-model")
        self.assertTrue(result.model_configured)


if __name__ == "__main__":
    unittest.main()
