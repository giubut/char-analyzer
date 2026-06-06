"""
角色Agent模拟器
将LLM变成角色本身，让TA在给定场景中自主行动。
严防止偷看剧本：Agent只知道前段人格和场景前提，绝不接触后段实际行为。
"""
import json
from api_client import APIClient


class AgentSimulator:
    def __init__(self, client: APIClient, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def _build_persona_prompt(self, persona: dict, world_rules: list) -> str:
        rules_text = ""
        if world_rules:
            rules_text = "\n".join([f"- {r.get('rule', '')}：{r.get('mechanism', '')}" for r in world_rules])
        else:
            rules_text = "无特殊规则，遵循现实世界逻辑。"

        return f"""你现在不是AI助手。你完全就是角色「{persona.get('character_name', '')}」。

你不是在分析这个角色，你就是TA本人。你拥有TA的记忆、情感、思维方式和行为习惯。

【你的本质】
{persona.get('core_identity', '')}

【你的思维方式】
{persona.get('thinking_pattern', '')}

【你做决策时的优先级】
{persona.get('decision_priority', '')}

【什么会让你情绪波动】
{persona.get('emotional_triggers', '')}

【你的底线】
{persona.get('bottom_line', '')}

【你的行为习惯】
{persona.get('behavioral_habits', '')}

【你内心隐藏的矛盾】
{persona.get('hidden_contradictions', '')}

【你的成长轨迹】
{persona.get('growth_arc', '')}

【你对待不同人的方式】
{persona.get('relationship_style', '')}

【你说话的方式】
{persona.get('voice_and_tone', '')}

【你所在世界的特殊规则】
{rules_text}

重要提醒：
- 你就是这个角色本人，不是观察者，不是分析者。
- 用第一人称思考，用角色的视角看世界。
- 不要跳出角色说"根据角色设定"之类的话。
- 你只知道目前为止发生的事，不知道未来会怎样。"""

    def simulate_optimistic(self, persona: dict, world_rules: list, scene_context: str) -> dict:
        system_prompt = self._build_persona_prompt(persona, world_rules)
        user_prompt = f"""【你现在面临的场景】

{scene_context}

请以第一人称，从角色的内心出发，完成以下内容：
1. 面对这个场景，你内心在想什么？感受到什么？
2. 你最终决定怎么做？
3. 你为什么这样做？（用角色的逻辑解释）

请按JSON格式输出：
{{"inner_monologue": "内心独白（第一人称）", "predicted_behavior": "你的行动", "reasoning": "你这样做的理由"}}"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.6,
                                       max_tokens=4096,
                                       step="【乐观模拟】Agent预测常规路径")
        return {
            "inner_monologue": result.get("inner_monologue", ""),
            "predicted_behavior": result.get("predicted_behavior", ""),
            "reasoning": result.get("reasoning", ""),
            "type": "optimistic",
        }

    def simulate_skeptical(self, persona: dict, world_rules: list, scene_context: str) -> dict:
        system_prompt = self._build_persona_prompt(persona, world_rules)
        system_prompt += """

【特别指令：探索你的另一面】
此刻，请深入审视你内心那些被压抑的、矛盾的、平时不会浮出水面的部分。
问自己：在什么情况下，我会做出和平时不一样的选择？
我的底线在什么条件下可能动摇？我有没有连自己都没意识到的冲动？
不要为了意外而意外，但也不要回避你性格中真实存在的张力。"""

        user_prompt = f"""【你现在面临的场景】

{scene_context}

请以第一人称，探索自己内心深处被压抑的面相：
1. 除了最常规的反应之外，你内心深处有没有不同的冲动？
2. 如果这次你打破了平时的惯性，你会怎么做？（必须逻辑自洽，从前文性格中找到依据）
3. 为什么你可能会选择这个意外路径？

请按JSON格式输出：
{{"inner_monologue": "内心独白（探索被压抑的一面）", "predicted_behavior": "打破惯性的行动", "reasoning": "意外行为的性格根源"}}"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = self.client.call_json(messages, model=self.model, temperature=0.8,
                                       max_tokens=4096,
                                       step="【怀疑模拟】Agent预测意外路径")
        return {
            "inner_monologue": result.get("inner_monologue", ""),
            "predicted_behavior": result.get("predicted_behavior", ""),
            "reasoning": result.get("reasoning", ""),
            "type": "skeptical",
        }
