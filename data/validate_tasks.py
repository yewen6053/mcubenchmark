# -*- coding: utf-8 -*-
"""Integrity / quality checks for tasks.jsonl (MCU-CodeBench draft)."""
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

PATH = Path(__file__).parent / "tasks.jsonl"

REQUIRED_FIELDS = {
    "id": str,
    "category": str,
    "platform": str,
    "framework": str,
    "difficulty": str,
    "prompt": str,
    "constraints": list,
    "expected": list,
    "evaluation": list,
    "failure_modes": list,
}
README_CATEGORIES = {"GPIO", "UART", "I2C", "SPI", "ADC", "PWM", "Timer", "Interrupt", "FreeRTOS"}
DIFFICULTIES = {"easy", "medium", "hard"}

errors, warnings = [], []
tasks = []

# ---- 1. line-level JSON parse + schema ----
raw_lines = PATH.read_text(encoding="utf-8").splitlines()
for lineno, line in enumerate(raw_lines, 1):
    if not line.strip():
        warnings.append(f"line {lineno}: blank line")
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        errors.append(f"line {lineno}: invalid JSON ({e})")
        continue
    extra = set(obj) - set(REQUIRED_FIELDS)
    missing = set(REQUIRED_FIELDS) - set(obj)
    if missing:
        errors.append(f"line {lineno} [{obj.get('id','?')}]: missing fields {sorted(missing)}")
    if extra:
        warnings.append(f"line {lineno} [{obj.get('id','?')}]: unexpected fields {sorted(extra)}")
    for f, typ in REQUIRED_FIELDS.items():
        if f in obj:
            if not isinstance(obj[f], typ):
                errors.append(f"line {lineno} [{obj.get('id','?')}]: field '{f}' should be {typ.__name__}, got {type(obj[f]).__name__}")
            elif typ is str and not obj[f].strip():
                errors.append(f"line {lineno} [{obj.get('id','?')}]: field '{f}' is empty string")
            elif typ is list:
                if len(obj[f]) == 0:
                    errors.append(f"line {lineno} [{obj.get('id','?')}]: field '{f}' is empty list")
                for i, item in enumerate(obj[f]):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"line {lineno} [{obj.get('id','?')}]: '{f}[{i}]' not a non-empty string")
    obj["_line"] = lineno
    tasks.append(obj)

# ---- 2. id uniqueness / format / category prefix / numbering ----
ids = [t["id"] for t in tasks if "id" in t]
for dup, n in Counter(ids).items():
    if n > 1:
        errors.append(f"duplicate id '{dup}' appears {n} times")

id_re = re.compile(r"^([A-Za-z0-9]+)_(\d{3})$")
cat_numbers = defaultdict(list)
for t in tasks:
    m = id_re.match(t.get("id", ""))
    if not m:
        errors.append(f"[{t.get('id','?')}]: id does not match PREFIX_NNN pattern")
        continue
    prefix, num = m.group(1), int(m.group(2))
    cat_norm = t.get("category", "").replace("/", "").replace(" ", "").upper()
    if prefix.upper() not in cat_norm and cat_norm not in prefix.upper():
        warnings.append(f"[{t['id']}]: id prefix '{prefix}' vs category '{t.get('category')}'")
    cat_numbers[prefix].append(num)

for prefix, nums in sorted(cat_numbers.items()):
    nums_sorted = sorted(nums)
    expect = list(range(1, len(nums_sorted) + 1))
    if nums_sorted != expect:
        gaps = sorted(set(expect) - set(nums_sorted))
        extras = sorted(set(nums_sorted) - set(expect))
        warnings.append(f"{prefix}: numbering not contiguous 1..{len(nums)} (missing {gaps}, out-of-range {extras})")

# ---- 3. enum checks ----
for t in tasks:
    if t.get("difficulty") not in DIFFICULTIES:
        errors.append(f"[{t.get('id','?')}]: difficulty '{t.get('difficulty')}' not in {sorted(DIFFICULTIES)}")
    cat = t.get("category", "")
    base = cat.split("/")[0].strip()
    if cat not in README_CATEGORIES and base not in README_CATEGORIES:
        warnings.append(f"[{t.get('id','?')}]: category '{cat}' not in README list")

