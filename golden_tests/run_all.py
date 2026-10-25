"""Run the complete deterministic regression suite and write an independent report."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "golden_tests" / "reports"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def project_python() -> str:
    candidates = [ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run_step(name: str, command: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
    print(f"\n=== {name} ===")
    print("$ " + " ".join(command))
    environment = os.environ.copy()
    if extra_env:
        environment.update(extra_env)
    process = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = (process.stdout + "\n" + process.stderr).strip()
    if output:
        print(output)
    status = "通过" if process.returncode == 0 else "失败"
    print(f"[{status}] {name}")
    return {"name": name, "status": status, "returncode": process.returncode, "output": output}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the golden dataset regression suite")
    parser.add_argument("--live-model", action="store_true", help="Reserved for future paid end-to-end Qwen evaluation")
    args = parser.parse_args()
    python = project_python()
    npm = "npm.cmd" if os.name == "nt" else "npm"
    steps = [
        run_step(
            "黄金测试集契约与边界校验",
            [python, "-m", "pytest", "-q", "golden_tests/test_golden_dataset.py"],
            ROOT,
        ),
        run_step(
            "后端单元与接口测试",
            [python, "-m", "pytest", "-q", "backend/tests"],
            ROOT,
            {"PYTHONPATH": str(ROOT / "backend")},
        ),
        run_step("前端生产构建", [npm, "run", "build"], ROOT / "frontend"),
    ]
    if args.live_model:
        steps.append({"name": "真实模型黄金集评测", "status": "跳过", "returncode": 0, "output": "当前未启用付费端到端评测；请先完成人工金标准标注后再实现。"})
        print("[跳过] 真实模型黄金集评测：当前未启用，避免未经人工标注就产生误判和模型费用")

    passed = sum(step["status"] == "通过" for step in steps)
    failed = sum(step["status"] == "失败" for step in steps)
    skipped = sum(step["status"] == "跳过" for step in steps)
    overall = "通过" if failed == 0 else "失败"
    report = [
        "# 黄金测试集自动测试报告",
        "",
        f"- 执行时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- 总体结果：**{overall}**",
        f"- 通过：{passed}，失败：{failed}，跳过：{skipped}",
        "",
        "## 分项结果",
        "",
    ]
    for step in steps:
        report.append(f"### {step['status']}：{step['name']}")
        report.append("")
        report.append("```text")
        report.append(step["output"][-4000:] or "无输出")
        report.append("```")
        report.append("")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "latest_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\n总体结果：{overall}")
    print(f"报告文件：{REPORT_DIR / 'latest_report.md'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
