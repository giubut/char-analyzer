"""
关键场景选择器
从后段文本中自动选择一个最适合做性格推演的关键场景。
信息隔离：场景前提和实际行为严格分离，Agent永远看不到实际行为。
"""
from api_client import APIClient


class SceneSelector:
    def __init__(self, client: APIClient, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def select(self, back_text: str, character_name: str) -> dict:
        prompt = f"""你是一位叙事分析师。请从以下小说后段文本中，为角色「{character_name}」选择一个最适合做性格推演的关键场景。

选择标准：
1. 角色面临明确的选择、决策或考验（非被动反应）
2. 对角色性格展示或变化有重要意义
3. 有足够上下文支撑推演

请按JSON格式输出：
{{
    "scene_context": "【重要】场景前提描述：背景、角色处境、面临的抉择、可选方向、所有影响决策的信息。只写到角色即将行动的那一刻就停笔，绝对不要透露角色最终做了什么。",
    "actual_behavior": "角色实际做出的行为和选择。这部分将不会展示给模拟角色的Agent。",
    "why_selected": "选择这个场景的原因"
}}

文本内容（后段）：
{back_text[:18000]}
"""
        messages = [
            {"role": "system", "content": "你是叙事分析师。场景前提与实际行为必须严格分离，前提中绝不泄露实际行为。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.4,
                                       step="【场景选择】从后段选关键场景")
        return {
            "scene_context": result.get("scene_context", ""),
            "actual_behavior": result.get("actual_behavior", ""),
            "why_selected": result.get("why_selected", ""),
        }
