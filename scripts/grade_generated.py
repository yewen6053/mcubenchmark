#!/usr/bin/env python3
"""
grade_generated.py - Grade generated MCU/edge firmware code against MCU-CodeBench.

Standalone grader for this benchmark repo. It performs a REAL on-device (上机)
assessment of each generated snippet:

  1. cross-compile with arm-none-eabi-gcc for the task's Cortex-M target
     (an auto-stub loop recovers "needs the vendor SDK" gaps so genuine C
     defects are isolated from ordinary environment gaps),
  2. .text/.data/.bss footprint via arm-none-eabi-size vs the MCU budget,
  3. best-effort link (undefined symbols weak-stubbed) into an ELF,
  4. multi-dimensional static scoring: compile, footprint, edge correctness,
     real-time/power, structure, functional completeness,
  5. a weighted composite edge_score (0-100) and an on_device_readiness
     verdict (build_ready / needs_fixes / won't_build / empty).

Inputs
  --tasks  <jsonl>   task set (default: data/mcucodebench_tasks.jsonl,
                     the 324-task expanded benchmark; use data/tasks.jsonl for
                     the 80-task seed or data/tasks_net.jsonl for the network
                     family).
  --generated <jsonl|json>  records containing the code to grade. Each record
                     must carry the task id and the generated code. Accepted
                     shapes (auto-detected):
                       {"id": ..., "code": ..., ...}                 (round11 style)
                       {"task_id": ..., "code": ..., ...}
                       {"task": {"id": ...}, "code": ...}
                       {"generated_code": ...}                       (round02/06 style,
                                                                     paired by order to tasks)
  --limit  <int>     grade only the first N tasks (quick smoke test)
  --target <str>     force a Cortex-M target (overrides per-platform mapping)
  --out    <path>    output json path (default: results/edge_eval/<set>.json)
  --md              also write a markdown report next to the json

Output
  results/edge_eval/<set>.json - per-task evaluations + aggregate
  results/edge_eval/<set>.md   - markdown report (with --md)

Toolchain
  By default the evaluator looks for a vendored GNU ARM toolchain at
  tools/arm_toolchain/usr/bin/arm-none-eabi-gcc (this repo does not vendor the
  ~1.2 GB toolchain; see README). If absent, set EDGE_EVAL_TOOLCHAIN to the
  bin dir of any arm-none-eabi-gcc (>= 10) installation. The SDK header stubs
  live in tools/bsp_stubs (vendored, ~230 KB). Override with EDGE_EVAL_BSP.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)

# --------------------------------------------------------------------------- #
# Repo-local imports (no pip install needed; repo root on sys.path)
# --------------------------------------------------------------------------- #
sys.path.insert(0, _REPO)

from src.edge_evaluator import EdgeEvaluator  # noqa: E402
from src.agent.build_tool import target_for_platform  # noqa: E402


def _load_metrics():
    """Weights + default target from configs/eval_metrics.yaml (JSON/YAML-lite)."""
    path = os.path.join(_REPO, "configs", "eval_metrics.yaml")
    weights = {"compile": 0.30, "footprint": 0.10, "edge": 0.25,
               "realtime_power": 0.10, "structure": 0.15, "functional": 0.10}
    targets = {"cortex-m0": (32768, 4096), "cortex-m3": (131072, 20480),
               "cortex-m4": (262144, 65536), "cortex-m7": (1048576, 327680)}
    default_target = "cortex-m4"
    try:
        import yaml  # type: ignore
        cfg = yaml.safe_load(open(path))
        if cfg and cfg.get("weights"):
            weights = cfg["weights"]
        if cfg and cfg.get("targets"):
            targets = {k: (v["flash"], v["ram"]) for k, v in cfg["targets"].items()}
        if cfg and cfg.get("default_target"):
            default_target = cfg["default_target"]
    except Exception:
        pass
    return weights, targets, default_target


def load_tasks(path):
    tasks = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        tasks.append(json.loads(line))
    return tasks


def load_generated(path, tasks):
    """Return list of (task, code) pairs. Auto-detects record shape."""
    text = open(path).read()
    data = json.loads(text)
    records = data if isinstance(data, list) else data.get("results", data.get("samples",
                                            data.get("per_task", [data])))

    by_id = {}
    for r in records:
        if not isinstance(r, dict):
            continue
        tid = r.get("id") or r.get("task_id")
        if tid is None and isinstance(r.get("task"), dict):
            tid = r["task"].get("id")
        code = r.get("code") or r.get("generated_code") or r.get("candidate") or ""
        if tid is None:
            continue
        by_id[str(tid)] = code

    pairs = []
    matched = 0
    for t in tasks:
        tid = str(t.get("id"))
        if tid in by_id:
            pairs.append((t, by_id[tid]))
            matched += 1
        elif "generated_code" in text:
            # positional fallback for plain {"generated_code": ...} lists
            idx = pairs and len(pairs) or 0
            if idx < len(records) and isinstance(records[idx], dict):
                code = records[idx].get("generated_code", "")
                pairs.append((t, code))
    return pairs, matched, len(tasks)


def aggregate(evals):
    """Identical semantics to the round06/round08/round11 aggregate()."""
    n = len(evals)
    if n == 0:
        return {}
    ag = {"n": n}
    ag["compile_success_rate"] = round(sum(1 for e in evals if e["compiles"]) / n, 4)
    ag["clean_compile_rate"] = round(
        sum(1 for e in evals if e["compile_status"] == "clean") / n, 4)
    ag["genuine_error_rate"] = round(
        sum(1 for e in evals if e["genuine_error_count"] > 0) / n, 4)
    ag["sdk_stub_rate"] = round(
        sum(1 for e in evals if e["compile_status"] == "sdk_stubbed") / n, 4)
    ag["average_warnings"] = round(sum(e["warning_count"] for e in evals) / n, 2)

    for k in ("compile", "footprint", "edge", "realtime_power", "structure", "functional"):
        ag[f"avg_{k}_score"] = round(sum(e["subscores"].get(k, 0) for e in evals) / n, 1)
    ag["avg_composite_score"] = round(sum(e["edge_score"] for e in evals) / n, 1)
    scores = sorted(e["edge_score"] for e in evals)
    ag["median_composite_score"] = scores[n // 2]
    ag["min_composite_score"] = scores[0]
    ag["max_composite_score"] = scores[-1]

    fps = [e["footprint"] for e in evals if e.get("footprint")]
    if fps:
        ag["avg_flash_bytes"] = round(sum(f["flash_bytes"] for f in fps) / len(fps), 1)
        ag["avg_ram_bytes"] = round(sum(f["ram_bytes"] for f in fps) / len(fps), 1)
        ag["avg_flash_satisfaction"] = round(
            sum(f["flash_satisfaction"] for f in fps) / len(fps), 3)
        ag["avg_ram_satisfaction"] = round(
            sum(f["ram_satisfaction"] for f in fps) / len(fps), 3)

    dist = collections.Counter(e["on_device_readiness"] for e in evals)
    ag["readiness"] = {k: dist.get(k, 0) for k in
                       ("build_ready", "needs_fixes", "won't_build", "empty")}

    for k in ["peripheral_access", "volatile_io", "defines_isr", "isr_critical_section",
              "uses_dma", "busy_wait", "has_timeout", "hal_error_checked",
              "null_checks", "init_called"]:
        ag[f"sig_{k}_rate"] = round(
            sum(1 for e in evals if e.get("edge_signals", {}).get(k) is True) / n, 3)
    for k in ["uses_interrupt", "uses_timer", "uses_low_power", "uses_dma", "pure_polling"]:
        ag[f"sig_{k}_rate"] = round(
            sum(1 for e in evals if e.get("realtime_signals", {}).get(k) is True) / n, 3)

    groups = {"by_category": collections.defaultdict(list),
              "by_difficulty": collections.defaultdict(list),
              "by_platform": collections.defaultdict(list)}
    for e in evals:
        m = e.get("_meta", {})
        groups["by_category"][m.get("category") or "unknown"].append(e)
        groups["by_difficulty"][m.get("difficulty") or "unknown"].append(e)
        groups["by_platform"][m.get("platform") or "unknown"].append(e)
    for gname, gdict in groups.items():
        ag[gname] = {
            g: {"n": len(evs),
                "compile_success_rate": round(sum(1 for e in evs if e["compiles"]) / len(evs), 3),
                "genuine_error_rate": round(
                    sum(1 for e in evs if e["genuine_error_count"] > 0) / len(evs), 3),
                "avg_edge_score": round(sum(e["edge_score"] for e in evs) / len(evs), 1),
                "avg_edge_correctness": round(
                    sum(e["subscores"].get("edge", 0) for e in evs) / len(evs), 1)}
            for g, evs in gdict.items() if evs}
    return ag


def render_md(set_key, tasks, evals, ag):
    L = [f"# {set_key} — MCU-CodeBench Edge Evaluation", ""]
    L.append(f"n = {ag['n']} · arm-none-eabi-gcc cross-compile · composite edge_score (0-100) · "
             f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L.append("")
    L.append("## Headline")
    L.append("")
    L.append(f"- **compile** {ag['compile_success_rate']*100:.1f}% "
             f"(clean {ag['clean_compile_rate']*100:.1f}% / sdk-stubbed "
             f"{ag['sdk_stub_rate']*100:.1f}%)")
    L.append(f"- **genuine error** {ag['genuine_error_rate']*100:.1f}%")
    L.append(f"- **composite edge_score** {ag['avg_composite_score']:.1f} "
             f"(min {ag['min_composite_score']:.1f}, med {ag['median_composite_score']:.1f}, "
             f"max {ag['max_composite_score']:.1f})")
    rd = ag["readiness"]
    L.append("- **build_ready** %s / needs_fixes %s / won't_build %s" % (
        rd['build_ready'], rd['needs_fixes'], rd.get("won't_build", 0)))
    L.append("")
    L.append("## By category")
    L.append("")
    L.append("| Category | n | Compile% | GenuineErr% | edge_score | edge_correctness |")
    L.append("|---|---|---|---|---|---|")
    for g, v in sorted(ag.get("by_category", {}).items()):
        L.append(f"| {g} | {v['n']} | {v['compile_success_rate']*100:.0f} | "
                 f"{v['genuine_error_rate']*100:.0f} | {v['avg_edge_score']:.1f} | "
                 f"{v['avg_edge_correctness']:.1f} |")
    L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default=os.path.join(_REPO, "data", "mcucodebench_tasks.jsonl"))
    ap.add_argument("--generated", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--target", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    weights, targets, default_target = _load_metrics()
    tasks = load_tasks(args.tasks)
    pairs, matched, n_tasks = load_generated(args.generated, tasks)
    if args.limit > 0:
        pairs = pairs[:args.limit]

    if not pairs:
        print(f"[grade] no code matched task ids in {args.generated} "
              f"({matched}/{n_tasks} matched). Check the record shape.")
        sys.exit(2)

    # Per-platform target/budget mapping; --target overrides.
    ev_by_plat = {}
    evals = []
    for t, code in pairs:
        plat = (t.get("platform") or "").strip()
        if args.target:
            target, fb, rb = args.target, *targets.get(args.target, (262144, 65536))
        elif plat and not args.target:
            cpu, fb, rb = target_for_platform(plat)
            target = cpu
        else:
            target = default_target
            fb, rb = targets.get(default_target, (262144, 65536))
        key = (target, fb, rb)
        if key not in ev_by_plat:
            ev_by_plat[key] = EdgeEvaluator(target=target, flash_budget=fb, ram_budget=rb,
                                            weights=weights)
        ev = ev_by_plat[key]
        meta = {"task_id": t.get("id"), "category": t.get("category", ""),
                "platform": plat, "difficulty": t.get("difficulty", ""),
                "scenario": t.get("scenario", "")}
        try:
            r = ev.evaluate(code, meta)
        except Exception as exc:  # noqa: BLE001
            r = {"compiles": False, "compile_status": f"exc:{exc}",
                 "genuine_error_count": 1, "sdk_stub_count": 0,
                 "compile_errors": [str(exc)], "warnings": [], "warning_count": 0,
                 "link_success": None, "footprint": None, "subscores": {},
                 "edge_score": 0.0, "on_device_readiness": "won't_build",
                 "edge_signals": {}, "realtime_signals": {}, "structure_signals": {},
                 "functional_signals": {}}
        r["_meta"] = meta
        evals.append(r)

    ag = aggregate(evals)
    set_key = os.path.splitext(os.path.basename(args.generated))[0]
    out_json = args.out or os.path.join(_REPO, "results", "edge_eval", f"{set_key}.json")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    payload = {
        "set_key": set_key, "dataset": os.path.basename(args.tasks),
        "n_tasks": n_tasks, "matched": matched, "graded": len(evals),
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "aggregate": ag, "per_task": evals,
    }
    json.dump(payload, open(out_json, "w"), indent=2, ensure_ascii=False)

    if args.md:
        md = render_md(set_key, tasks, evals, ag)
        open(out_json.replace(".json", ".md"), "w").write(md)

    print(f"[grade] {len(evals)} tasks graded (matched {matched}/{n_tasks})")
    print(f"[grade] compile={ag['compile_success_rate']*100:.1f}% "
          f"genuine_err={ag['genuine_error_rate']*100:.1f}% "
          f"edge_score={ag['avg_composite_score']:.1f} "
          f"build_ready={ag['readiness']['build_ready']}/{ag['n']}")
    print(f"[grade] -> {out_json}")


if __name__ == "__main__":
    main()