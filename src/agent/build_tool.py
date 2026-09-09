"""
build_tool.py - Real cross-compiler feedback for the agent (the "environment").

The agent is given the *same compiler* the evaluation harness uses
(`arm-none-eabi-gcc` + `tools/bsp_stubs`, with the vendor-SDK auto-stub recovery
loop), because a firmware engineer always has a compiler. It is **not** given
the scoring function: this module deliberately returns only raw diagnostics
(errors / warnings / section sizes) and never any sub-score, weight or verdict
from `src/edge_evaluator.py`.

Keeping the build environment identical to the evaluator's is what makes the
agent's compile loop meaningful; keeping the *score* hidden is what keeps the
measurement honest.
"""
from __future__ import annotations

import importlib.util
import os
import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))

_EV_CACHE: Dict[str, Any] = {}


def _evaluator_module():
    if "mod" not in _EV_CACHE:
        path = os.path.join(_REPO, "src", "edge_evaluator.py")
        spec = importlib.util.spec_from_file_location("edge_evaluator_for_build", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _EV_CACHE["mod"] = mod
    return _EV_CACHE["mod"]


_TARGET_BY_PLATFORM = {
    "STM32F103C8T6": ("cortex-m3", 65536, 20480),
    "STM32F407VG": ("cortex-m4", 1048576, 131072),
    "ESP32-WROOM-32": ("cortex-m4", 4194304, 327680),  # xtensa in reality; m4 proxy
    "RP2040": ("cortex-m0", 2097152, 264192),
    "Raspberry Pi Pico (RP2040)": ("cortex-m0", 2097152, 264192),
}


def target_for_platform(platform: str):
    """Map a dataset platform string to (cpu, flash_budget, ram_budget)."""
    if not platform:
        return ("cortex-m4", 262144, 65536)
    for key, val in _TARGET_BY_PLATFORM.items():
        if key.lower() in platform.lower() or platform.lower() in key.lower():
            return val
    if "rp2040" in platform.lower() or "pico" in platform.lower():
        return _TARGET_BY_PLATFORM["RP2040"]
    if "esp32" in platform.lower():
        return _TARGET_BY_PLATFORM["ESP32-WROOM-32"]
    return ("cortex-m4", 262144, 65536)


class Builder:
    """Cross-compile a C source string and report raw diagnostics."""

    def __init__(self, target: str = "cortex-m4"):
        mod = _evaluator_module()
        # We instantiate EdgeEvaluator purely for its toolchain plumbing and the
        # SDK auto-stub recovery loop; only `_cross_compile` is ever called.
        self._impl = mod.EdgeEvaluator(target=target)
        self.target = target

    def build(self, code: str) -> Dict[str, Any]:
        code = (code or "").strip()
        if not code:
            return {
                "ok": False,
                "status": "no_code",
                "error_count": 0,
                "errors": [],
                "warning_count": 0,
                "warnings": [],
                "sdk_symbols_stubbed": 0,
                "code_errors": [],
                "code_error_count": 0,
                "artifact_errors": [],
                "artifact_error_count": 0,
                "text_bytes": None,
                "data_bytes": None,
                "bss_bytes": None,
            }
        raw = self._impl._cross_compile(code + "\n")  # noqa: SLF001 - intentional
        fp = raw.get("footprint") or {}
        errors = [_clean_diag(e) for e in raw.get("compile_errors", [])][:10]
        stubbed = raw.get("sdk_stub_count", 0)
        code_errs, artefacts = classify_errors(errors, code, stubbed)
        return {
            "ok": bool(raw.get("compiles")),
            "status": raw.get("compile_status"),
            "error_count": raw.get("genuine_error_count", 0),
            "errors": errors,
            "code_errors": code_errs,
            "code_error_count": len(code_errs),
            "artifact_errors": artefacts,
            "artifact_error_count": len(artefacts),
            "collision_hints": collision_hints(errors, code),
            "warning_count": raw.get("warning_count", 0),
            "warnings": [_clean_diag(w) for w in raw.get("warnings", [])][:10],
            "sdk_symbols_stubbed": raw.get("sdk_stub_count", 0),
            "text_bytes": fp.get("text_bytes"),
            "data_bytes": fp.get("data_bytes"),
            "bss_bytes": fp.get("bss_bytes"),
            "flash_bytes": fp.get("flash_bytes"),
            "ram_bytes": fp.get("ram_bytes"),
        }


def _clean_diag(line: str) -> str:
    """Strip the temp-dir prefix so diagnostics read like `line 42: ...`."""
    line = re.sub(r"^\S*src\.c:", "src.c:", line.strip())
    line = re.sub(r"^/tmp/\S+/", "", line)
    return line[:300]


# --------------------------------------------------------------------------- #
# Offline-SDK artefact detection
#
# The harness has no real vendor SDK: every unknown symbol is recovered by an
# auto-stub generator that can only emit
#     typedef struct { int a; int b; } T;   int func(int, ...);   #define ID 0
# Correct vendor code therefore produces a small family of diagnostics that say
# nothing about the firmware -- e.g. `esp_restart()` becomes "too few arguments"
# because the stub prototype is `int esp_restart(int, ...)`, and
# `i2c_config_t c = {.mode = ...}` cannot match an all-`int` stub struct.
#
# Reporting this distinction is information about the *environment* (the same
# thing a real build system says when a mock is in the include path). It is not
# information about the score: the agent is explicitly told NOT to distort
# correct SDK usage to silence these, because that would trade real firmware
# quality for a compiler-shaped illusion.
# --------------------------------------------------------------------------- #
_ARTIFACT_PATTERNS = [
    (r"too few arguments to function", "stub prototype is `int f(int, ...)`"),
    (r"field name not in record or union initializer", "stub type is not a struct"),
    (r"invalid initializer", "stub type cannot accept the real SDK initializer"),
    (r"has no member named", "stub struct has only the fields the stubber inferred"),
    (r"invalid operands to binary", "stub typedef is a struct, not a scalar"),
    (r"used struct type value where scalar is required", "stub typedef is a struct"),
    (r"incompatible types when (?:assigning|initializing|returning)", "stub type mismatch"),
    (r"invalid application of 'sizeof' to (?:an )?incomplete type", "stub type is incomplete"),
    (r"dereferencing pointer to incomplete type", "stub type is incomplete"),
    (r"wrong type argument to unary exclamation mark", "stub typedef is a struct"),
    (r"conversion to non-scalar type requested", "stub typedef is a struct"),
]

_QUOTED_RE = re.compile(r"'([A-Za-z_]\w*)'")

# The bench BSP (`tools/bsp_stubs/mcu_stub.h`) seeds vendor symbols for *all*
# supported families at once, so a helper named after a common SDK entry point
# (e.g. `i2c_init`, which the Pico SDK owns) collides even on an ESP32 task.
# That is fixable by the model -- renaming the helper is idiomatic anyway -- so
# it gets an actionable hint rather than being written off as an artefact.
_COLLISION_RE = re.compile(
    r"error:\s*(?:conflicting types for|redefinition of|"
    r"static declaration of)\s+'(\w+)'")


def collision_hints(errors: List[str], code: str) -> List[str]:
    hints = []
    seen = set()
    for e in errors:
        m = _COLLISION_RE.search(e)
        if not m:
            continue
        name = m.group(1)
        if name in seen or not _user_defined(name, code):
            continue
        seen.add(name)
        hints.append(
            f"'{name}' is already declared by this bench's BSP header (it is a "
            f"vendor-SDK entry point for one of the supported boards). Rename your "
            f"own helper, e.g. `{name}` -> `app_{name}` or `{name}_cfg`, and update "
            f"its call sites."
        )
    return hints


def _user_defined(name: str, code: str) -> bool:
    """True if `name` is declared by the model itself (so the diag is genuine)."""
    if not name:
        return False
    pats = [
        rf"\btypedef\b[^;{{]*\b{re.escape(name)}\s*;",
        rf"\btypedef\s+(?:struct|union|enum)\s*(?:\w+\s*)?\{{[^}}]*\}}\s*{re.escape(name)}\b",
        rf"\b(?:struct|union|enum)\s+{re.escape(name)}\s*\{{",
        rf"^\s*(?:static\s+)?[\w \t\*]+\b{re.escape(name)}\s*\([^;]*\)\s*\{{",
        rf"^\s*#\s*define\s+{re.escape(name)}\b",
    ]
    return any(re.search(p, code, re.M) for p in pats)


def classify_errors(errors: List[str], code: str, stubbed: int):
    """Split compiler errors into (code_errors, artifact_errors).

    Conservative: nothing is called an artefact unless the auto-stubber actually
    fired, and any symbol the model declared itself keeps its error genuine.
    """
    if stubbed <= 0:
        return list(errors), []
    real: List[str] = []
    artefacts: List[str] = []
    for e in errors:
        why = None
        for pat, reason in _ARTIFACT_PATTERNS:
            if re.search(pat, e):
                why = reason
                break
        if why is None:
            real.append(e)
            continue
        names = _QUOTED_RE.findall(e)
        if any(_user_defined(n, code) for n in names):
            real.append(e)
        else:
            artefacts.append(f"{e}   [offline-SDK artefact: {why}]")
    return real, artefacts


def format_build_report(res: Dict[str, Any], flash_budget: Optional[int] = None,
                        ram_budget: Optional[int] = None) -> str:
    """Render a compiler report for the agent transcript."""
    L: List[str] = []
    if res["status"] == "no_code":
        return "BUILD: no source in the workspace. Write a ```c code block first."
    verdict = "SUCCESS" if res["ok"] and res["error_count"] == 0 else "FAILED"
    L.append(f"BUILD {verdict}  (arm-none-eabi-gcc, status={res['status']})")
    code_errs = res.get("code_errors")
    artefacts = res.get("artifact_errors") or []
    if code_errs is None:                     # older result dict
        code_errs = res.get("errors", [])
    if code_errs:
        L.append(f"errors in your code: {len(code_errs)}")
        for e in code_errs:
            L.append(f"  {e}")
        for h in (res.get("collision_hints") or []):
            L.append(f"  hint: {h}")
    if artefacts:
        L.append(f"errors caused by the offline SDK stub, NOT by your code: {len(artefacts)}")
        for e in artefacts[:6]:
            L.append(f"  {e}")
        L.append("  -> This bench has no real vendor SDK; unknown symbols are replaced "
                 "by `int f(int,...)` / all-int structs, which cannot match correct "
                 "vendor code. Do NOT rewrite correct SDK usage to silence these. "
                 "Spend your remaining effort on the review and requirement findings.")
    if res["warning_count"]:
        L.append(f"warnings: {res['warning_count']}")
        for w in res["warnings"][:6]:
            L.append(f"  {w}")
    if res.get("sdk_symbols_stubbed"):
        L.append(
            f"note: {res['sdk_symbols_stubbed']} vendor-SDK symbol(s) were auto-stubbed "
            "(missing SDK headers are tolerated; this is not an error)."
        )
    if res.get("flash_bytes") is not None:
        line = (f"footprint: .text={res['text_bytes']}B .data={res['data_bytes']}B "
                f".bss={res['bss_bytes']}B -> flash={res['flash_bytes']}B "
                f"ram={res['ram_bytes']}B")
        if flash_budget:
            line += f" (flash budget {flash_budget}B"
            if ram_budget:
                line += f", ram budget {ram_budget}B"
            line += ")"
            if res["flash_bytes"] > flash_budget:
                line += "  *** OVER FLASH BUDGET ***"
            if ram_budget and res["ram_bytes"] > ram_budget:
                line += "  *** OVER RAM BUDGET ***"
        L.append(line)
    if verdict == "SUCCESS" and not res["warning_count"]:
        L.append("No errors and no warnings.")
    return "\n".join(L)
