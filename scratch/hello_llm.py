import time
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "dolphin-llama3:8b"


def chat(messages, model=MODEL, json_mode=False):
    """Gui danh sach tin nhan cho Ollama, tra ve toan bo phan hoi."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 256,
        },
    }
    
    if json_mode:
        payload["format"] = "json"       # ép model chỉ trả về JSON
        
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Lỗi kết nối tới Ollama: {e}")
        return None

if __name__ == "__main__":
    messages = [
        {"role": "system",
         "content": "You are an office assistant. Answer briefly in English."},
        {"role": "user",
         "content": "Summarize in one sentence: The team meeting is moved to Friday at 3pm."},
    ]

    start = time.time()
    data = chat(messages)
    elapsed = time.time() - start

    print("Tra loi:", data["message"]["content"])
    print(f"Thoi gian: {elapsed:.1f}s")
    # eval_duration tinh bang nano giay
    tps = data["eval_count"] / (data["eval_duration"] / 1e9)
    print(f"Toc do: {tps:.1f} tokens/s")