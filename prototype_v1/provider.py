from __future__ import annotations

import json


class OpenAICompatibleProvider:
    conformance_scope = "mock-schema-only"
    production_candidate_verified = False

    def __init__(self, client, model: str):
        self.client, self.model = client, model

    def request(self, messages, tools):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=0,
                parallel_tool_calls=False,
            )
        except Exception:
            raise RuntimeError("provider request failed") from None
        choices = getattr(response, "choices", None)
        if not choices or not getattr(choices[0], "message", None):
            raise RuntimeError("invalid provider response")
        message = choices[0].message
        calls = getattr(message, "tool_calls", None)
        if calls:
            normalized = []
            for call in calls:
                function = getattr(call, "function", None)
                try:
                    arguments = json.loads(function.arguments)
                except (AttributeError, TypeError, ValueError):
                    raise ValueError("invalid provider tool arguments") from None
                if not isinstance(arguments, dict):
                    raise ValueError("invalid provider tool arguments")
                normalized.append({"name": function.name, "arguments": arguments})
            return {"tool_calls": normalized}
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            raise RuntimeError("invalid provider response")
        return {"text": content}


class GeminiNativeProvider:
    def __init__(self, client, model: str, api_key: str):
        self.client, self.model, self.api_key = client, model, api_key

    async def request(self, messages, tools):
        contents = [
            {"role": "model" if item["role"] == "assistant" else "user", "parts": [{"text": str(item["content"])}]}
            for item in messages
            if item.get("role") in {"user", "assistant"}
        ]
        payload = {"contents": contents}
        if tools:
            payload["tools"] = [{"function_declarations": [item["function"] for item in tools]}]
        try:
            response = await self.client.post(
                f"/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            parts = response.json()["candidates"][0]["content"]["parts"]
        except Exception:
            raise RuntimeError("provider request failed") from None
        calls = [part["functionCall"] for part in parts if "functionCall" in part]
        if calls:
            if any(not isinstance(call.get("name"), str) or not isinstance(call.get("args"), dict) for call in calls):
                raise ValueError("invalid provider tool arguments")
            return {"tool_calls": [{"name": call["name"], "arguments": call["args"]} for call in calls]}
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            raise RuntimeError("invalid provider response")
        return {"text": text}


Router9Provider = OpenAICompatibleProvider
