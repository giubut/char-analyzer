"""
主流程管线（Pipeline）
串联所有模块，世界观深度推演，Agent完整原文传递。
"""
import threading
import json
import time as _time
from api_client import APIClient
from text_analyzer import TextAnalyzer
from scene_selector import SceneSelector
from agent_simulator import AgentSimulator
from debate_engine import DebateEngine
from judge import Judge
from change_analyzer import ChangeAnalyzer
from report_generator import ReportGenerator
from overseer import Overseer, DataIntegrityError


class Pipeline:
    def __init__(self, base_url: str, api_key: str, model: str = "gpt-4o",
                 progress_callback=None, log_callback=None, step_callback=None):
        self.client = APIClient(base_url=base_url, api_key=api_key)
        self.model = model
        self.progress = progress_callback or (lambda msg, pct: None)
        self.log = log_callback or (lambda msg: None)
        self.step_callback = step_callback

        self.text_analyzer = TextAnalyzer(self.client, model)
        self.scene_selector = SceneSelector(self.client, model)
        self.simulator = AgentSimulator(self.client, model)
        self.debate_engine = DebateEngine(self.client, model)
        self.judge = Judge(self.client, model)
        self.change_analyzer = ChangeAnalyzer(self.client, model)
        self.report_gen = ReportGenerator()
        self.overseer = Overseer()
        self._actual_behavior = None
        self._scene_context = None

    def _emit_step(self, name: str, status: str, full: dict, dur_ms: int = 0):
        if self.step_callback:
            try:
                self.step_callback(name, status, full, dur_ms)
            except:
                pass

    def run(self, front_text: str, back_text: str, character_name: str) -> dict:
        try:
            # 阶段1：文本分析（并行）
            self.log("━━━ 阶段1：文本分析 ━━━")
            self.log("  ⏳ 并行提取人格画像+世界观...")
            self.progress("提取人格画像+世界观（并行）...", 3)
            self.overseer.start("文本分析", input_data={"text_length": len(front_text)})
            t0 = _time.time()
            text_analysis = self.text_analyzer.analyze(front_text, character_name)
            self.overseer.complete("文本分析", text_analysis, schema_key="text_analysis")
            persona = text_analysis["persona_portrait"]
            world_rules = text_analysis["world_rules"]
            self.log(f"  ✅ 人格画像（{len(persona)}维）世界观规则：{len(world_rules)}条")
            self._emit_step("文本分析", "success", persona, int((_time.time()-t0)*1000))
            self.progress("人格画像完成", 12)

            # 角色名确认检查
            if isinstance(persona, dict):
                ai_char = persona.get("character_name", "")
                if ai_char and ("未" in ai_char or "无法" in ai_char or "无" in ai_char):
                    self.log(f"  ⚠️ AI 未识别到角色「{character_name}」，终止分析")
                    return {"success": False,
                            "error": f"文本分析未识别到角色「{character_name}」。AI 返回：{ai_char}。请确认文本包含该角色的有效描述。"}

            # 阶段2：关键场景
            self.log("━━━ 阶段2：关键场景选择 ━━━")
            self.log("  ⏳ 从后段选择关键场景...")
            self.progress("选择关键场景...", 18)
            self.overseer.start("场景选择", upstream=["文本分析"])
            t0 = _time.time()
            key_scene = self.scene_selector.select(back_text, character_name)
            self.overseer.complete("场景选择", key_scene, schema_key="scene_selection")
            self._actual_behavior = key_scene["actual_behavior"]
            self._scene_context = key_scene["scene_context"]
            self.log(f"  ✅ 场景选定（{len(self._scene_context)}字）")
            self._emit_step("场景选择", "success", key_scene, int((_time.time()-t0)*1000))
            self.progress("场景选定", 25)

            # 场景选择失败检查
            # 场景选择失败检查
            check_text = (self._scene_context + key_scene.get("why_selected", "")
                          + key_scene.get("actual_behavior", ""))
            fail_words = ["未出现", "不存在", "无法选择", "无法找到", "未找到", "无法记录",
                          "未包含", "没有出现", "找不到", "未能找到", "未涉及"]
            if any(w in check_text for w in fail_words):
                self.log(f"  ⚠️ 后段文本未包含角色「{character_name}」，终止分析")
                return {"success": False,
                        "error": f"后段文本未包含角色「{character_name}」。AI 反馈：{self._scene_context[:150]}"}

            # 阶段2.5：世界观推演
            world_implications = ""
            if world_rules:
                self.log("━━━ 世界观深度推演 ━━━")
                self.log("  ⏳ 分析特殊规则对角色行为的影响...")
                self.progress("世界观推演...", 28)
                t0 = _time.time()
                world_implications = self.judge.analyze_world_impact(
                    persona, world_rules, self._scene_context, character_name)
                self.log(f"  {'✅ 推演完成' if world_implications else 'ℹ️ 无影响'}")
                self._emit_step("世界观推演", "success" if world_implications else "skipped",
                                {"analysis": world_implications}, int((_time.time()-t0)*1000))

            # 阶段3+4：双Agent并行
            self.log("━━━ 阶段3：双Agent并行模拟 ━━━")
            self.log("  ⏳ 乐观+怀疑Agent同时代入角色...")
            self.progress("双Agent并行模拟中...", 32)
            self.overseer.start("乐观模拟", upstream=["文本分析", "场景选择"])
            self.overseer.start("怀疑模拟", upstream=["文本分析", "场景选择"])

            opt_r, skp_r = [None], [None]
            opt_e, skp_e = [None], [None]
            opt_t, skp_t = [0], [0]

            def _run_opt():
                try:
                    t_ = _time.time(); opt_r[0] = self.simulator.simulate_optimistic(persona, world_rules, self._scene_context)
                    opt_t[0] = int((_time.time()-t_)*1000)
                except Exception as e: opt_e[0] = e
            def _run_skp():
                try:
                    t_ = _time.time(); skp_r[0] = self.simulator.simulate_skeptical(persona, world_rules, self._scene_context)
                    skp_t[0] = int((_time.time()-t_)*1000)
                except Exception as e: skp_e[0] = e

            t1 = threading.Thread(target=_run_opt); t2 = threading.Thread(target=_run_skp)
            t1.start(); t2.start(); t1.join(); t2.join()
            if opt_e[0]: raise opt_e[0]
            if skp_e[0]: raise skp_e[0]

            optimistic_sim, skeptical_sim = opt_r[0], skp_r[0]
            self.overseer.complete("乐观模拟", optimistic_sim, schema_key="optimistic_simulation")
            self.overseer.complete("怀疑模拟", skeptical_sim, schema_key="skeptical_simulation")
            self._emit_step("乐观模拟", "success", optimistic_sim, opt_t[0])
            self._emit_step("怀疑模拟", "success", skeptical_sim, skp_t[0])
            self.log(f"  ✅ 双路径完成")
            self.progress("双路径完成", 55)

            # 阶段5：辩论
            self.log("━━━ 阶段5：Agent辩论 ━━━")
            self.log("  ⏳ 两Agent互相审视推理...")
            self.progress("Agent辩论中...", 60)
            self.overseer.start("Agent辩论", upstream=["乐观模拟", "怀疑模拟"])
            t0 = _time.time()
            debate_result = self.debate_engine.debate(persona, world_rules, self._scene_context,
                                                       optimistic_sim, skeptical_sim, character_name)
            self.overseer.complete("Agent辩论", debate_result, schema_key="debate_result")
            self._emit_step("Agent辩论", "success", debate_result, int((_time.time()-t0)*1000))
            self.log("  ✅ 辩论完成"); self.progress("辩论完成", 70)

            # 阶段6：裁判
            self.log("━━━ 阶段6：裁判判决 ━━━")
            self.log("  ⏳ 裁判对比预测与实际行为...")
            self.progress("裁判判决中...", 73)
            self.overseer.start("裁判判决", upstream=["文本分析", "Agent辩论"])
            t0 = _time.time()
            judgment = self.judge.evaluate(persona, world_rules, self._scene_context,
                self._actual_behavior,
                optimistic_sim.get("predicted_behavior", ""),
                skeptical_sim.get("predicted_behavior", ""),
                debate_result, character_name, world_implications)
            self.overseer.complete("裁判判决", judgment, schema_key="judgment")
            self._emit_step("裁判判决", "success", judgment, int((_time.time()-t0)*1000))
            self.log(f"  ✅ 裁判：可预测={judgment.get('predictability_score','?')} 合理={judgment.get('rationality_score','?')}")
            self.progress("裁判完成", 78)

            # 阶段7：合理版本
            rational_version = {"rewritten_scene": "", "needed": False}
            if judgment.get("rationality_score", 1.0) < 0.6:
                self.log("  ⚠️ 合理性偏低，创作合理版本...")
                self.progress("合理版本...", 80)
                self.overseer.start("合理版本创作", upstream=["裁判判决"])
                t0 = _time.time()
                rational_version = self.judge.create_rational_version(
                    persona, world_rules, self._scene_context,
                    self._actual_behavior, judgment, character_name)
                self.overseer.complete("合理版本创作", rational_version, schema_key="rational_version")
                self._emit_step("合理版本创作", "success", rational_version, int((_time.time()-t0)*1000))
                self.log("  ✅ 合理版本完成")

            # 阶段8：变化分析
            self.log("━━━ 阶段8：变化指数分析 ━━━")
            self.progress("变化分析...", 85)
            self.overseer.start("变化分析", upstream=["裁判判决"])
            t0 = _time.time()
            change_analysis = self.change_analyzer.analyze(
                persona, world_rules, self._actual_behavior, judgment, character_name)
            self.overseer.complete("变化分析", change_analysis, schema_key="change_analysis")
            self._emit_step("变化分析", "success", change_analysis, int((_time.time()-t0)*1000))
            self.log(f"  ✅ 变化指数：{change_analysis.get('change_index','?')}")
            self.progress("变化分析完成", 90)

            # 阶段9：未来预测
            self.log("  ⏳ 预测角色未来发展方向...")
            self.progress("未来预测...", 93)
            self.overseer.start("未来预测", upstream=["变化分析"])
            t0 = _time.time()
            future_prediction = self.change_analyzer.predict_future(
                persona, world_rules, change_analysis, character_name)
            self.overseer.complete("未来预测", future_prediction)
            self._emit_step("未来预测", "success", future_prediction, int((_time.time()-t0)*1000))
            self.log("  ✅ 未来预测完成")
            self.progress("未来预测完成", 96)

            # === 阶段10：报告（极简版，不调用任何可能卡死的函数） ===
            self.overseer.start("报告生成", upstream=["未来预测", "裁判判决", "Agent辩论"])
            self.log("  ⏳ 生成报告...")

            try:
                ci = change_analysis.get('change_index', '?')
                pred = judgment.get('predictability_score', '?')
                rat = judgment.get('rationality_score', '?')
                verdict = judgment.get('overall_verdict', '')
                report = (
                    f"=== 角色性格变化分析结果 ===\n"
                    f"角色: {character_name}\n"
                    f"变化指数: {ci}\n"
                    f"可预测性: {pred}\n"
                    f"合理性: {rat}\n"
                    f"变化性质: {change_analysis.get('change_nature','?')}\n"
                    f"变化方向: {change_analysis.get('change_direction','?')}\n"
                    f"裁判判断: {verdict}\n"
                )
                if rational_version.get('needed') and rational_version.get('rewritten_scene'):
                    report += f"\n合理版本: {rational_version['rewritten_scene'][:300]}..."
                report += "\n（完整监工报告可通过导出查看）"
                self.log("  ✅ 报告完成")
            except Exception as e:
                self.log(f"  ⚠️ 报告异常: {e}")
                report = f"报告生成异常: {e}"

            # 这三行必须按顺序执行，全部兜住异常
            try:
                self.overseer.complete("报告生成", {"report_length": len(report)})
                self.progress("完成", 100)
            except Exception as e:
                self.log(f"  ⚠️ 标记完成异常: {e}")

            overseer_json = "{}"
            try:
                overseer_json = self.overseer.export_json()
            except Exception as e:
                self.log(f"  ⚠️ 监工导出异常: {e}")

            return {"success": True, "report": report, "overseer_json": overseer_json,
                    "change_index": change_analysis.get("change_index", 0),
                    "predictability_score": judgment.get("predictability_score", 0),
                    "rationality_score": judgment.get("rationality_score", 0),
                    "change_nature": change_analysis.get("change_nature", ""),
                    "change_direction": change_analysis.get("change_direction", ""),
                    "overall_verdict": judgment.get("overall_verdict", "")}

        except DataIntegrityError as e:
            import traceback; tb = traceback.format_exc()
            self.log(f"  ❌ 数据完整性: {e}")
            for line in tb.split("\n"):
                self.log(f"     {line}")
            self.overseer.fail("数据完整性", e)
            return {"success": False, "error": f"数据完整性校验失败：{e}\n{tb}",
                    "overseer_json": self.overseer.export_json()}
        except RuntimeError as e:
            import traceback; tb = traceback.format_exc()
            self.log(f"  ❌ API调用失败")
            for line in tb.split("\n"):
                self.log(f"     {line}")
            self.overseer.fail("API调用", e)
            return {"success": False, "error": f"API调用失败：{e}\n{tb}",
                    "overseer_json": self.overseer.export_json()}
        except Exception as e:
            import traceback; tb = traceback.format_exc()
            self.log(f"  ❌ 未知错误: {e}")
            for line in tb.split("\n"):
                self.log(f"     {line}")
            self.overseer.fail("未知错误", e)
            return {"success": False, "error": f"未知错误：{e}\n{tb}",
                    "overseer_json": self.overseer.export_json()}