# ---- 4. platform <-> framework consistency ----
def plat_family(p):
    p = p.upper()
    if p.startswith("STM32"): return "STM32"
    if "ESP32" in p: return "ESP32"
    if "RP2040" in p or "PICO" in p: return "RP2040"
    if "NRF" in p: return "NRF"
    if "AVR" in p or "ATMEGA" in p: return "AVR"
    return p

fw_expect = {"STM32": ("STM32", "HAL", "LL", "CMSIS", "CUBE"),
             "ESP32": ("ESP-IDF", "ESP", "ARDUINO"),
             "RP2040": ("PICO", "SDK"),
             "NRF": ("NRF", "ZEPHYR"),
             "AVR": ("AVR", "ARDUINO")}
for t in tasks:
    fam = plat_family(t.get("platform", ""))
    fw = t.get("framework", "").upper()
    if fam in fw_expect and not any(k in fw for k in fw_expect[fam]):
        warnings.append(f"[{t.get('id','?')}]: platform '{t.get('platform')}' with framework '{t.get('framework')}' looks inconsistent")

# ---- 5. duplicate / near-duplicate prompts ----
prompts = [(t["id"], t["prompt"]) for t in tasks if "prompt" in t]
for i in range(len(prompts)):
    for j in range(i + 1, len(prompts)):
        a, b = prompts[i], prompts[j]
        if a[1] == b[1]:
            errors.append(f"identical prompt: {a[0]} == {b[0]}")
        elif SequenceMatcher(None, a[1], b[1]).ratio() > 0.90:
            warnings.append(f"near-duplicate prompt (>{90}%): {a[0]} ~ {b[0]}")

# ---- 6. failure_modes vocabulary ----
fm_counter = Counter(fm for t in tasks for fm in t.get("failure_modes", []))
bad_fm = [fm for fm in fm_counter if not re.match(r"^[a-z0-9_]+$", fm)]
for fm in bad_fm:
    warnings.append(f"failure_mode label not snake_case: '{fm}'")

# ---- 7. distributions ----
def dist(field):
    return Counter(t.get(field, "?") for t in tasks)

print("=" * 64)
print(f"tasks parsed: {len(tasks)} / {len([l for l in raw_lines if l.strip()])} non-empty lines")
print("\n-- category x difficulty --")
cats = dist("category")
grid = defaultdict(Counter)
for t in tasks:
    grid[t.get("category", "?")][t.get("difficulty", "?")] += 1
print(f"{'category':<22}{'easy':>6}{'medium':>8}{'hard':>6}{'total':>7}")
for c in sorted(grid):
    g = grid[c]
    print(f"{c:<22}{g.get('easy',0):>6}{g.get('medium',0):>8}{g.get('hard',0):>6}{sum(g.values()):>7}")
tot = Counter()
for g in grid.values(): tot.update(g)
print(f"{'TOTAL':<22}{tot.get('easy',0):>6}{tot.get('medium',0):>8}{tot.get('hard',0):>6}{sum(tot.values()):>7}")

print("\n-- platform --")
for p, n in dist("platform").most_common():
    print(f"  {p:<24}{n:>3}")
print("\n-- framework --")
for f, n in dist("framework").most_common():
    print(f"  {f:<24}{n:>3}")

print(f"\n-- failure_modes: {len(fm_counter)} unique labels, top 10 --")
for fm, n in fm_counter.most_common(10):
    print(f"  {fm:<32}{n:>3}")
singletons = [fm for fm, n in fm_counter.items() if n == 1]
print(f"  (labels used only once: {len(singletons)})")

plens = sorted(len(t.get("prompt", "")) for t in tasks)
print(f"\n-- prompt length (chars): min {plens[0]}, median {plens[len(plens)//2]}, max {plens[-1]}")

print("\n" + "=" * 64)
print(f"ERRORS: {len(errors)}")
for e in errors:
    print(f"  [E] {e}")
print(f"WARNINGS: {len(warnings)}")
for w in warnings:
    print(f"  [W] {w}")
sys.exit(1 if errors else 0)
