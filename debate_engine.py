"""
辩论引擎
两个角色Agent完成各自模拟后，互相审视对方的推理，进行结构化辩论。
辩论过程不涉及后段实际行为。
"""
from api_client import APIClient


class DebateEngine:
    def __init__(self, client: APIClient, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def debate(self, persona: dict, world_rules: list, scene_context: str,
               optimistic_result: dict, skeptical_result: dict, character_name: str) -> dict:
        persona_summary = f"""角色「{character_name}」前段人格核心：
本质：{persona.get('core_identity', '')}
思维模式：{persona.get('thinking_pattern', '')}
决策优先级：{persona.get('decision_priority', '')}
底线：{persona.get('bottom_line', '')}
隐藏矛盾：{persona.get('hidden_contradictions', '')}"""

        rules_summary = "\n".join([f"- {r.get('rule', '')}" for r in world_rules]) if world_rules else "无特殊规则"

        opt_summary = f"""【乐观路径预测】
内心独白：{optimistic_result.get('inner_monologue', '')[:500]}
预测行为：{optimistic_result.get('predicted_behavior', '')[:500]}
推理：{optimistic_result.get('reasoning', '')[:500]}"""

        skp_summary = f"""【怀疑路径预测】
内心独白：{skeptical_result.get('inner_monologue', '')[:500]}
预测行为：{skeptical_result.get('predicted_behavior', '')[:500]}
推理：{skeptical_result.get('reasoning', '')[:500]}"""

        debate_prompt = f"""你是公正的辩论主持人。以下是两个不同倾向的AI分别代入角色「{character_name}」后对同一场景的行为预测。

角色前段人格：
{persona_summary}

世界观规则：
{rules_summary}

场景前提：
{scene_context[:1000]}

---
{opt_summary}

---
{skp_summary}
---

请完成：
1. 乐观预测对怀疑预测可能提出的质疑（3-5条）
2. 怀疑预测对乐观预测可能提出的质疑（3-5条）
3. 分析双方回应质疑的有效性
4. 列出共识点
5. 核心分歧是什么
6. 两种预测的深层动机分析
7. 辩论总结：哪种预测更站得住脚？

请按JSON格式输出：
{{"optimistic_challenges": ["质疑1"], "skeptical_challenges": ["质疑1"], "response_analysis": "分析",
  "consensus_points": ["共识1"], "core_disagreement": "核心分歧", "motivation_analysis": "动机分析",
  "debate_summary": "辩论总结"}}"""
        messages = [
            {"role": "system", "content": "你是专业的叙事辩论主持人。请公正客观地分析双方的推理。"},
            {"role": "user", "content": debate_prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.4,
                                       step="【辩论】Agent互相质疑推理")
        return {
            "optimistic_challenges": result.get("optimistic_challenges", []),
            "skeptical_challenges": result.get("skeptical_challenges", []),
            "response_analysis": result.get("response_analysis", ""),
            "consensus_points": result.get("consensus_points", []),
            "core_disagreement": result.get("core_disagreement", ""),
            "motivation_analysis": result.get("motivation_analysis", ""),
            "debate_summary": result.get("debate_summary", ""),
        }
