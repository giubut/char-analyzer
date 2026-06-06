"""
裁判模块
新增：世界观深度推演，让裁判基于特殊规则重新审视合理性。
"""
import json
from api_client import APIClient


class Judge:
    def __init__(self, client: APIClient, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def analyze_world_impact(self, persona: dict, world_rules: list,
                             scene_context: str, character_name: str) -> str:
        """
        世界观深度推演：在 Agent 模拟之前，先分析世界观特殊规则
        对角色行为可能产生的影响。输出直接传递给裁判，不污染 Agent。
        """
        if not world_rules:
            return ""

        persona_core = json.dumps({
            "本质": persona.get("core_identity", ""),
            "底线": persona.get("bottom_line", ""),
        }, ensure_ascii=False)

        rules_text = json.dumps(world_rules, ensure_ascii=False, indent=2)

        prompt = f"""你是一位世界观逻辑分析师。角色「{character_name}」所在的世界存在特殊规则。

世界观规则：
{rules_text}

角色前段人格：
{persona_core}

场景前提：
{scene_context[:1000]}

请分析以下问题：
1. 这些世界观规则是否可能导致角色在后段表现出与前段人格不一致的行为？
   （比如：记忆可以被删除 → 角色性情大变可能是被洗脑 → 看似不合理的突变实际上合理）
2. 是否有某种世界观规则可以解释角色看似崩坏的行为？
3. 如果完全没有特殊规则影响，标记为"无特殊影响"。

请直接输出分析文字（非JSON），150字以内。"""
        messages = [
            {"role": "system", "content": "你分析世界观规则对角色行为的影响。始终用中文输出。不要JSON。"},
            {"role": "user", "content": prompt},
        ]
        try:
            result = self.client.call(messages, model=self.model, temperature=0.3,
                                      max_tokens=500, step="【世界观推演】规则深度分析")
            return result.strip()
        except Exception:
            return ""

    def evaluate(self, persona: dict, world_rules: list, scene_context: str,
                 actual_behavior: str, optimistic_prediction: str,
                 skeptical_prediction: str, debate_result: dict,
                 character_name: str, world_implications: str = "") -> dict:
        persona_summary = json.dumps({
            "本质": persona.get("core_identity", ""),
            "思维模式": persona.get("thinking_pattern", ""),
            "底线": persona.get("bottom_line", ""),
            "隐藏矛盾": persona.get("hidden_contradictions", ""),
        }, ensure_ascii=False)
        rules_text = json.dumps(world_rules, ensure_ascii=False) if world_rules else "无"
        debate_summary = debate_result.get("debate_summary", "")
        world_section = ""
        if world_implications:
            world_section = f"\n【世界观影响分析——裁判已考虑以下因素】\n{world_implications}\n"

        prompt = f"""你是公正的叙事裁判。请评估角色「{character_name}」的行为分析。

角色前段人格：
{persona_summary}

世界观规则：
{rules_text}{world_section}

场景前提：
{scene_context[:1500]}

乐观Agent预测：{optimistic_prediction[:800]}
怀疑Agent预测：{skeptical_prediction[:800]}
辩论总结：{debate_summary[:500]}

角色实际行为（后段原文）：
{actual_behavior}

请完成以下判断：

【可预测性分数】(0-1)：取两个预测中与实际行为语义相似度较高者。
注意：如果世界观规则可能导致行为变异，可预测性可以降低。

【合理性分数】(0-1)：独立判断实际行为在(前段性格+世界观规则)下是否合情合理。
"意外"≠"不合理"。世界观规则可以改变合理性判断：
- 如果规则解释得通：即使行为与前段性格矛盾，也可以得高合理性分
- 如果没有规则能解释：才是真正的崩坏，得低分

请按JSON格式输出：
{{"predictability_score": 0.xx, "predictability_analysis": "...",
  "rationality_score": 0.xx, "rationality_analysis": "...",
  "overall_verdict": "..."}}"""
        messages = [
            {"role": "system", "content": "你是公正的叙事裁判。区分'可预测'和'合理'，考虑世界观规则的影响。始终用中文回答。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.2,
                                       max_tokens=4096, step="【裁判】对比预测与实际行为")
        return {
            "predictability_score": round(self._safe_float(result.get("predictability_score", 0.5)), 4),
            "predictability_analysis": result.get("predictability_analysis", ""),
            "rationality_score": round(self._safe_float(result.get("rationality_score", 0.5)), 4),
            "rationality_analysis": result.get("rationality_analysis", ""),
            "overall_verdict": result.get("overall_verdict", ""),
        }

    def create_rational_version(self, persona: dict, world_rules: list,
                                scene_context: str, actual_behavior: str,
                                judgment: dict, character_name: str) -> dict:
        rationality = judgment.get("rationality_score", 1.0)
        if rationality >= 0.6:
            return {"rewritten_scene": "", "needed": False}
        persona_summary = json.dumps({
            "本质": persona.get("core_identity", ""),
            "思维模式": persona.get("thinking_pattern", ""),
            "底线": persona.get("bottom_line", ""),
            "隐藏矛盾": persona.get("hidden_contradictions", ""),
        }, ensure_ascii=False)
        prompt = f"""你是叙事创作者。裁判认为以下角色行为不合理（{rationality}）。

角色「{character_name}」前段人格：
{persona_summary}

场景前提：
{scene_context[:1500]}

原文（不合理版本）：
{actual_behavior[:800]}

裁判分析：{judgment.get('rationality_analysis', '')[:500]}

请创作"合理版本"：同样场景下，角色按前段性格逻辑应该怎么做。
保持原文文风。合理≠常规，性格有矛盾则展现张力。

JSON输出：
{{"rewritten_scene": "重写场景（200-500字）", "rewrite_rationale": "依据"}}"""
        messages = [
            {"role": "system", "content": "你是尊重原文风格的叙事创作者。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.7,
                                       max_tokens=4096, step="【合理版本】创作替代场景")
        return {
            "rewritten_scene": result.get("rewritten_scene", ""),
            "rewrite_rationale": result.get("rewrite_rationale", ""),
            "needed": True,
        }

    def _safe_float(self, val) -> float:
        try:
            return max(0.0, min(1.0, float(val)))
        except (ValueError, TypeError):
            return 0.5
