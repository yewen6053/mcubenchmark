"""
edge_evaluator.py - Multi-dimensional evaluator for generated MCU/edge firmware C code.

Replaces the old heuristic validator (brace/paren counting + hard-coded keyword
bonuses) with a framework that produces a REAL on-device (上机) assessment:

  1. Compile / 上机可编译性  - cross-compiles with arm-none-eabi-gcc for an ARM
     Cortex-M target (real compiler, not regex). An auto-stub loop recovers from
     "needs the vendor SDK" references so that *genuine* C defects are isolated
     from ordinary environment gaps. Reports errors, warnings, and link success.
  2. Footprint / 资源占用   - real .text/.data/.bss bytes via arm-none-eabi-size,
     compared against the target MCU flash/RAM budget.
  3. Edge correctness / 边缘正确性 - peripheral/HAL register usage, volatile IO,
     ISR / critical-section safety, DMA, busy-wait timeout safety, error/return
     checking, init/clock ordering.
  4. Real-time / power / 实时功耗 - interrupt/timer usage, low-power modes,
     polling vs event-driven trade-offs.
  5. Structure / 结构可维护  - includes, modularity, comments, proper types,
     encapsulation (strengthened structural checks).
  6. Functional completeness / 功能匹配 - required-API coverage derived from the
     task category (replaces the hard-coded per-category keyword bonus).

The composite `edge_score` (0-100) is a weighted sum of the six dimension
scores (weights from configs/eval_metrics.yaml). A `on_device_readiness`
verdict classifies the code as production-candidate / needs-fixes / won't-build.
"""
import os
import re
import json
import shutil
import tempfile
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)


def _default_toolchain_bin():
    env = os.environ.get("EDGE_EVAL_TOOLCHAIN")
    if env:
        return env
    local = os.path.join(_REPO, "tools", "arm_toolchain", "usr", "bin")
    if os.path.isdir(local):
        return local
    return ""  # rely on PATH


def _default_bsp_dir():
    env = os.environ.get("EDGE_EVAL_BSP")
    if env:
        return env
    local = os.path.join(_REPO, "tools", "bsp_stubs")
    if os.path.isdir(local):
        return local
    return ""


# C keywords that must never be auto-stubbed
_C_KEYWORDS = {
    "int", "char", "float", "double", "void", "long", "short", "unsigned",
    "signed", "const", "static", "volatile", "register", "struct", "union",
    "enum", "typedef", "extern", "auto", "if", "else", "for", "while", "do",
    "switch", "case", "default", "break", "continue", "return", "goto",
    "sizeof", "typeof", "inline", "restrict", "_Bool", "bool", "true", "false",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t", "int8_t", "int16_t",
    "int32_t", "int64_t", "size_t", "intptr_t", "uintptr_t", "intmax_t",
    "uintmax_t", "float_t", "double_t", "wchar_t", "ptrdiff_t",
}


def _declared_in_code(name: str, code: str) -> bool:
    """True if `name` is declared somewhere in the submitted source.

    Used to keep the auto-stubber from `#define`-ing an identifier that the
    author actually declared (typically a handle declared inside one function
    and then referenced from another). Such a symbol is a genuine scope defect,
    not a missing vendor-SDK symbol, and must stay a real error.
    """
    if not name:
        return False
    n = re.escape(name)
    patterns = [
        # declaration/definition with a type in front: `TIM_HandleTypeDef htim2;`
        rf"^[ \t]*(?:static|volatile|const|extern|register|struct|union|enum|unsigned|signed)?"
        rf"[\w \t\*]*?\b{n}\s*(?:\[[^\]]*\])?\s*(?:=|;|,|\))",
        rf"\b(?:struct|union|enum)\s+\w+\s*\*?\s*{n}\b",
        rf"^[ \t]*#\s*define\s+{n}\b",
        rf"\b{n}\s*\([^;]*\)\s*\{{",          # function definition
        rf"\btypedef\b[^;]*\b{n}\s*;",
    ]
    return any(re.search(p, code, re.M) for p in patterns)


