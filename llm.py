from time import monotonic, sleep
from urllib.parse import urlsplit

import httpx

from settings import Settings


class ModelUnavailable(RuntimeError):
    def __init__(self, message: str, *, authentication_error: bool = False):
        super().__init__(message)
        self.authentication_error = authentication_error


class LLMClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None,
                 *, deadline: float | None = None):
        self.settings = settings
        self.transport = transport
        self.deadline = deadline

    def _remaining(self) -> float:
        return self.deadline - monotonic() if self.deadline is not None else float("inf")

    def generate(self, messages: list[dict[str, str]]) -> str:
        cfg = self.settings
        if not cfg.model_configured:
            raise ModelUnavailable("Задайте адрес, ключ и имя модели в окружении сервера")
        try:
            url = urlsplit(cfg.base_url)
            if (url.scheme not in {"http", "https"} or not url.hostname or url.username is not None
                    or url.query or url.fragment):
                raise ValueError
        except ValueError:
            raise ModelUnavailable("Некорректный адрес API модели") from None
        payload = {"model": cfg.model, "messages": messages,
                   "temperature": cfg.temperature, "max_tokens": cfg.max_tokens}
        with httpx.Client(transport=self.transport, follow_redirects=False) as client:
            for attempt in range(2):
                remaining = self._remaining()
                if remaining <= 0:
                    raise ModelUnavailable("Истёк лимит времени пакетной обработки")
                timeout = min(cfg.timeout, remaining)
                try:
                    response = client.post(
                        cfg.base_url.rstrip("/") + "/chat/completions",
                        headers={"Authorization": "Bearer " + cfg.api_key},
                        json=payload,
                        timeout=httpx.Timeout(timeout, connect=min(5.0, timeout)),
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    if isinstance(content, str) and content.strip():
                        return content
                    raise ModelUnavailable("Модель вернула пустой ответ")
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status in {401, 403}:
                        raise ModelUnavailable(f"API модели отклонил доступ (HTTP {status})",
                                               authentication_error=True) from None
                    if status not in {429, 500, 502, 503, 504} or attempt:
                        raise ModelUnavailable(f"Ошибка API модели (HTTP {status})") from None
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
                    if attempt:
                        raise ModelUnavailable("Не удалось подключиться к модели") from None
                except (httpx.HTTPError, httpx.InvalidURL, ValueError, KeyError, TypeError, IndexError):
                    raise ModelUnavailable("Модель недоступна или вернула некорректный ответ") from None
                if self._remaining() > 1.0:
                    sleep(1.0)
        raise ModelUnavailable("Модель недоступна")
