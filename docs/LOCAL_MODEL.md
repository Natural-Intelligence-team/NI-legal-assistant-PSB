
# Local LLM (Qwen2.5-7B)

Локальный запуск Qwen2.5-7B-Instruct через llama-cpp-python с OpenAI-compatible API.

УСТАНОВКА

pip install -r requirements-local.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

КОНФИГУРАЦИЯ

Добавить в файл .env:

LLM_BASE_URL=http://127.0.0.1:8001/v1
LLM_API_KEY=local
LLM_MODEL=Qwen2.5-7B-Instruct
TEMPERATURE=0
MAX_TOKENS=2200
LLM_TIMEOUT=90

GGUF-файл модели должен быть доступен локально. По умолчанию используется:

~/Загрузки/Qwen2.5-7B-Instruct-Q4_K_M.gguf

ЗАПУСК

./scripts/run-local-llm.sh

По умолчанию сервер запускается на 127.0.0.1:8001, CPU — 8 потоков, контекст — 2048 токенов.

Параметры можно переопределить через MODEL_PATH, LLM_THREADS, LLM_CONTEXT, LLM_HOST и LLM_PORT.

