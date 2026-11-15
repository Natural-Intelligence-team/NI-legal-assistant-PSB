"""FastAPI entry point: python -m uvicorn api:app --reload --port 8000."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from assistant import Assistant, InvalidAnswer
from knowledge import KnowledgeBase
from llm import LLMClient, ModelUnavailable
from schemas import ApiError, ChatRequest, ChatResponse, Document
from settings import Settings


def create_app(knowledge: KnowledgeBase | None = None, llm: LLMClient | None = None,
               settings: Settings | None = None) -> FastAPI:
    cfg = settings if settings is not None else Settings.from_env()
    store = knowledge if knowledge is not None else KnowledgeBase()
    archive = cfg.data_dir / "knowledge-base.zip"
    if knowledge is None and archive.is_file():
        store.load(archive)
    model = llm if llm is not None else LLMClient(cfg)
    assistant = Assistant(store, model)
    app = FastAPI(title="Юридический ассистент ПСБ")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=ApiError(error=str(exc.detail)).model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=ApiError(error="Проверьте вопрос и историю сообщений").model_dump())

    @app.get("/health")
    def health():
        return {"status": "ok", "model_configured": cfg.model_configured,
                "documents": len(store.documents)}

    @app.post("/api/chat", response_model=ChatResponse,
              responses={422: {"model": ApiError}, 503: {"model": ApiError}})
    def chat(request: ChatRequest):
        if not store.documents:
            raise HTTPException(status_code=503, detail="База документов не загружена")
        try:
            return assistant.answer_with_repair(request)
        except (ModelUnavailable, InvalidAnswer) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None

    @app.get("/api/documents/{source_id}", response_model=Document, responses={404: {"model": ApiError}})
    def document(source_id: str):
        result = store.get_document(source_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Документ не найден")
        return result

    return app


app = create_app()
