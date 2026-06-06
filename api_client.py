"""
LLM API 调用客户端
支持 OpenAI 兼容格式，自动重试，详细错误上下文。
"""
import json
import time
import urllib.request
import urllib.error
import ssl
from config import DEFAULT_BASE_URL


class APIClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or ""
        self._ssl_context = ssl.create_default_context()

    def _ctx(self, step, model, url, extra=""):
        parts = [f"API调用失败", f"步骤: {step}", f"模型: {model}", f"端点: {url}"]
        if extra:
            parts.append(extra)
        return "\n".join(parts)

    def call(self, messages, model="gpt-4o", temperature=0.7,
             max_tokens=4096, timeout=180, step="未知步骤", retries=1):
        url = f"{self.base_url}/chat/completions"
        payload = {"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        data = json.dumps(payload).encode("utf-8")

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {self.api_key}")
                resp = urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context)
                body = resp.read().decode("utf-8")
                result = json.loads(body)

                choices = result.get("choices")
                if not choices or not isinstance(choices, list) or len(choices) == 0:
                    if attempt < retries:
                        time.sleep(3 * (attempt + 1))
                        continue
                    raise RuntimeError(self._ctx(step, model, url,
                        f"choices为空(已重试{retries}次)\n响应: {body[:300]}"))

                msg = choices[0].get("message")
                if not msg or not msg.get("content"):
                    if attempt < retries:
                        time.sleep(3 * (attempt + 1))
                        continue
                    raise RuntimeError(self._ctx(step, model, url,
                        f"message/content为空(已重试{retries}次)\n响应: {body[:300]}"))

                return msg["content"]

            except urllib.error.HTTPError as e:
                eb = e.read().decode("utf-8", errors="replace")
                if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(3 * (attempt + 1))
                    continue
                extra = f"HTTP {e.code}\n{eb[:400]}"
                if e.code == 401: extra += "\nKey无效"
                elif e.code == 402: extra += "\n余额不足"
                elif e.code == 403: extra += "\n无权限"
                elif e.code == 404: extra += "\nURL/模型名错"
                elif e.code == 429: extra += "\n限流/额度用完"
                raise RuntimeError(self._ctx(step, model, url, extra))

            except (urllib.error.URLError, OSError) as e:
                reason = str(getattr(e, 'reason', e))
                if "timed out" in reason.lower() and attempt < retries:
                    time.sleep(5)
                    continue
                if attempt < retries:
                    time.sleep(3 * (attempt + 1))
                    continue
                if "timed out" in reason.lower():
                    raise RuntimeError(self._ctx(step, model, url,
                        f"请求超时(已重试{retries}次)\nAPI服务器响应过慢，请稍后重试或更换API提供商"))
                raise RuntimeError(self._ctx(step, model, url, f"网络不通: {reason}"))

            except RuntimeError:
                raise

            except json.JSONDecodeError as e:
                raise RuntimeError(self._ctx(step, model, url,
                    f"JSON解析失败: {e}\n{body[:300]}"))

            except (KeyError, IndexError, TypeError) as e:
                raise RuntimeError(self._ctx(step, model, url,
                    f"响应格式异常: {e}\n{body[:300]}"))

    def call_json(self, messages, model="gpt-4o", temperature=0.3,
                  max_tokens=4096, timeout=120, step="未知步骤"):
        json_instruction = ("\n\n请严格按照JSON格式输出，不要包含markdown代码块标记，"
                            "直接输出纯JSON对象。注意JSON键名、冒号、逗号、引号、花括号"
                            "必须全部使用英文半角符号，禁止中文全角标点。")
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = messages[0]["content"] + json_instruction
        else:
            messages.insert(0, {"role": "system", "content": json_instruction})

        raw = self.call(messages, model=model, temperature=temperature,
                        max_tokens=max_tokens, timeout=timeout, step=step)
        try:
            return self._parse_json(raw)
        except json.JSONDecodeError as e:
            repaired = self._repair_truncated_json(raw)
            if repaired is not None:
                return repaired
            raise RuntimeError(self._ctx(step, model,
                f"{self.base_url}/chat/completions",
                f"AI未返回有效JSON\n{e}\n{raw[:500]}"))

    def _parse_json(self, raw):
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 1:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return json.loads(text)

    def _repair_truncated_json(self, raw):
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 1:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        if not text.startswith("{"):
            return None

        import re
        pairs = list(re.finditer(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?', text))
        if len(pairs) >= 3:
            parts = []
            for i, m in enumerate(pairs):
                key = m.group(1)
                val = m.group(2)
                comma = "," if i < len(pairs) - 1 else ""
                parts.append(f'  "{key}": "{val}"{comma}')
            candidate = "{\n" + "\n".join(parts) + "\n}"
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        for i in range(len(text) - 1, max(len(text) - 500, 0), -1):
            if text[i] == '"':
                try:
                    result = json.loads(text[:i+1] + "\n}")
                    if isinstance(result, dict) and len(result) >= 3:
                        return result
                except json.JSONDecodeError:
                    continue

        for suffix in ["\n}", "}"]:
            try:
                return json.loads(text.rstrip().rstrip(",") + suffix)
            except json.JSONDecodeError:
                pass
        return None
