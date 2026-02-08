import requests
import json
import time

class GeminiLLM:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = (
            "https://generativelanguage.googleapis.com/v1/models/"
            "gemini-2.5-flash:generateContent"
        )

    def run(self, prompt: str, retries: int = 3) -> str:
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        for attempt in range(retries):
            try:
                response = requests.post(
                    f"{self.url}?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=180  # ⬅️ increased timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]

                else:
                    raise RuntimeError(
                        f"Gemini API error {response.status_code}: {response.text}"
                    )

            except requests.exceptions.ReadTimeout:
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))  # backoff
                else:
                    return (
                        "⚠️ Gemini timed out while generating this section.\n\n"
                        "Please try again or shorten the prompt."
                    )
