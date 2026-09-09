# MCU-Benchmark

**MCU firmware code-generation benchmark with a real on-device (上机) evaluation pipeline.**

This repository bundles two things:

1. **MCU-CodeBench task set** — 324 MCU firmware code-generation tasks (plus an 80-task seed and a 12-task network family) across 6 platforms and 18 scenarios, each with a natural-language prompt, hardware constraints, expected behavior, evaluation checksais, and failure modes.
2. **The automatic evaluation pipeline** — a standalone grader that performs a real `arm-none-eabi-gcc` cross-compile of each generated snippet, measures flash/RAM footprint, checks linkability, and produces a six-dimensional quality score plus an on-device readiness verdict.

It is a standalone, self-contained benchmark: the dataset and the grader live in one repo, and the grader reads the dataset directly — no experiment harness or model is required to reproduce a score.

---

## Dataset

`data/`

| File | Tasks | Description |
|---|---|---|
| `mcucodebench_tasks.jsonl` | 324 | expanded benchmark (18 scenarios, 6 platform/framework targets, easy/medium/hard) |
| `tasks.jsonl` | 80 | seed tasks (GPIO / UART / I2C / SPI / ADC / PWM / Timer / Interrupt / FreeRTOS) |
| `tasks_net.jsonl` | 12 | network family (MQTT / BLE / HTTP / LoRa / TCP-IP / NB-IoT) |

Each line is one task with: `id`, `category`, `platform`, `framework`, `difficulty`, `prompt`, `constraints`, `expected`, `evaluation`, `failure_modes`, `scenario`, `source_refs`.

Regenerate the expanded set: `python data/scripts/generate_extended_tasks.py`

Validate tasks: `python data/validate_tasks.py`

---

## Evaluation pipeline

`src/edge_evaluator.py` — the grader. It performs a **real on-device assessment** (not brace/keyword counting):

1. **Cross-compile** — `arm-none-eabi-gcc -mcpu=<cortex-m0/m3/m4/m7> -mthumb -c -Os -Wall -Wextra` with an *auto-stub recovery loop*: missing vendor-SDK symbols are stubbed (empty header, typedef, struct field, function prototype, `#define`) up to 8 passes, so *genuine* C defects are isolated from "needs the vendor SDK" gaps. Reports `genuine_error_count` vs `sdk_stub_count`.
2. **Footprint** — `arm-none-eabi-size` gives real `.text/.data/.bss`; `flash = text+data`, `ram = data+bss`, compared against the target MCU budget.
3. **Link check** — undefined symbols are weak-stubbed and the unit is linked (`-nostartfiles -Wl,-e,Reset_Handler`) to confirm it can produce a final ELF.
4. **Six-dimension scoring** (weights from `configs/eval_metrics.yaml`):
   - `compile` (0.30) — real cross-compile success
   - `footprint` (0.10) — flash/RAM budget satisfaction
   - `edge` (0.25) — peripheral/HAL access, volatile IO, ISR safety, DMA, busy-wait timeout, HAL error checking, NULL checks, init ordering
   - `realtime_power` (0.10) — interrupt/timer/low-power/DMA vs pure polling
   - `structure` (0.15) — includes, modularity, comments, types, error handling, encapsulation
   - `functional` (0.10) — required-API coverage derived from the task category
5. **Composite `edge_score` (0-100)** — weighted sum, plus an `on_device_readiness` verdict (`build_ready` / `needs_fixes` / `won't_build` / `empty`).

`src/agent/build_tool.py` — the agent-facing wrapper around the same cross-compiler. It deliberately returns only raw diagnostics and **never** exposes the score, keeping the measurement honest.

`tools/bsp_stubs/` — ~230 KB of vendor-SDK header stubs (STM32 HAL, ESP-IDF, Pico SDK, Arduino, FreeRTOS, mbedtls, …) so generated code compiles as valid C. `src/edge_evaluator.py` picks them up automatically (`tools/bsp_stubs`), or override with `EDGE_EVAL_BSP`.

---

## Usage

### 1. Get a compiler

The GNU ARM toolchain is **not vendored** here (~1.2 GB). Any `arm-none-eabi-gcc` ≥ 10 works:

```bash
# Debian/Ubuntu
sudo apt-get install gcc-arm-none-eabi

# or point the grader at an existing install
export EDGE_EVAL_TOOLCHAIN=/path/to/toolchain/usr/bin
```

### 2. Grade generated code

```bash
python scripts/grade_generated.py \
  --tasks data/tasks.jsonl \
  --generated path/to/your/generations.json \
  --md
```

`--generated` accepts records in any of these shapes (auto-detected):

```jsonc
{"id": "GPIO_001", "code": "..."}
{"task_id": "GPIO_001", "code": "..."}
{"task": {"id": "GPIO_001"}, "code": "..."}
{"generated_code": "..."}   // positional fallback, paired to tasks in order
```

Output:

- `results/edge_eval/<set>.json` — per-task evaluations + aggregate metrics (compile %, clean %, genuine-error %, sdk-stub %, warnings, all six sub-scores, composite, readiness distribution, signal rates, per-category/per-difficulty/per-platform breakdowns).
- `results/edge_eval/<set>.md` — markdown report (with `--md`).

### Example

```bash
# quick smoke test on 4 tasks
python scripts/grade_generated.py --tasks data/tasks.jsonl \
  --generated my_gen.json --limit 4 --md

# grade the full 324-task benchmark
python scripts/grade_generated.py \
  --tasks data/mcucodebench_tasks.jsonl \
  --generated my_gen.json
```

---

## Metrics at a glance

| Metric | Meaning |
|---|---|
| `compile_success_rate` | fraction that cross-compile for the target Cortex-M |
| `clean_compile_rate` | fraction that compile with *no* SDK stubbing |
| `genuine_error_rate` | fraction failing from real C defects (not SDK gaps) |
| `sdk_stub_rate` | fraction compiling only after stubbing vendor SDK |
| `average_warnings` | mean `-Wall -Wextra` warnings |
| `avg_composite_score` | weighted six-dimension `edge_score` (0-100) |
| `build_ready` | compile + within budget + no critical anti-patterns |
| `sig_*_rate` | per-signal rates (peripheral access, ISR, DMA, timeout, low-power, …) |

---

## Repository layout

```
.
├── data/                  MCU-CodeBench task set
│   ├── mcucodebench_tasks.jsonl
│   ├── tasks.jsonl
│   ├── tasks_net.jsonl
│   ├── scripts/generate_extended_tasks.py
│   ├── validate_tasks.py
│   └── data/source_catalog.json
├── src/
│   ├── edge_evaluator.py   multi-dimension real-compile grader
│   └── agent/build_tool.py agent-facing compiler wrapper (score hidden)
├── configs/
│   └── eval_metrics.yaml   weights + target flash/RAM budgets
├── scripts/
│   └── grade_generated.py  standalone grading entry point
└── tools/
    └── bsp_stubs/          vendor-SDK header stubs
```

## License

MIT — see `LICENSE`.