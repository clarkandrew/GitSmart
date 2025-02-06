import json
import requests
from typing import List, Dict, Optional, Callable

from .config import AUTH_TOKEN, API_URL

def get_chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    stream: bool = True,
    timeout: int = 60,
    status_callback: Optional[Callable[[str], None]] = None,
    provider: str = "httprequest"
) -> str:
    """
    Calls the LLM provider and returns a streaming chat completion.
    The 'provider' argument allows for additional implementations
    (e.g., provider='mlx' can be supported later).
    """
    if provider == "httprequest":
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "n": 1,
            "stop": None,
            "temperature": temperature,
            "stream": stream
        }
        response = requests.post(API_URL, headers=headers, json=body, stream=stream, timeout=timeout)
        response.raise_for_status()
        result = ""
        for chunk in response.iter_lines():
            if chunk:
                chunk_data = chunk.decode("utf-8").strip()
                if chunk_data.startswith("data: "):
                    chunk_data = chunk_data[6:]
                    try:
                        data = json.loads(chunk_data)
                        delta_content = data["choices"][0]["delta"].get("content", "")
                        result += delta_content
                        if status_callback is not None:
                            status_callback(result)
                    except json.JSONDecodeError:
                        continue
        return result
    elif provider == "mlx":
        # In the future, add native support for the MLX provider here.
        raise NotImplementedError("MLX provider not implemented yet")
    else:
        raise ValueError(f"Unknown provider: {provider}")
