"""
报告生成器
整合所有模块输出，生成完整的分析报告。
"""
import json
import time


class ReportGenerator:
    """生成最终分析报告"""

    def __init__(self):
        pass

    def generate(
        self,
        character_name: str,
        text_analysis: dict,
        key_scene: dict,
        optimistic_sim: dict,
        skeptical_sim: dict,
        debate_result: dict,
        judgment: dict,
        rational_version: dict,
        change_analysis: dict,
        future_prediction: dict,
        overseer_report: str,
    ) -> str:
        """生成完整报告，纯文本格式"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  角色性格变化分析报告")
        lines.append(f"  角色：{character_name}")
        lines.append(f"  生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # === 一、核心分数 ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  一、核心分数")
        lines.append("━" * 70)
        lines.append("")
        lines.append(f"  变化指数：    {self._bar(change_analysis.get('change_index', 0))} {change_analysis.get('change_index', 0)}")
        lines.append(f"  可预测性：    {self._bar(judgment.get('predictability_score', 0))} {judgment.get('predictability_score', 0)}")
        lines.append(f"  合理性：      {self._bar(judgment.get('rationality_score', 0))} {judgment.get('rationality_score', 0)}")
        lines.append("")
        lines.append(f"  变化性质：{change_analysis.get('change_nature', '')}")
        lines.append(f"  变化方向：{change_analysis.get('change_direction', '')}")

        # === 二、角色前段人格画像 ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  二、角色前段人格画像")
        lines.append("━" * 70)
        lines.append("")
        persona = text_analysis.get("persona_portrait", {})
        sections = [
            ("核心本质", "core_identity"),
            ("思维模式", "thinking_pattern"),
            ("决策优先级", "decision_priority"),
            ("情感触发点", "emotional_triggers"),
            ("底线", "bottom_line"),
            ("行为习惯", "behavioral_habits"),
            ("隐藏矛盾", "hidden_contradictions"),
            ("成长轨迹（前段可见）", "growth_arc"),
        ]
        for label, key in sections:
            val = persona.get(key, "")
            if val:
                lines.append(f"  ▸ {label}")
                lines.append(f"    {val}")
                lines.append("")

        # === 三、关键场景 ===
        lines.append("━" * 70)
        lines.append("  三、关键场景（后段）")
        lines.append("━" * 70)
        lines.append("")
        lines.append(f"  【场景前提】")
        lines.append(f"  {key_scene.get('scene_context', '')[:800]}")
        lines.append("")
        lines.append(f"  【角色实际行为】")
        lines.append(f"  {key_scene.get('actual_behavior', '')[:800]}")

        # === 四、沙盘推演 ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  四、沙盘推演：角色模拟")
        lines.append("━" * 70)
        lines.append("")

        lines.append("  ▸ 乐观模拟（最常规路径）")
        lines.append("")
        if optimistic_sim.get("inner_monologue"):
            lines.append(f"  【内心独白】")
            lines.append(f"  {optimistic_sim['inner_monologue'][:500]}")
            lines.append("")
        lines.append(f"  【预测行为】")
        lines.append(f"  {optimistic_sim.get('predicted_behavior', '')[:500]}")
        lines.append("")
        lines.append(f"  【推理】")
        lines.append(f"  {optimistic_sim.get('reasoning', '')[:500]}")
        lines.append("")

        lines.append("  ▸ 怀疑模拟（最意外但逻辑自洽路径）")
        lines.append("")
        if skeptical_sim.get("inner_monologue"):
            lines.append(f"  【内心独白】")
            lines.append(f"  {skeptical_sim['inner_monologue'][:500]}")
            lines.append("")
        lines.append(f"  【预测行为】")
        lines.append(f"  {skeptical_sim.get('predicted_behavior', '')[:500]}")
        lines.append("")
        lines.append(f"  【推理】")
        lines.append(f"  {skeptical_sim.get('reasoning', '')[:500]}")

        # === 五、辩论分析 ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  五、Agent辩论分析")
        lines.append("━" * 70)
        lines.append("")

        if debate_result.get("optimistic_challenges"):
            lines.append("  ▸ 乐观方对怀疑方的质疑")
            for c in debate_result["optimistic_challenges"]:
                lines.append(f"    · {c}")
            lines.append("")

        if debate_result.get("skeptical_challenges"):
            lines.append("  ▸ 怀疑方对乐观方的质疑")
            for c in debate_result["skeptical_challenges"]:
                lines.append(f"    · {c}")
            lines.append("")

        if debate_result.get("consensus_points"):
            lines.append("  ▸ 双方共识")
            for c in debate_result["consensus_points"]:
                lines.append(f"    · {c}")
            lines.append("")

        if debate_result.get("core_disagreement"):
            lines.append(f"  ▸ 核心分歧")
            lines.append(f"    {debate_result['core_disagreement']}")
            lines.append("")

        lines.append(f"  ▸ 辩论总结")
        lines.append(f"    {debate_result.get('debate_summary', '')}")

        # === 六、裁判判决 ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  六、裁判判决")
        lines.append("━" * 70)
        lines.append("")
        lines.append(f"  ▸ 可预测性分析")
        lines.append(f"    {judgment.get('predictability_analysis', '')}")
        lines.append("")
        lines.append(f"  ▸ 合理性分析")
        lines.append(f"    {judgment.get('rationality_analysis', '')}")
        lines.append("")
        lines.append(f"  ▸ 整体判断")
        lines.append(f"    {judgment.get('overall_verdict', '')}")

        # === 七、合理版本（如果有） ===
        if rational_version.get("needed") and rational_version.get("rewritten_scene"):
            lines.append("")
            lines.append("━" * 70)
            lines.append("  七、合理版本（建议）")
            lines.append("━" * 70)
            lines.append("")
            lines.append(f"  裁判认为原文行为合理性偏低（{judgment.get('rationality_score', '?')}）。")
            lines.append(f"  以下是基于前段人格逻辑创作的合理版本，供参考：")
            lines.append("")
            lines.append(f"  {rational_version.get('rewritten_scene', '')}")
            lines.append("")
            if rational_version.get('rewrite_rationale'):
                lines.append(f"  ▸ 创作依据")
                lines.append(f"    {rational_version['rewrite_rationale']}")

        # === 八、变化分析与未来预测 ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  八、变化分析与未来预测")
        lines.append("━" * 70)
        lines.append("")
        lines.append(f"  ▸ 变化分析")
        lines.append(f"    {change_analysis.get('analysis', '')}")
        lines.append("")
        if future_prediction.get("predicted_trajectory"):
            lines.append(f"  ▸ 未来发展方向预测")
            lines.append(f"    {future_prediction['predicted_trajectory']}")
            lines.append("")
            if future_prediction.get("key_variables"):
                lines.append(f"  ▸ 关键变量")
                for v in future_prediction["key_variables"]:
                    lines.append(f"    · {v}")
            lines.append("")
            lines.append(f"  ▸ 可能的最终形态")
            lines.append(f"    {future_prediction.get('possible_outcomes', '')}")

        # === 九、监工追溯（摘要） ===
        lines.append("")
        lines.append("━" * 70)
        lines.append("  九、监工追溯摘要")
        lines.append("━" * 70)
        lines.append("")
        lines.append("  （完整追溯报告可通过'导出监工报告'按钮查看）")
        lines.append("")
        # 提取执行步骤摘要
        try:
            data = json.loads(overseer_report)
            for name in data.get("execution_order", []):
                rec = data["steps"].get(name, {})
                icon = "✅" if rec.get("status") == "success" else "❌"
                dur = rec.get("duration_ms", "?")
                lines.append(f"  {icon} {name}（{dur}ms）")
        except:
            lines.append("  （监工数据解析失败）")

        lines.append("")
        lines.append("=" * 70)
        lines.append("  报告结束")
        lines.append("=" * 70)

        return "\n".join(lines)

    def _bar(self, value: float, width: int = 20) -> str:
        """生成简单的进度条"""
        if value is None:
            value = 0
        filled = int(value * width)
        return f"[{'█' * filled}{'░' * (width - filled)}]"
