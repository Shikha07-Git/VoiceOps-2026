"""LLM API interface for text generation and embeddings using Google Gemini."""
import json
import time
import urllib.request
import urllib.error
from typing import List, Optional, Dict, Any

from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_EMBED_MODEL


def call_gemini_api(url: str, payload: dict, max_retries: int = 6, timeout: int = 35) -> dict:
    """Make HTTP POST call to Gemini API with retries and exponential backoff."""
    data_bytes = json.dumps(payload).encode("utf-8")
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            if e.code == 429:
                wait_time = min(40, attempt * 6)
                print(f"[LLM] Rate limited (429). Waiting {wait_time}s before retry {attempt}/{max_retries}...", flush=True)
                time.sleep(wait_time)
            elif attempt == max_retries:
                raise RuntimeError(f"Gemini API HTTP Error {e.code}: {error_body}") from e
            else:
                time.sleep(attempt * 2)
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"Gemini API request failed after {max_retries} attempts: {e}") from e
            time.sleep(attempt * 2)
    raise RuntimeError("Gemini API call failed after exhausting all retries.")


def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.0,
    max_output_tokens: int = 512,
    model: str = GEMINI_MODEL
) -> str:
    """Generate text response using Gemini model."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    payload: Dict[str, Any] = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    res = call_gemini_api(url, payload)
    try:
        candidates = res.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""
        return parts[0].get("text", "").strip()
    except Exception as e:
        print(f"[LLM] Error extracting response: {e}, Raw: {res}", flush=True)
        return ""


def get_embedding(text: str, model: str = GEMINI_EMBED_MODEL) -> List[float]:
    """Retrieve vector embedding for a single text."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "content": {"parts": [{"text": text}]}
    }
    res = call_gemini_api(url, payload)
    return res.get("embedding", {}).get("values", [])


def get_embeddings_batch(texts: List[str], model: str = GEMINI_EMBED_MODEL) -> List[List[float]]:
    """Retrieve embeddings for a list of texts using batchEmbedContents in chunks of 50."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents?key={GEMINI_API_KEY}"
    all_embeddings = []
    batch_size = 50

    for i in range(0, len(texts), batch_size):
        chunk_texts = texts[i:i + batch_size]
        payload = {
            "requests": [
                {
                    "model": f"models/{model}",
                    "content": {"parts": [{"text": t}]}
                }
                for t in chunk_texts
            ]
        }
        res = call_gemini_api(url, payload)
        embeddings = res.get("embeddings", [])
        for item in embeddings:
            all_embeddings.append(item.get("values", []))
        if i + batch_size < len(texts):
            time.sleep(1.0)

    return all_embeddings
