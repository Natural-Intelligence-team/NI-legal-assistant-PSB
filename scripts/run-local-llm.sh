#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"

MODEL_PATH="${MODEL_PATH:-$HOME/Загрузки/Qwen2.5-7B-Instruct-Q4_K_M.gguf}"
HOST="${LLM_HOST:-127.0.0.1}"
PORT="${LLM_PORT:-8001}"
THREADS="${LLM_THREADS:-8}"
CONTEXT="${LLM_CONTEXT:-2048}"

if [[ ! -x "$PYTHON" ]]; then
    echo "Ошибка: Python из .venv не найден: $PYTHON" >&2
    exit 1
fi

if [[ ! -f "$MODEL_PATH" ]]; then
    echo "Ошибка: GGUF-модель не найдена: $MODEL_PATH" >&2
    echo "Укажи путь через MODEL_PATH=/путь/к/модели" >&2
    exit 1
fi

exec "$PYTHON" -m llama_cpp.server \
    --model "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --n_threads "$THREADS" \
    --n_ctx "$CONTEXT"
