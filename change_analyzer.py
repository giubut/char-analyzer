"""
变化指数分析
基于前段人格画像，评估角色在后段行为中体现的变化程度。
不是量表相减，而是AI直接判断：这个角色变了吗？变了多少？往哪变？
"""
import json
from api_client import APIClient


class ChangeAnalyzer:
    def __init__(self, client: APIClient, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def analyze(self, persona: dict, world_rules: list, actual_behavior: str,
                judgment: dict, character_name: str) -> dict:
        persona_core = json.dumps({
            "本质": persona.get("core_identity", ""),
            "思维模式": persona.get("thinking_pattern", ""),
            "底线": persona.get("bottom_line", ""),
            "隐藏矛盾": persona.get("hidden_contradictions", ""),
            "成长轨迹": persona.get("growth_arc", ""),
        }, ensure_ascii=False)

        prompt = f"""你是角色发展分析师。评估角色「{character_name}」在前后段之间的变化。

角色前段人格：
{persona_core}

后段关键场景实际行为：
{actual_behavior[:1000]}

裁判分析（可预测性:{judgment.get('predictability_score','?')}，合理性:{judgment.get('rationality_score','?')}）：
{judgment.get('overall_verdict', '')}

请完成：
1.【变化指数】(0-1)：0=无变化，0.3=明显变化，0.6=显著转变，1.0=根本性变化
2.【变化方向】：角色在往什么方向发展？
3.【变化性质】：成长/崩溃/揭示(本来就有这面)/断裂(无法解释的矛盾)

请按JSON格式输出：
{{"change_index": 0.xx, "change_direction": "变化方向描述",
  "change_nature": "成长/崩溃/揭示/断裂",
  "analysis": "详细分析：变化源头是性格内在张力的释放？外部事件冲击？还是作者设定的转变？"}}"""
        messages = [
            {"role": "system", "content": "你是角色发展分析师。基于文本证据判断，不过度解读。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.3,
                                       step="【变化分析】判断角色变化程度")
        return {
            "change_index": round(self._safe_float(result.get("change_index", 0)), 4),
            "change_direction": result.get("change_direction", ""),
            "change_nature": result.get("change_nature", ""),
            "analysis": result.get("analysis", ""),
        }

    def predict_future(self, persona: dict, world_rules: list,
                       change_analysis: dict, character_name: str) -> dict:
        persona_core = json.dumps({
            "本质": persona.get("core_identity", ""),
            "隐藏矛盾": persona.get("hidden_contradictions", ""),
            "成长轨迹": persona.get("growth_arc", ""),
        }, ensure_ascii=False)

        prompt = f"""你是角色发展预测专家。基于角色前段人格和已观察到的变化轨迹，预测未来发展方向。

角色「{character_name}」前段人格：
{persona_core}

已观察到的变化：{change_analysis.get('change_direction','')}
变化性质：{change_analysis.get('change_nature','')}

请预测：
1. 按当前轨迹，角色性格会向什么方向演变？
2. 什么因素可能加速或逆转这种变化？
3. 如果轨迹不变，角色最终可能变成什么样的人？

请按JSON格式输出：
{{"predicted_trajectory": "演变预测", "key_variables": ["变量1"],
  "possible_outcomes": "可能的最终形态"}}"""
        messages = [
            {"role": "system", "content": "你是角色发展预测专家。基于证据做合理推演。"},
            {"role": "user", "content": prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.5,
                                       step="【未来预测】推演角色发展方向")
        return {
            "predicted_trajectory": result.get("predicted_trajectory", ""),
            "key_variables": result.get("key_variables", []),
            "possible_outcomes": result.get("possible_outcomes", ""),
        }

    def _safe_float(self, val) -> float:
        try:
            return max(0.0, min(1.0, float(val)))
        except (ValueError, TypeError):
            return 0.0
