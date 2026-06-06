"""
监工系统 V2（Overseer）
全程追踪数据流，支持完整原文存储（Agent推理不截断）。
"""
import json
import time
from config import REQUIRED_OUTPUT_SCHEMA


class DataIntegrityError(Exception):
    pass


class StepRecord:
    def __init__(self, step_name: str, upstream: list[str] = None):
        self.step_name = step_name
        self.upstream = upstream or []
        self.downstream = []
        self.input_data = None
        self.output_data = None
        self.full_output = None      # Agent推理完整原文
        self.start_time = None
        self.end_time = None
        self.status = "pending"
        self.error = None

    def to_dict(self) -> dict:
        return {
            "step": self.step_name,
            "upstream": self.upstream,
            "downstream": self.downstream,
            "input_summary": self._summarize(self.input_data),
            "output_summary": self._summarize(self.output_data),
            "full_output": self.full_output,
            "duration_ms": (
                int((self.end_time - self.start_time) * 1000)
                if self.start_time and self.end_time
                else None
            ),
            "status": self.status,
            "error": self.error,
        }

    def _summarize(self, data) -> str:
        if data is None:
            return "(无)"
        if isinstance(data, dict):
            keys = list(data.keys())
            lines = [f"dict 含 {len(keys)} 个键: {keys}"]
            for k, v in data.items():
                if isinstance(v, str):
                    lines.append(f"  [{k}]: {v[:150]}{'...' if len(v)>150 else ''}")
                elif isinstance(v, list):
                    lines.append(f"  [{k}]: list 长度 {len(v)}")
                elif isinstance(v, dict):
                    lines.append(f"  [{k}]: dict 含 {len(v)} 个键")
                else:
                    lines.append(f"  [{k}]: {v}")
            return "\n".join(lines)
        if isinstance(data, list):
            return f"list 长度 {len(data)}"
        if isinstance(data, str):
            return data[:300] + ("..." if len(data) > 300 else "")
        return str(data)[:300]


class Overseer:
    def __init__(self):
        self.steps: dict[str, StepRecord] = {}
        self._order: list[str] = []
        self._fatal_error = None

    def start(self, step_name: str, input_data=None, upstream: list[str] = None):
        rec = StepRecord(step_name, upstream)
        self.steps[step_name] = rec
        for up_name in (upstream or []):
            if up_name in self.steps:
                self.steps[up_name].downstream.append(step_name)
        rec.status = "running"
        rec.start_time = time.time()
        rec.input_data = input_data
        self._order.append(step_name)
        return rec

    def complete(self, step_name: str, output_data, schema_key: str = None, full_output: str = None):
        """
        步骤完成：校验输出完整性，并存储完整原文（用于监工对话展示）。
        full_output: Agent推理的完整文本，不截断。
        """
        if step_name not in self.steps:
            self.start(step_name)
        rec = self.steps[step_name]
        rec.end_time = time.time()
        rec.output_data = output_data
        if full_output:
            rec.full_output = full_output

        if schema_key and schema_key in REQUIRED_OUTPUT_SCHEMA:
            schema = REQUIRED_OUTPUT_SCHEMA[schema_key]
            if isinstance(output_data, dict):
                missing = [k for k in schema if k not in output_data]
                if missing:
                    raise DataIntegrityError(
                        f"步骤 [{step_name}] 输出缺失必需字段: {missing}。"
                        f"预期: {schema}，实际: {list(output_data.keys())}"
                    )

        rec.status = "success"

    def fail(self, step_name: str, error: Exception):
        for name, rec in self.steps.items():
            if rec.status == "running":
                rec.status = "failed"
                rec.end_time = rec.end_time or time.time()
                rec.error = str(error)
        if step_name in self.steps and self.steps[step_name].status != "failed":
            rec = self.steps[step_name]
            rec.status = "failed"
            rec.end_time = time.time()
            rec.error = str(error)
        self._fatal_error = f"[{step_name}] {error}"

    @property
    def has_error(self) -> bool:
        return self._fatal_error is not None

    def get_step_full(self, step_name: str) -> dict:
        """获取某一步的完整数据（含原文）"""
        if step_name not in self.steps:
            return {}
        rec = self.steps[step_name]
        return {
            "step": rec.step_name,
            "status": rec.status,
            "full_output": rec.full_output,
            "output_data": rec.output_data,
            "duration_ms": (
                int((rec.end_time - rec.start_time) * 1000)
                if rec.start_time and rec.end_time
                else None
            ),
            "error": rec.error,
        }

    def generate_report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("  监工追溯报告（Overseer Trace Report）")
        lines.append("=" * 60)
        lines.append(f"  执行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  总步骤数: {len(self._order)}")
        lines.append(f"  最终状态: {'❌ 异常终止' if self._fatal_error else '✅ 全部通过'}")
        if self._fatal_error:
            lines.append(f"  致命错误: {self._fatal_error}")
        lines.append("")
        for i, step_name in enumerate(self._order, 1):
            rec = self.steps[step_name]
            icon = {"success": "✅", "failed": "❌", "running": "⏳", "pending": "⬜"}.get(rec.status, "?")
            lines.append(f"--- 步骤 {i}: {step_name} {icon} ---")
            lines.append(f"  上游: {rec.upstream or '(无·入口)'}")
            lines.append(f"  下游: {rec.downstream or '(无·终点)'}")
            if rec.start_time and rec.end_time:
                lines.append(f"  耗时: {int((rec.end_time - rec.start_time)*1000)}ms")
            lines.append(f"  输入摘要:\n    {rec._summarize(rec.input_data)}")
            lines.append(f"  输出摘要:\n    {rec._summarize(rec.output_data)}")
            if rec.error:
                lines.append(f"  ❌ 错误: {rec.error}")
            lines.append("")
        lines.append("=" * 60)
        lines.append("  报告结束。完整Agent原文可通过界面查看或导出JSON。")
        return "\n".join(lines)

    def export_json(self) -> str:
        return json.dumps(
            {
                "execution_order": self._order,
                "fatal_error": self._fatal_error,
                "steps": {n: r.to_dict() for n, r in self.steps.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