class EdgeEvaluator:
    def __init__(self, toolchain_bin=None, bsp_dir=None, target="cortex-m4",
                 flash_budget=262144, ram_budget=65536, config_path=None, weights=None):
        self.toolchain_bin = toolchain_bin or _default_toolchain_bin()
        self.bsp_dir = bsp_dir or _default_bsp_dir()
        self.target = target
        self.flash_budget = flash_budget
        self.ram_budget = ram_budget
        self.weights = weights or self._load_weights(config_path)
        # CPU / arch flags per target
        self.cpu_flags = {
            "cortex-m0": ["-mcpu=cortex-m0", "-mthumb"],
            "cortex-m3": ["-mcpu=cortex-m3", "-mthumb"],
            "cortex-m4": ["-mcpu=cortex-m4", "-mthumb"],
            "cortex-m7": ["-mcpu=cortex-m7", "-mthumb"],
        }.get(target, ["-mcpu=cortex-m4", "-mthumb"])
        # names we already seeded in mcu_stub.h (so we don't re-stub them)
        self._seeded = self._scan_seeded(self.bsp_dir)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def evaluate(self, code: str, task: dict = None) -> dict:
        task = task or {}
        out = {
            "compiles": None,
            "compile_status": "unknown",
            "genuine_error_count": 0,
            "sdk_stub_count": 0,
            "compile_errors": [],
            "warnings": [],
            "warning_count": 0,
            "link_success": None,
            "footprint": None,
            "edge_signals": {},
            "realtime_signals": {},
            "structure_signals": {},
            "functional_signals": {},
            "subscores": {},
            "edge_score": 0.0,
            "on_device_readiness": "unknown",
            "dimension_notes": [],
        }
        c_code = self._extract_c(code)
        if not c_code:
            out["compile_status"] = "no_code"
            out["on_device_readiness"] = "empty"
            out["dimension_notes"].append("No C code extracted from the response.")
            return out

        # 1) Compile + footprint
        comp = self._cross_compile(c_code)
        out.update({k: comp[k] for k in (
            "compiles", "compile_status", "genuine_error_count", "sdk_stub_count",
            "compile_errors", "warnings", "warning_count", "link_success", "footprint")})
        out["subscores"]["compile"] = self._score_compile(comp)

        # 2) Footprint score
        out["subscores"]["footprint"] = self._score_footprint(comp.get("footprint"))

        # 3) Edge correctness
        edge = self._edge_correctness(c_code, comp)
        out["edge_signals"] = edge["signals"]
        out["subscores"]["edge"] = edge["score"]

        # 4) Real-time / power
        rt = self._realtime_power(c_code)
        out["realtime_signals"] = rt["signals"]
        out["subscores"]["realtime_power"] = rt["score"]

        # 5) Structure
        struct = self._structure(c_code)
        out["structure_signals"] = struct["signals"]
        out["subscores"]["structure"] = struct["score"]

        # 6) Functional completeness
        func = self._functional(c_code, task)
        out["functional_signals"] = func["signals"]
        out["subscores"]["functional"] = func["score"]

        # Composite
        w = self.weights
        raw = sum(out["subscores"].get(k, 0.0) * w.get(k, 0.0) for k in w)
        total_w = sum(w.values()) or 1.0
        out["edge_score"] = round(raw / total_w, 1)
        out["on_device_readiness"] = self._verdict(out)
        return out

    # ------------------------------------------------------------------ #
    # Extraction
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_c(text: str) -> str:
        if not text:
            return ""
        # fenced code block
        m = re.findall(r"```(?:c|cpp|objectivec|C)?\n(.*?)```", text, re.DOTALL)
        if m:
            return m[0].strip() + "\n"
        # otherwise assume the whole thing is code-ish; strip markdown
        return text.strip() + "\n"

    # ------------------------------------------------------------------ #
    # Cross compilation (real compiler + auto-stub recovery)
    # ------------------------------------------------------------------ #
    def _gcc(self):
        if self.toolchain_bin:
            return os.path.join(self.toolchain_bin, "arm-none-eabi-gcc")
        return "arm-none-eabi-gcc"

    def _size(self):
        if self.toolchain_bin:
            return os.path.join(self.toolchain_bin, "arm-none-eabi-size")
        return "arm-none-eabi-size"

    def _nm(self):
        if self.toolchain_bin:
            return os.path.join(self.toolchain_bin, "arm-none-eabi-nm")
        return "arm-none-eabi-nm"

    def _cross_compile(self, code: str) -> dict:
        res = {
            "compiles": False, "compile_status": "error",
            "genuine_error_count": 0, "sdk_stub_count": 0,
            "compile_errors": [], "warnings": [], "warning_count": 0,
            "link_success": None, "footprint": None,
            "struct_field_gaps": 0,
        }
        work = tempfile.mkdtemp(prefix="edge_eval_")
        try:
            src = os.path.join(work, "src.c")
            obj = os.path.join(work, "src.o")
            stub_h = os.path.join(work, "autostub.h")
            open(src, "w").write(code)

            includes = []
            if self.bsp_dir:
                includes += ["-I", self.bsp_dir]
                stub_abs = os.path.join(self.bsp_dir, "mcu_stub.h")
                if os.path.exists(stub_abs):
                    includes += ["-include", stub_abs]
            # emergency include dir: missing SDK/standard headers get an empty
            # stub header dropped here so they are recovered as an "SDK gap"
            # rather than silently misreported as a clean compile.
            includes += ["-I", work]
            includes += ["-include", stub_h]

            base_cmd = [self._gcc(), *self.cpu_flags, "-c", "-Os",
                        "-Wall", "-Wextra", "-Wno-implicit-function-declaration",
                        "-Wno-implicit-int", "-fcommon", "-Wno-unknown-pragmas",
                        *includes, src, "-o", obj]

            # stub state
            types = set()            # type names (may be "struct X")
            type_fields = {}         # type -> set(fields)
            funcs = set()
            idents = set()
            inc_stubs = 0            # missing include headers recovered with empty stubs

            def write_stub():
                L = ["/* auto-generated stubs */\n"]
                for t in types:
                    if t in self._seeded:
                        continue
                    fields = type_fields.get(t, set())
                    body = " ".join(f"int {f};" for f in fields) if fields else "int _stub_;"
                    if t.startswith("struct "):
                        tag = t[len("struct "):]
                        L.append(f"struct {tag} {{ {body} }};\n")
                    else:
                        L.append(f"typedef struct {{ {body} }} {t};\n")
                for f in funcs:
                    L.append(f"int {f}(int, ...);\n")
                for i in idents:
                    L.append(f"#define {i} 0\n")
                open(stub_h, "w").write("".join(L))

            write_stub()
            genuine = []
            for _ in range(8):
                genuine = []  # only keep errors unresolved in the *latest* iteration
                proc = subprocess.run(base_cmd, capture_output=True, text=True, timeout=30)
                errs = [l for l in proc.stderr.splitlines()
                        if (": error:" in l or "fatal error:" in l)]
                warns = [l for l in proc.stderr.splitlines()
                         if ": warning:" in l or ": note:" in l]
                if not errs:
                    res["compiles"] = True
                    res["compile_status"] = "clean" if not (types or funcs or idents) else "sdk_stubbed"
                    res["warnings"] = warns
                    res["warning_count"] = len(warns)
                    break
                stub_lines = []
                for l in errs:
                    kind, payload = self._classify_error(l)
                    if kind is None:
                        genuine.append(l)
                    else:
                        stub_lines.append((kind, payload))
                if not stub_lines:
                    genuine = errs
                    break
                changed = False
                for kind, payload in stub_lines:
                    if kind == "type":
                        name = payload
                        if name in self._seeded or name in types:
                            continue
                        types.add(name); changed = True
                    elif kind == "struct_field":
                        tname, field = payload
                        if tname in self._seeded:
                            # cannot extend seeded struct; treat as SDK gap (not genuine)
                            res["struct_field_gaps"] += 1
                            continue
                        type_fields.setdefault(tname, set()).add(field)
                        types.add(tname); changed = True
                    elif kind == "func":
                        name = payload
                        if name in self._seeded or name in funcs:
                            continue
                        funcs.add(name); changed = True
                    elif kind == "ident":
                        name = payload
                        if name in _C_KEYWORDS or name in idents:
                            continue
                        # An identifier the code itself declares is NOT a missing
                        # SDK symbol -- it is an out-of-scope use (e.g. a handle
                        # declared local to main() but referenced from an ISR).
                        # `#define`-ing it would rewrite every *valid* use of that
                        # variable into `0.field`, turning one real defect into a
                        # cascade of phantom "not a structure" errors and hiding
                        # the bug the author actually has to fix.
                        if _declared_in_code(name, code):
                            continue
                        idents.add(name); changed = True
                    elif kind == "include":
                        hname = payload
                        hpath = os.path.join(work, hname)
                        if not os.path.exists(hpath):
                            # headers like "esp_adc/adc_oneshot.h" need their
                            # parent directory created first, otherwise open()
                            # raises and the whole evaluation aborts.
                            parent = os.path.dirname(hpath)
                            if parent:
                                os.makedirs(parent, exist_ok=True)
                            open(hpath, "w").write(
                                "/* stub header for missing include: %s */\n" % hname)
                            inc_stubs += 1
                            changed = True
                if not changed:
                    genuine = errs
                    break
                write_stub()
            else:
                pass

            res["genuine_error_count"] = len(genuine)
            res["compile_errors"] = genuine[:12]
            res["sdk_stub_count"] = (len(types) + len(funcs) + len(idents)
                                     + sum(len(v) for v in type_fields.values()) + inc_stubs)
            if not res["compiles"]:
                if genuine:
                    res["compile_status"] = "genuine_error"
                else:
                    res["compile_status"] = "error"

            if os.path.exists(obj):
                res["footprint"] = self._size_obj(obj)
                res["link_success"] = self._try_link(work, src, obj, code)
            return res
        except subprocess.TimeoutExpired:
            res["compile_status"] = "timeout"
            return res
        except Exception as e:
            res["compile_status"] = f"exception:{e}"
            return res
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _classify_error(self, line: str):
        """Return (kind, payload) for stubbable errors, else (None, None).
        kinds: 'type' -> name; 'struct_field' -> (type, field);
               'func' -> name; 'ident' -> name."""
        # missing include (standard or vendor header not present) -> recoverable
        m = re.search(r"(?:fatal )?error:\s*([^:]+):\s*No such file or directory", line)
        if m:
            return ("include", m.group(1).strip())
        m = re.search(r"unknown type name '([^']+)'", line)
        if m:
            return ("type", m.group(1))
        m = re.search(r"no member named '(\w+)' (?:in '(?:struct )?([^']+)')", line)
        if m:
            return ("struct_field", (m.group(2), m.group(1)))
        m = re.search(r"'([^']+)' has no member named '(\w+)'", line)
        if m:
            return ("struct_field", (m.group(1), m.group(2)))
        m = re.search(r"implicit declaration of function '([^']+)'", line)
        if m:
            return ("func", m.group(1))
        m = re.search(r"'([^']+)' undeclared \(first use", line)
        if m:
            name = m.group(1)
            if name in _C_KEYWORDS:
                return (None, None)
            return ("ident", name)
        m = re.search(r"error: '([^']+)' undeclared", line)
        if m:
            name = m.group(1)
            if name in _C_KEYWORDS:
                return (None, None)
            return ("ident", name)
        return (None, None)

    def _size_obj(self, obj: str) -> dict:
        try:
            proc = subprocess.run([self._size(), obj], capture_output=True, text=True, timeout=15)
            lines = [l for l in proc.stdout.splitlines() if l.strip()]
            if len(lines) >= 2:
                hdr = lines[0].split()
                vals = lines[1].split()
                # berkeley format is "text data bss dec hex filename"; keep only
                # the first three (text/data/bss), which is all footprint needs.
                # (dec/hex/filename are not all decimal, so don't int() them.)
                hdr = hdr[:3]
                vals = vals[:3]
                nums = [int(v) for v in vals]
                d = dict(zip(hdr, nums))
                text = d.get("text", 0)
                data = d.get("data", 0)
                bss = d.get("bss", 0)
                flash = text + data
                ram = data + bss
                return {
                    "text_bytes": text, "data_bytes": data, "bss_bytes": bss,
                    "flash_bytes": flash, "ram_bytes": ram,
                    "flash_budget": self.flash_budget, "ram_budget": self.ram_budget,
                    "flash_satisfaction": round(min(1.0, self.flash_budget / max(1, flash)), 3),
                    "ram_satisfaction": round(min(1.0, self.ram_budget / max(1, ram)), 3),
                }
        except Exception:
            pass
        return None

    def _try_link(self, work, src, obj, code):
        """Best-effort link: stub every undefined symbol with a weak empty body
        and a minimal entry point, to report whether the snippet is
        self-contained enough to produce a final ELF for the target."""
        try:
            nm = subprocess.run([self._nm(), "-u", obj], capture_output=True, text=True, timeout=15)
            undef = [l.strip().split()[-1] for l in nm.stdout.splitlines() if l.strip()]
            undef = [u for u in undef if u and u not in ("main",)]
            stubs_c = os.path.join(work, "stubs.c")
            lines = ["/* best-effort link stubs */\n",
                     "int main(void){ return 0; }\n",
                     "void Reset_Handler(void){ main(); }\n",
                     "void Default_Handler(void){ while(1){} }\n"]
            for u in undef:
                if u in _C_KEYWORDS:
                    continue
                lines.append(f"int {u}(int, ...){{ return 0; }}\n")
            open(stubs_c, "w").write("\n".join(lines))
            elf = os.path.join(work, "out.elf")
            cmd = [self._gcc(), *self.cpu_flags, "-nostartfiles",
                   "-Wl,-e,Reset_Handler", "-Wl,-Ttext=0x08000000",
                   obj, stubs_c, "-o", elf]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return proc.returncode == 0
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Dimension scoring
    # ------------------------------------------------------------------ #
    def _score_compile(self, comp: dict) -> float:
        if comp.get("compiles") and comp.get("genuine_error_count", 0) == 0:
            return 100.0
        # compiled but only via heavy stubbing / has warnings
        n = comp.get("genuine_error_count", 0)
        if n == 0:
            return 70.0
        return max(0.0, 100.0 - 18.0 * n)

    def _score_footprint(self, fp: dict) -> float:
        if not fp:
            return 0.0
        sat = 0.6 * fp["flash_satisfaction"] + 0.4 * fp["ram_satisfaction"]
        return round(100.0 * sat, 1)

    # ---- edge correctness ----
    def _edge_correctness(self, code, comp):
        s = {}
        notes = []
        score = 100.0
        low = code.lower()

        # peripheral / HAL register access
        has_hal = bool(re.search(r'HAL_[A-Za-z]+', code))
        has_driver = bool(re.search(r'(gpio_|uart_|i2c_|spi_|adc_|tim_|nrf_|cyw43|pwm_)', low))
        has_register = bool(re.search(r'\((?:\s*volatile\s+)?\s*(?:uint\d+_t|unsigned)\s*\*\s*\)', code))
        s["peripheral_access"] = has_hal or has_driver or has_register
        if not s["peripheral_access"]:
            score -= 25
            notes.append("No recognizable peripheral/HAL access (pure generic C).")

        # volatile for direct register IO
        direct_reg = bool(re.search(r'\(\s*(?:volatile\s+)?\s*(?:uint\d+_t|unsigned)\s*\*\s*\)\s*0x', code))
        volatile_used = 'volatile' in low
        if direct_reg and not volatile_used:
            score -= 15
            notes.append("Direct register access without `volatile` qualifier.")
            s["volatile_io"] = False
        else:
            s["volatile_io"] = volatile_used or (not direct_reg)

        # ISR / critical section safety
        isr = re.search(r'\bISR\s*\(|\b(?:\w+|_)?\s*Handler\s*\(', code) or ('interrupt' in low)
        has_isr = bool(re.search(r'ISR\s*\(|void\s+\w*(?:_IRQ|_Handler|Interrupt)\s*\(', code))
        s["defines_isr"] = has_isr
        if has_isr:
            # ISR should not call blocking HAL / long loops
            blocking_in_isr = bool(re.search(r'(HAL_UART_Transmit|HAL_I2C_Mem_Read|HAL_Delay|printf|sleep_ms|while\s*\(\s*1\s*\))', code))
            crit = bool(re.search(r'__disable_irq|__enable_irq|taskENTER_CRITICAL|portENTER_CRITICAL|ATOMIC', code))
            if blocking_in_isr:
                score -= 18
                notes.append("ISR appears to call blocking APIs / contains infinite loop.")
            if not crit and has_isr:
                # not necessarily wrong, but note
                notes.append("ISR defined; verify critical-section protection for shared state.")
            s["isr_critical_section"] = crit
        else:
            s["isr_critical_section"] = None

        # DMA for bulk transfer
        s["uses_dma"] = bool(re.search(r'DMA|dma', low))
        if s["uses_dma"]:
            score += 0  # informational

        # busy-wait / timeout safety
        busy = bool(re.search(r'while\s*\(\s*!\s*\w+\s*\)', code)) or bool(re.search(r'while\s*\(\s*\w+\s*==\s*\w+\s*\)', code))
        has_timeout = bool(re.search(r'HAL_GetTick|timeout|TIMEOUT|timeout_ms|to\b', low)) or 'timeout' in low
        s["busy_wait"] = busy
        s["has_timeout"] = has_timeout
        if busy and not has_timeout:
            score -= 12
            notes.append("Busy-wait loop without an explicit timeout/abort condition.")

        # error / return-value checking on HAL calls
        hal_calls = len(re.findall(r'HAL_[A-Za-z]+\s*\(', code))
        hal_checked = len(re.findall(r'(==\s*HAL_OK|!=\s*HAL_OK|==\s*HAL_ERROR|if\s*\([^)]*HAL_[A-Za-z]+\s*\()', code))
        s["hal_error_checked"] = (hal_calls == 0) or (hal_checked > 0)
        if hal_calls > 0 and hal_checked == 0:
            score -= 12
            notes.append("HAL calls present but return values are not checked.")
        # NULL checks
        s["null_checks"] = bool(re.search(r'==\s*NULL|!=\s*NULL|if\s*\(\s*\w+\s*==\s*NULL', code))
        if re.search(r'malloc|alloc|uart_dev|i2c_dev|adc_dev|handle', low) and not s["null_checks"]:
            score -= 4

        # init / clock enable before use
        s["init_called"] = bool(re.search(r'_Init\s*\(|init\s*\(|HAL_RCC_|clk_enable|gpio_init|uart_init|i2c_init|spi_init|adc_init', low))
        if has_hal and not s["init_called"]:
            score -= 6
            notes.append("HAL/peripheral used but no init/clock-enable sequence found.")

        score = max(0.0, min(100.0, score))
        return {"score": round(score, 1), "signals": s, "_notes": notes}

    # ---- real-time / power ----
    def _realtime_power(self, code):
        low = code.lower()
        s = {}
        score = 40.0  # base; event-driven firmware earns more
        uses_irq = bool(re.search(r'NVIC|IRQ|ISR\s*\(|EXTI|interrupt|HAL_TIM_Base_Start|callback', code))
        uses_timer = bool(re.search(r'TIM|timer|HAL_GetTick|systick|pwm', low))
        uses_lowpower = bool(re.search(r'WFI|WFE|__WFI|sleep|STOP|PWR|pdMS|enter_low|low[_ ]?power|light[_ ]?sleep', low))
        uses_dma = bool(re.search(r'dma', low))
        pure_poll = bool(re.search(r'while\s*\(\s*1\s*\)', code)) and not uses_irq
        s["uses_interrupt"] = uses_irq
        s["uses_timer"] = uses_timer
        s["uses_low_power"] = uses_lowpower
        s["uses_dma"] = uses_dma
        s["pure_polling"] = pure_poll
        if uses_irq:
            score += 25
        if uses_timer:
            score += 15
        if uses_lowpower:
            score += 15
        if uses_dma:
            score += 5
        if pure_poll:
            score -= 20
        score = max(0.0, min(100.0, score))
        return {"score": round(score, 1), "signals": s}

    # ---- structure / maintainability ----
    def _structure(self, code):
        low = code.lower()
        s = {}
        score = 0.0
        s["has_includes"] = bool(re.search(r'#include\s*[<"]', code))
        s["has_functions"] = bool(re.search(r'\b\w+\s+\w+\s*\([^)]*\)\s*\{', code))
        s["has_comments"] = bool(re.search(r'//|/\*', code))
        s["has_proper_types"] = bool(re.search(r'\b(?:u?int\d+_t|size_t|bool)\b', code))
        s["has_error_handling"] = bool(re.search(r'==\s*NULL|!=\s*HAL_OK|<\s*0|ERROR_CHECK|ESP_ERROR_CHECK|return\s+\w*ERR', code))
        s["uses_static"] = 'static' in low
        s["uses_const"] = 'const' in low
        if s["has_includes"]:
            score += 15
        if s["has_functions"]:
            score += 20
        if s["has_comments"]:
            score += 15
        if s["has_proper_types"]:
            score += 15
        if s["has_error_handling"]:
            score += 15
        if s["uses_static"]:
            score += 10
        if s["uses_const"]:
            score += 10
        # modularity: multiple functions
        nfunc = len(re.findall(r'\b\w+\s+\w+\s*\([^)]*\)\s*\{', code))
        if nfunc >= 2:
            score += 0  # already credited
        score = max(0.0, min(100.0, score))
        return {"score": round(score, 1), "signals": s}

    # ---- functional completeness (required-API coverage) ----
    def _functional(self, code, task):
        low = code.lower()
        cat = (str(task.get("category", "")) + " " + str(task.get("scenario", ""))).lower()
        vocab = self._required_vocab(cat)
        if not vocab:
            # generic: any peripheral API + init + main/loop
            vocab = ["init", "main", "gpio|uart|i2c|spi|adc|tim|hal_"]
        present = []
        missing = []
        for tok in vocab:
            if re.search(tok, low):
                present.append(tok)
            else:
                missing.append(tok)
        cov = len(present) / max(1, len(vocab))
        s = {"required_vocab": vocab, "present": present, "missing": missing,
             "coverage": round(cov, 2)}
        return {"score": round(100.0 * cov, 1), "signals": s}

    @staticmethod
    def _required_vocab(cat: str):
        rules = [
            # ---- network / connectivity first (distinctive triggers; prevents
            # e.g. "broadcast" containing "adc" from hijacking the match) ----
            (("mqtt",), ["mqtt", "init|start", "publish|subscribe|topic", "connect"]),
            (("ble ", "bluetooth", "nimble", "gatt"), ["ble|nimble|gap|gatt", "init", "adv|scan|disc|gatts"]),
            (("http",), ["http", "client|get|post", "url|host|uri"]),
            (("lora", "sx127", "rfm9"), ["lora|sx127|rfm9", "init|reset", "spi|frequency", "send|recv|dio"]),
            (("ntp", "sntp"), ["ntp|sntp", "server|pool", "time|sync"]),
            (("nb-iot", "nb_iot", "at command", "at modem", "bc26", "bc95", "modem"), ["at|modem", "uart|usart", "ok|response", "timeout|retry"]),
            (("tcp", "udp", "socket", "wifi", "network"), ["socket|wifi|esp_wifi|cyw43|netif", "init|connect|bind", "send|recv|publish|listen", "port|timeout"]),
            (("gpio", "led", "blink"), ["gpio", "init", "write|toggle|set", "read", "mode", "main|while"]),
            (("uart", "serial"), ["uart", "init", "transmit|send", "receive|read", "baud"]),
            (("i2c",), ["i2c", "init", "write", "read", "address"]),
            (("spi",), ["spi", "init", "transfer", "baud|clock"]),
            (("adc", "analog"), ["adc", "init", "read|convert", "channel"]),
            (("timer", "pwm", "delay"), ["tim|timer", "init", "period|pulse|pwm", "start|interrupt"]),
            (("sensor", "bme", "temperature", "humidity"), ["i2c|spi", "init", "read", "data"]),
            (("interrupt", "exti", "irq"), ["irq|nvic|exti|isr", "init", "callback", "priority"]),
            (("watchdog", "wdt"), ["watchdog|wdt|iwdg", "init", "refresh|reload"]),
            (("rtc", "clock"), ["rtc", "init", "get|set", "time"]),
        ]
        for keys, vocab in rules:
            if any(k in cat for k in keys):
                return vocab
        return []

    # ------------------------------------------------------------------ #
    # Verdict
    # ------------------------------------------------------------------ #
    def _verdict(self, out: dict) -> str:
        if out["compile_status"] in ("no_code", "empty"):
            return "empty"
        if not out["compiles"] or out["genuine_error_count"] > 0:
            return "won't_build"
        # compiles
        fp = out.get("footprint")
        over_budget = fp and (fp["flash_bytes"] > fp["flash_budget"] or fp["ram_bytes"] > fp["ram_budget"])
        bad_edge = out["subscores"].get("edge", 100) < 60
        heavy_warn = out.get("warning_count", 0) >= 8 or out.get("sdk_stub_count", 0) >= 40
        if over_budget or bad_edge:
            return "needs_fixes"
        if heavy_warn:
            return "needs_fixes"
        return "build_ready"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _load_weights(self, config_path):
        if config_path and os.path.exists(config_path):
            try:
                cfg = json.load(open(config_path))
                if isinstance(cfg, dict) and cfg.get("weights"):
                    return cfg["weights"]
            except Exception:
                pass
        return {
            "compile": 0.30, "footprint": 0.10, "edge": 0.25,
            "realtime_power": 0.10, "structure": 0.15, "functional": 0.10,
        }

    @staticmethod
    def _scan_seeded(bsp_dir):
        names = set()
        if not bsp_dir:
            return names
        h = os.path.join(bsp_dir, "mcu_stub.h")
        if not os.path.exists(h):
            return names
        txt = open(h).read()
        for m in re.finditer(r'typedef\s+(?:enum|struct|union)\s*(?:\{(?:[^{}]*)\})?\s*(\w+)\s*;', txt):
            names.add(m.group(1))
        for m in re.finditer(r'#define\s+(\w+)', txt):
            names.add(m.group(1))
        for m in re.finditer(r'struct\s+(\w+)\s*\{', txt):
            names.add("struct " + m.group(1))
        # common SDK function names (so we don't re-stub them)
        for m in re.finditer(r'\b(HAL_[A-Za-z_]+|gpio_[A-Za-z_]+|nrf_gpio_[A-Za-z_]+|k_[A-Za-z_]+|vTask[A-Za-z]+|xTask[A-Za-z]+|xQueue[A-Za-z]+|xSemaphore[A-Za-z]+|printk|DEVICE_DT_GET|GPIO_DT_SPEC_GET)\b', txt):
            names.add(m.group(1))
        return names


if __name__ == "__main__":
    import sys
    sample = sys.argv[1] if len(sys.argv) > 1 else None
    if sample and os.path.exists(sample):
        code = open(sample).read()
    else:
        code = r'''
#include "stm32f1xx_hal.h"
GPIO_InitTypeDef g;
int main(void){
    g.Pin = GPIO_PIN_13;
    HAL_GPIO_Init(GPIOB, &g);
    while(1){ HAL_GPIO_TogglePin(GPIOB, GPIO_PIN_13); HAL_Delay(500); }
    return 0;
}
'''
    ev = EdgeEvaluator()
    r = ev.evaluate(code, {"category": "LED Blink", "scenario": "blink led"})
    print(json.dumps(r, indent=2, ensure_ascii=False))
