import json
import re
from abc import ABC, abstractmethod

class AIModelHandler(ABC):
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    @abstractmethod
    async def get_completion(self, prompt: str) -> str:
        pass

    def parse_json_response(self, response_text: str) -> dict:
        if not response_text:
            raise ValueError("AI response is empty.")
        # Gemini의 Markdown (` ```json ... ``` `) 제거
        match = re.search(r"```(json)?\n(.*?)```", response_text, re.DOTALL)
        json_string = match.group(2).strip() if match else response_text.strip()
        if not json_string:
            raise ValueError("AI response after cleaning is empty.")
        return json.loads(json_string)

class OpenAIHandler(AIModelHandler):
    async def get_completion(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

class GeminiHandler(AIModelHandler):
    async def get_completion(self, prompt: str) -> str:
        # self.client는 GenerativeModel 인스턴스이거나 genai 모듈일 수 있다.
        model = self.client
        try:
            # GenerativeModel 인스턴스인 경우
            generate = getattr(model, "generate_content_async", None)
            if callable(generate):
                response = await model.generate_content_async(prompt)
                return getattr(response, "text", str(response))
            # genai 모듈이 넘어온 경우
            if hasattr(model, "GenerativeModel"):
                m = model.GenerativeModel(self.model_name)
                response = await m.generate_content_async(prompt)
                return getattr(response, "text", str(response))
            raise AttributeError("Invalid Gemini client provided")
        except Exception as e:
            # 동기 API만 가능한 환경 대비 폴백
            try:
                sync_generate = getattr(model, "generate_content", None)
                if callable(sync_generate):
                    response = model.generate_content(prompt)
                    return getattr(response, "text", str(response))
            except Exception:
                pass
            raise