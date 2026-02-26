"""
DeepSeek API 集成层 — 所有与 LLM 的交互统一通过此模块
采用 OpenAI 兼容接口协议
"""

import json
import logging
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger("agent_os.llm")


class DeepSeekClient:
    """DeepSeek API 客户端，兼容 OpenAI Chat Completion 接口"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-chat", temperature: float = 0.3,
                 max_tokens: int = 4096):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.Client(timeout=120)

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages: List[Dict[str, str]],
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             response_format: Optional[Dict] = None) -> str:
        """
        发送对话请求，返回助手回复文本。
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.base_url}/chat/completions"
        logger.debug(f"[DeepSeek] 请求 → {url}, model={self.model}, msgs={len(messages)}")

        try:
            resp = self._client.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug(f"[DeepSeek] 响应 ← {len(content)} chars")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek] HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[DeepSeek] 请求失败: {e}")
            raise

    def chat_json(self, messages: List[Dict[str, str]],
                  temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        发送对话请求，期望返回 JSON 格式，自动解析。
        """
        raw = self.chat(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        # 尝试从返回中提取 JSON
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # 尝试从 markdown 代码块中提取
            if "```json" in raw:
                start = raw.index("```json") + 7
                end = raw.index("```", start)
                return json.loads(raw[start:end].strip())
            elif "```" in raw:
                start = raw.index("```") + 3
                end = raw.index("```", start)
                return json.loads(raw[start:end].strip())
            logger.error(f"[DeepSeek] 无法解析 JSON 响应: {raw[:200]}")
            return {"error": "无法解析响应", "raw": raw}

    def analyze(self, system_prompt: str, user_prompt: str,
                temperature: Optional[float] = None) -> str:
        """便捷方法：系统提示 + 用户提示 → 回复"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages, temperature=temperature)

    def analyze_json(self, system_prompt: str, user_prompt: str,
                     temperature: Optional[float] = None) -> Dict[str, Any]:
        """便捷方法：系统提示 + 用户提示 → JSON 回复"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat_json(messages, temperature=temperature)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
