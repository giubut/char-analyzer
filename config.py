"""
配置读写 + Base64简加密 + 全局常量
"""
import os
import sys
import json
import base64

DEFAULT_BASE_URL = "https://api.openai.com/v1"
AVAILABLE_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo",
    "deepseek-chat", "deepseek-reasoner", "qwen-plus", "qwen-max",
    "glm-4-plus", "claude-3-5-sonnet",
]
REQUIRED_OUTPUT_SCHEMA = {
    "text_analysis":          ["persona_portrait", "world_rules"],
    "scene_selection":        ["scene_context", "actual_behavior"],
    "optimistic_simulation":  ["predicted_behavior", "reasoning", "inner_monologue"],
    "skeptical_simulation":   ["predicted_behavior", "reasoning", "inner_monologue"],
    "debate_result":          ["debate_summary", "consensus_points"],
    "judgment":               ["predictability_score", "rationality_score", "overall_verdict"],
    "rational_version":       ["rewritten_scene"],
    "change_analysis":        ["change_index", "analysis"],
}

CONFIG_FILE = "config.json"


def _exe_dir() -> str:
    """返回 exe 实际所在目录（打包和开发模式都适用）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _xor_mask(data: str, key: str = "char_analyzer_v1") -> str:
    result = []
    for i, c in enumerate(data):
        result.append(chr(ord(c) ^ ord(key[i % len(key)])))
    return "".join(result)


def encrypt_key(key: str) -> str:
    if not key:
        return ""
    return base64.b64encode(_xor_mask(key).encode()).decode()


def decrypt_key(encrypted: str) -> str:
    if not encrypted:
        return ""
    try:
        raw = base64.b64decode(encrypted).decode()
        return _xor_mask(raw)
    except Exception:
        return ""


def load_config() -> dict:
    path = os.path.join(_exe_dir(), CONFIG_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "api_key_encrypted" in data:
            data["api_key"] = decrypt_key(data.pop("api_key_encrypted"))
        return data
    except Exception:
        return {}


def save_config(data: dict):
    path = os.path.join(_exe_dir(), CONFIG_FILE)
    out = {}
    if "api_key" in data:
        out["api_key_encrypted"] = encrypt_key(data.pop("api_key"))
    out.update(data)
    out["_version"] = 1
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
