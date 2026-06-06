"""
文本分析模块
从小说前段提取角色人格画像和世界观特殊规则。
人格画像是自然语言描述，不是打分表。目的是让Agent能真正代入角色。
"""
from api_client import APIClient


class TextAnalyzer:
    """从小说文本中提取角色人格画像和世界观规则"""

    def __init__(self, client: APIClient, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def extract_persona(self, front_text: str, character_name: str) -> dict:
        prompt = f"""你是一位深度角色分析师。请阅读以下小说前段文本，为角色「{character_name}」构建一份"人格操作系统"。

这份描述的目标是：让一个完全不了解这个角色的AI，读完你的描述后能够准确模拟该角色的思考和行为。

请按以下JSON格式输出（只输出JSON，不要markdown包装）：

{{
    "core_identity": "一句话定义：这个角色的本质是什么？",
    "thinking_pattern": "思维模式：TA怎么想问题？理性还是直觉？长远规划还是活在当下？",
    "decision_priority": "决策优先级：面对选择时TA优先考虑什么？排序并解释",
    "emotional_triggers": "情感触发点：什么事会让TA愤怒/恐惧/心软/兴奋？",
    "bottom_line": "底线：什么事TA绝对不会做？什么情境下TA会打破原则？",
    "behavioral_habits": "行为习惯：遇到冲突、压力、关心他人时的典型模式",
    "hidden_contradictions": "隐藏矛盾：性格中的内在张力，什么条件下可能爆发？",
    "growth_arc": "成长轨迹（前段可见的）：已经或正在经历什么变化？",
    "relationship_style": "人际风格：怎么对待亲近的人、敌人、陌生人、弱者？",
    "voice_and_tone": "语言风格：用词文雅还是粗俗？句子长还是短？口头禅？"
}}

重要：
1. 只基于前段文本证据，不要推测后段。
2. 证据不足处标注"文本中未充分展示"。
3. 每个描述都要有文本依据，拒绝空洞形容词。

文本内容（前段）：
{front_text[:20000]}
"""
        messages = [
            {"role": "system", "content": "你是深度角色分析师。请给出具体、可操作的人格描述。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.3,
                                       max_tokens=8192,
                                       step="【文本分析】提取人格画像")
        return {
            "character_name": character_name,
            "core_identity": result.get("core_identity", ""),
            "thinking_pattern": result.get("thinking_pattern", ""),
            "decision_priority": result.get("decision_priority", ""),
            "emotional_triggers": result.get("emotional_triggers", ""),
            "bottom_line": result.get("bottom_line", ""),
            "behavioral_habits": result.get("behavioral_habits", ""),
            "hidden_contradictions": result.get("hidden_contradictions", ""),
            "growth_arc": result.get("growth_arc", ""),
            "relationship_style": result.get("relationship_style", ""),
            "voice_and_tone": result.get("voice_and_tone", ""),
        }

    def extract_world_rules(self, front_text: str) -> list[dict]:
        prompt = f"""请从以下小说文本中提取所有"非现实世界观规则"。

注意：只提取不同于现实世界的特殊设定（如记忆抹除、时间回溯、超能力等）。普通时代背景不算。

请按JSON格式输出：
{{"world_rules": [{{"rule": "规则描述", "mechanism": "运作方式", "impact_on_character": "对角色行为的影响"}}]}}

如果无特殊规则返回 {{"world_rules": []}}

文本内容：
{front_text[:15000]}
"""
        messages = [
            {"role": "system", "content": "你是世界观分析专家。只提取非现实世界的特殊设定。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.2,
                                       step="【文本分析】提取世界观规则")
        return result.get("world_rules", [])

    def identify_characters(self, front_text: str, back_text: str = "") -> list[str]:
        combined = front_text[:8000]
        if back_text:
            combined += "\n\n" + back_text[:4000]
        prompt = f"""请从以下小说文本中提取所有主要角色（有名字、有对话或有明确行为的角色）。
只返回角色的名字，每行一个，不要编号，不要其他描述。按重要性排序。

文本内容：
{combined}"""
        messages = [
            {"role": "system", "content": "你是角色识别助手。只返回角色名列表，每行一个。"},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self.client.call(messages, model=self.model, temperature=0.1, max_tokens=500,
                                   step="【文本分析】扫描角色列表")
            lines = [line.strip() for line in raw.strip().split("\n") if line.strip()]
            seen = set()
            result = []
            for line in lines:
                line = line.lstrip("0123456789.、- )")
                if line and line not in seen:
                    seen.add(line)
                    result.append(line)
            return result[:20]
        except Exception:
            return []

    def analyze(self, front_text: str, character_name: str) -> dict:
        """并行提取人格画像和世界观规则"""
        import threading
        persona_result = [None]
        rules_result = [None]
        persona_err = [None]
        rules_err = [None]

        def _get_persona():
            try:
                persona_result[0] = self.extract_persona(front_text, character_name)
            except Exception as e:
                persona_err[0] = e

        def _get_rules():
            try:
                rules_result[0] = self.extract_world_rules(front_text)
            except Exception as e:
                rules_err[0] = e

        t1 = threading.Thread(target=_get_persona)
        t2 = threading.Thread(target=_get_rules)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        if persona_err[0]:
            raise persona_err[0]
        if rules_err[0]:
            raise rules_err[0]

        return {"persona_portrait": persona_result[0], "world_rules": rules_result[0]}
