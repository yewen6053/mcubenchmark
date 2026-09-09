# -*- coding: utf-8 -*-
"""Generate an expanded MCU-CodeBench task set and data report.

The generated tasks are prompt/evaluation metadata. They do not copy source code
from upstream projects; source references identify examples that motivated the
scenario taxonomy and should be checked before importing any upstream code.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS_OUT = ROOT / "mcucodebench_tasks.jsonl"
DEFAULT_CATALOG_OUT = ROOT / "data" / "source_catalog.json"
DEFAULT_REPORT_OUT = ROOT / "reports" / "mcucodebench_data_report.md"

DIFFICULTIES = ("easy", "medium", "hard")
REQUIRED_SCENARIOS = (
    "digital_io",
    "analog_io",
    "timing_pwm",
    "serial_uart",
    "serial_i2c",
    "serial_spi",
    "interrupts_dma",
    "rtos_concurrency",
    "clocks_power",
    "boot_flash_ota",
    "storage_filesystem",
    "usb",
    "wireless_network",
    "security_crypto",
    "sensors_actuators",
    "control_dsp",
    "debug_test",
    "safety_reliability",
)

SOURCE_CATALOG = [
    {
        "id": "stm32cube_f4",
        "name": "STMicroelectronics STM32CubeF4 examples",
        "url": "https://github.com/STMicroelectronics/STM32CubeF4",
        "license": "STMicroelectronics software license; use as reference unless license review permits code import",
        "coverage": ["STM32 HAL", "GPIO", "ADC", "DMA", "USB", "FreeRTOS", "low power", "bootloader"],
    },
    {
        "id": "stm32cube_f1",
        "name": "STMicroelectronics STM32CubeF1 examples",
        "url": "https://github.com/STMicroelectronics/STM32CubeF1",
        "license": "STMicroelectronics software license; use as reference unless license review permits code import",
        "coverage": ["STM32 HAL", "timers", "UART", "I2C", "SPI", "interrupts"],
    },
    {
        "id": "esp_idf_examples",
        "name": "Espressif ESP-IDF examples",
        "url": "https://github.com/espressif/esp-idf/tree/master/examples",
        "license": "Apache-2.0",
        "coverage": ["ESP-IDF", "Wi-Fi", "BLE", "FreeRTOS", "storage", "security", "peripherals"],
    },
    {
        "id": "pico_examples",
        "name": "Raspberry Pi Pico examples",
        "url": "https://github.com/raspberrypi/pico-examples",
        "license": "BSD-3-Clause",
        "coverage": ["Pico SDK", "PIO", "ADC", "PWM", "USB", "multicore", "DMA"],
    },
    {
        "id": "zephyr_samples",
        "name": "Zephyr samples",
        "url": "https://github.com/zephyrproject-rtos/zephyr/tree/main/samples",
        "license": "Apache-2.0",
        "coverage": ["drivers", "kernel", "Bluetooth", "networking", "power management", "testing"],
    },
    {
        "id": "freertos_demo",
        "name": "FreeRTOS demos",
        "url": "https://github.com/FreeRTOS/FreeRTOS/tree/main/FreeRTOS/Demo",
        "license": "MIT",
        "coverage": ["tasks", "queues", "timers", "semaphores", "heap", "tickless idle"],
    },
    {
        "id": "arduino_avr_examples",
        "name": "Arduino AVR core libraries and examples",
        "url": "https://github.com/arduino/ArduinoCore-avr",
        "license": "LGPL-2.1",
        "coverage": ["Arduino", "AVR", "GPIO", "analog", "serial", "Wire", "SPI"],
    },
    {
        "id": "libopencm3_examples",
        "name": "libopencm3 examples",
        "url": "https://github.com/libopencm3/libopencm3-examples",
        "license": "GPL-3.0-or-later for examples; use as reference unless license review permits code import",
        "coverage": ["bare-metal STM32", "timers", "USB", "USART", "ADC", "DMA"],
    },
    {
        "id": "tinyusb_examples",
        "name": "TinyUSB examples",
        "url": "https://github.com/hathach/tinyusb/tree/master/examples",
        "license": "MIT",
        "coverage": ["USB device", "USB host", "CDC", "HID", "MSC", "MIDI"],
    },
    {
        "id": "littlefs",
        "name": "littlefs embedded filesystem",
        "url": "https://github.com/littlefs-project/littlefs",
        "license": "BSD-3-Clause",
        "coverage": ["flash filesystem", "wear leveling", "power-loss resilience"],
    },
    {
        "id": "fatfs",
        "name": "FatFs generic FAT filesystem",
        "url": "http://elm-chan.org/fsw/ff/00index_e.html",
        "license": "FatFs license; permissive but review before redistribution",
        "coverage": ["SD card", "FAT filesystem", "block devices"],
    },
    {
        "id": "mbed_os_examples",
        "name": "Arm Mbed OS examples",
        "url": "https://github.com/ARMmbed/mbed-os-example-blinky",
        "license": "Apache-2.0",
        "coverage": ["Mbed OS", "drivers", "RTOS", "networking", "low power"],
    },
]

PLATFORMS = [
    ("STM32F103C8T6", "STM32 HAL", ["stm32cube_f1", "libopencm3_examples"]),
    ("STM32F407VG", "STM32 HAL", ["stm32cube_f4", "libopencm3_examples"]),
    ("ESP32-WROOM-32", "ESP-IDF", ["esp_idf_examples"]),
    ("RP2040 Pico", "Pico SDK", ["pico_examples"]),
    ("nRF52840 DK", "Zephyr", ["zephyr_samples"]),
    ("ATmega328P", "Arduino AVR", ["arduino_avr_examples"]),
]

SCENARIOS = {
    "digital_io": ("GPIO", "digital I/O"),
    "analog_io": ("ADC/DAC", "analog acquisition and output"),
    "timing_pwm": ("Timer/PWM", "timers, counters, PWM, capture/compare"),
    "serial_uart": ("UART", "serial console, framing, and protocol parsing"),
    "serial_i2c": ("I2C", "I2C sensors and register transactions"),
    "serial_spi": ("SPI", "SPI displays, flash, and full-duplex transfers"),
    "interrupts_dma": ("Interrupt/DMA", "interrupt latency, DMA transfer, and callback handling"),
    "rtos_concurrency": ("RTOS", "tasks, queues, timers, mutexes, and ISR handoff"),
    "clocks_power": ("Clock/Power", "clock tree, sleep modes, wakeup, and brownout"),
    "boot_flash_ota": ("Boot/Flash/OTA", "bootloader handoff, firmware update, and flash layout"),
    "storage_filesystem": ("Storage/FS", "NOR flash, SD card, FAT, and littlefs workflows"),
    "usb": ("USB", "USB CDC, HID, MSC, and composite device behavior"),
    "wireless_network": ("Wireless/Network", "Wi-Fi, BLE, sockets, MQTT, and provisioning"),
    "security_crypto": ("Security/Crypto", "secure boot, TLS, keys, RNG, and crypto APIs"),
    "sensors_actuators": ("Sensors/Actuators", "sensor drivers, calibration, motors, and displays"),
    "control_dsp": ("Control/DSP", "filters, PID loops, fixed-point DSP, and real-time control"),
    "debug_test": ("Debug/Test", "logging, assertions, host tests, and hardware-in-loop hooks"),
    "safety_reliability": ("Safety/Reliability", "watchdog, failsafe state, fault handling, and recovery"),
}

TASK_BLUEPRINTS = {
    "digital_io": [
        ("easy", "blink a status LED without blocking other polling work", ["no delay over 20 ms", "configure output before first write"]),
        ("medium", "scan a debounced matrix keypad and report stable key events", ["debounce both press and release", "avoid ghost key reports"]),
        ("hard", "implement a GPIO expander style bit-banged parallel bus with atomic updates", ["preserve unrelated pins", "document timing assumptions"]),
    ],
    "analog_io": [
        ("easy", "read one ADC channel and convert raw counts to millivolts", ["use the platform ADC reference", "avoid floating point if not needed"]),
        ("medium", "sample a thermistor and apply a lookup-table linearization", ["validate ADC range", "report sensor open/short faults"]),
        ("hard", "run multi-channel ADC acquisition with DMA and timestamped batches", ["double-buffer samples", "handle overrun without data races"]),
    ],
    "timing_pwm": [
        ("easy", "create a periodic 1 kHz timer tick callback", ["derive prescaler from clock", "keep callback under 20 us"]),
        ("medium", "drive a servo PWM output with microsecond pulse width setters", ["clamp 1000-2000 us", "avoid timer reinit on every update"]),
        ("hard", "capture input pulse width while generating an independent PWM output", ["handle counter wrap", "keep capture ISR minimal"]),
    ],
    "serial_uart": [
        ("easy", "initialize UART console logging at 115200 baud", ["8N1 framing", "nonblocking transmit where available"]),
        ("medium", "parse newline-delimited commands from a UART ring buffer", ["protect buffer indices", "reject overlong commands"]),
        ("hard", "implement DMA-backed UART receive with idle-line frame detection", ["restart DMA safely", "surface framing errors"]),
    ],
    "serial_i2c": [
        ("easy", "read a WHO_AM_I register from an I2C sensor", ["use a 7-bit address", "check transfer status"]),
        ("medium", "poll a temperature sensor and convert two-byte readings", ["big-endian register order", "timeout on bus errors"]),
        ("hard", "recover a stuck I2C bus and retry an EEPROM page write", ["respect page boundaries", "toggle SCL recovery pulses"]),
    ],
    "serial_spi": [
        ("easy", "transfer a JEDEC ID command to an SPI flash", ["control chip select explicitly", "use mode 0"]),
        ("medium", "update a small SPI display region from a framebuffer", ["set address window", "avoid full-screen redraw"]),
        ("hard", "stream SPI sensor data using DMA with cache-safe buffers", ["align DMA buffers", "invalidate cache before parse if required"]),
    ],
    "interrupts_dma": [
        ("easy", "handle a button interrupt with software debounce", ["clear interrupt flag", "defer work out of ISR"]),
        ("medium", "complete an ADC DMA transfer and publish a buffer-ready flag", ["volatile or synchronization primitive", "no printf in ISR"]),
        ("hard", "coordinate timer-triggered ADC DMA and UART telemetry without priority inversion", ["bounded ISR work", "drop or backpressure policy"]),
    ],
    "rtos_concurrency": [
        ("easy", "create two tasks that exchange heartbeat messages through a queue", ["bounded queue", "check send/receive return values"]),
        ("medium", "protect an I2C bus shared by sensor and display tasks", ["mutex timeout", "no blocking while holding unrelated locks"]),
        ("hard", "design ISR-to-task telemetry using queue sets or notifications", ["no heap allocation after init", "handle queue overflow"]),
    ],
    "clocks_power": [
        ("easy", "configure the system clock and expose a function returning Hz", ["validate PLL assumptions", "keep SysTick correct"]),
        ("medium", "enter low-power sleep and wake on GPIO interrupt", ["reconfigure clocks after wake if needed", "preserve wake reason"]),
        ("hard", "implement tickless idle with RTC wakeup and peripheral quiesce hooks", ["disable unsafe peripherals", "measure lost ticks"]),
    ],
    "boot_flash_ota": [
        ("easy", "read firmware version metadata from a fixed flash address", ["check magic number", "avoid unaligned access"]),
        ("medium", "write a bootloader handoff record and jump to an application image", ["set vector table", "validate stack pointer"]),
        ("hard", "implement dual-slot OTA selection with rollback after failed health check", ["atomic slot metadata", "wear-aware flash writes"]),
    ],
    "storage_filesystem": [
        ("easy", "append diagnostic records to a flash-backed circular log", ["handle wraparound", "do not erase on every record"]),
        ("medium", "mount an SD card filesystem and write CSV sensor samples", ["flush on interval", "handle card removal"]),
        ("hard", "store configuration in littlefs with power-loss-safe commit semantics", ["version records", "fallback to defaults on corruption"]),
    ],
    "usb": [
        ("easy", "expose a USB CDC serial echo endpoint", ["do not block USB task", "handle host disconnect"]),
        ("medium", "implement a USB HID keyboard report sender", ["debounce key input", "send key release reports"]),
        ("hard", "build a composite CDC plus MSC device backed by flash", ["serialize flash access", "handle host eject"]),
    ],
    "wireless_network": [
        ("easy", "connect to Wi-Fi and publish connection state", ["bounded retry count", "mask credentials in logs"]),
        ("medium", "send MQTT telemetry with reconnect backoff", ["QoS documented", "offline queue limit"]),
        ("hard", "run BLE provisioning that stores credentials and starts Wi-Fi", ["secure pairing mode", "erase credentials command"]),
    ],
    "security_crypto": [
        ("easy", "generate random bytes using the hardware RNG or approved API", ["check entropy API status", "no rand() for keys"]),
        ("medium", "verify a signed configuration blob before applying it", ["constant-time hash compare where available", "reject rollback version"]),
        ("hard", "configure TLS client credentials from secure storage", ["no private key logging", "validate server certificate"]),
    ],
    "sensors_actuators": [
        ("easy", "read a digital temperature sensor and expose Celsius values", ["sensor init sequence", "range check readings"]),
        ("medium", "control a stepper motor with acceleration limits", ["bounded step rate", "safe disable on fault"]),
        ("hard", "fuse IMU gyro and accelerometer data for orientation output", ["calibration offsets", "fixed update period"]),
    ],
    "control_dsp": [
        ("easy", "apply a moving-average filter to ADC samples", ["fixed window size", "avoid accumulator overflow"]),
        ("medium", "run a fixed-point PID loop for motor speed control", ["anti-windup", "saturate output"]),
        ("hard", "execute an FFT or biquad filter pipeline within a timer budget", ["measure cycle count", "avoid dynamic allocation"]),
    ],
    "debug_test": [
        ("easy", "add compile-time configurable logging macros", ["zero cost when disabled", "timestamp messages if available"]),
        ("medium", "create host-testable pure functions for packet parsing", ["no hardware dependencies in parser", "include malformed packet tests"]),
        ("hard", "add a hardware-in-loop self-test command for GPIO, ADC, and UART", ["safe pin states", "machine-readable result output"]),
    ],
    "safety_reliability": [
        ("easy", "configure a watchdog and refresh it from the main health loop", ["do not refresh inside every ISR", "record reset cause"]),
        ("medium", "enter a failsafe output state when sensor readings are invalid", ["define invalid thresholds", "latched fault until cleared"]),
        ("hard", "implement fault containment for brownout, stack overflow, and task deadlock", ["persistent fault log", "safe restart policy"]),
    ],
}

EXTRA_SOURCE_BY_SCENARIO = {
    "rtos_concurrency": ["freertos_demo"],
    "storage_filesystem": ["littlefs", "fatfs"],
    "usb": ["tinyusb_examples"],
    "wireless_network": ["zephyr_samples", "mbed_os_examples"],
    "security_crypto": ["zephyr_samples", "esp_idf_examples"],
    "clocks_power": ["stm32cube_f4", "zephyr_samples"],
    "boot_flash_ota": ["esp_idf_examples", "stm32cube_f4"],
    "debug_test": ["zephyr_samples"],
}


def source_catalog_by_id() -> dict[str, dict]:
    return {source["id"]: dict(source) for source in SOURCE_CATALOG}


def _source_refs(platform_sources: list[str], scenario: str) -> list[str]:
    refs = list(dict.fromkeys(platform_sources + EXTRA_SOURCE_BY_SCENARIO.get(scenario, [])))
    return refs


def generate_tasks() -> list[dict]:
    tasks = []
    counters = defaultdict(int)
    for scenario in REQUIRED_SCENARIOS:
        category, description = SCENARIOS[scenario]
        for platform, framework, platform_sources in PLATFORMS:
            for difficulty, action, constraints in TASK_BLUEPRINTS[scenario]:
                counters[scenario] += 1
                task_id = f"{scenario.upper()}_{counters[scenario]:03d}"
                source_refs = _source_refs(platform_sources, scenario)
                prompt = (
                    f"Generate {framework} firmware for {platform} to {action}. "
                    f"Target scenario: {description}."
                )
                expected = [
                    "Compilable C or C++ firmware module plus required initialization code",
                    "Clear separation between hardware initialization and application logic",
                ]
                evaluation = [
                    f"Build against the {framework} SDK or a documented mock-compatible project",
                    "Static check for bounded error handling and required API usage",
                    "Host/mock unit test for the scenario-specific edge case when hardware is unavailable",
                ]
                failure_modes = [
                    "wrong_sdk_api",
                    "missing_error_handling",
                    "unbounded_blocking",
                    f"{scenario}_logic_error",
                ]
                tasks.append(
                    {
                        "id": task_id,
                        "category": category,
                        "platform": platform,
                        "framework": framework,
                        "difficulty": difficulty,
                        "scenario": scenario,
                        "prompt": prompt,
                        "constraints": list(constraints),
                        "expected": expected,
                        "evaluation": evaluation,
                        "failure_modes": failure_modes,
                        "source_refs": source_refs,
                    }
                )
    return tasks


def write_jsonl(tasks: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for task in tasks:
            fh.write(json.dumps(task, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_source_catalog(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(SOURCE_CATALOG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _markdown_table(rows: list[list[str]]) -> str:
    header = "| " + " | ".join(rows[0]) + " |"
    sep = "| " + " | ".join(["---"] * len(rows[0])) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join([header, sep] + body)


def build_report(tasks: list[dict]) -> str:
    by_scenario = Counter(task["scenario"] for task in tasks)
    by_platform = Counter(task["platform"] for task in tasks)
    by_difficulty = Counter(task["difficulty"] for task in tasks)
    by_source = Counter(ref for task in tasks for ref in task["source_refs"])
    catalog = source_catalog_by_id()
    seed_path = ROOT / "tasks.jsonl"
    seed_count = 0
    if seed_path.exists():
        seed_count = sum(1 for line in seed_path.read_text(encoding="utf-8").splitlines() if line.strip())

    scenario_rows = [["Scenario", "Category", "Tasks"]]
    for scenario in REQUIRED_SCENARIOS:
        scenario_rows.append([scenario, SCENARIOS[scenario][0], str(by_scenario[scenario])])

    platform_rows = [["Platform", "Framework", "Tasks"]]
    framework_by_platform = {platform: framework for platform, framework, _ in PLATFORMS}
    for platform, count in sorted(by_platform.items()):
        platform_rows.append([platform, framework_by_platform[platform], str(count)])

    source_rows = [["Source", "License note", "Referenced tasks", "URL"]]
    for source_id, count in sorted(by_source.items()):
        source = catalog[source_id]
        source_rows.append([source["name"], source["license"], str(count), source["url"]])

    difficulty_line = ", ".join(f"{name}: {by_difficulty[name]}" for name in DIFFICULTIES)
    return "\n".join(
        [
            "# MCU-CodeBench Expanded Data Report",
            "",
            "## Research Conclusion",
            "",
            "No single public dataset found in this workspace can be adopted as a complete MCU firmware code-generation benchmark. The practical path is to build MCU-CodeBench from original task metadata, using public SDK examples and embedded projects as scenario/API references. This avoids copying vendor or GPL example code while still grounding tasks in real MCU development workflows.",
            "",
            "Recommended upstream sources are split into three groups:",
            "",
            "- Vendor SDK examples: STM32CubeF1/F4, ESP-IDF, Pico SDK, Zephyr, Arduino AVR, and Mbed OS. These are the best references for buildable API patterns and board-specific behavior.",
            "- Middleware and subsystem projects: FreeRTOS, TinyUSB, littlefs, and FatFs. These cover RTOS primitives, USB classes, and storage workflows that the current seed set barely exercises.",
            "- Bare-metal reference examples: libopencm3 examples. Useful for peripheral coverage, but license review is required before bundling code.",
            "",
            "## Summary",
            "",
            f"- Existing seed tasks in tasks.jsonl: {seed_count}",
            f"- Generated tasks: {len(tasks)}",
            f"- Data expansion factor over seed: {len(tasks) / seed_count:.1f}x" if seed_count else "- Data expansion factor over seed: n/a",
            f"- Scenarios covered: {len(by_scenario)} / {len(REQUIRED_SCENARIOS)}",
            f"- Platforms covered: {len(by_platform)}",
            f"- Difficulty distribution: {difficulty_line}",
            "- Task records include prompt, constraints, expected artifacts, evaluation hooks, failure labels, scenario, and source_refs.",
            "- The generated JSONL is deterministic; re-run scripts/generate_extended_tasks.py after editing the taxonomy or source catalog.",
            "",
            "## Coverage Taxonomy",
            "",
            "The taxonomy treats MCU firmware development as 18 task families. Each family has one easy, medium, and hard task for each supported platform/framework pair. This gives balanced coverage across peripheral work, concurrency, power, boot/update, connectivity, storage, security, testability, and reliability.",
            "",
            "## Scenario Coverage",
            "",
            _markdown_table(scenario_rows),
            "",
            "## Platform Coverage",
            "",
            _markdown_table(platform_rows),
            "",
            "## Public Sources Considered",
            "",
            _markdown_table(source_rows),
            "",
            "## Inclusion Guidance",
            "",
            "- Treat upstream repositories as scenario and API references unless their license permits copying code into this benchmark.",
            "- Prefer importing metadata, build commands, and small original tasks over copying complete example source files.",
            "- For vendor SDKs with restrictive terms, keep only derived prompts and point evaluators at locally installed SDK examples.",
            "- Freeze SDK versions, board packages, compiler versions, and build commands before publishing model scores.",
            "- Add reference implementations only after each platform target has a pinned board, toolchain, SDK commit, and CI or hardware-in-loop runner.",
            "",
            "## Suggested Evaluation Gates",
            "",
            "- JSONL integrity: schema, unique IDs, non-empty constraints, expected outputs, evaluation hooks, failure modes, and resolvable source_refs.",
            "- Static checks: forbidden API use, pin/peripheral validity, blocking calls in ISR/RTOS contexts, bounds checks, and flash-write safety.",
            "- Build checks: compile each generated answer against the pinned SDK project or mock-compatible host build.",
            "- Behavioral checks: host tests for pure logic and hardware-in-loop tests for timing, bus transactions, low-power wakeup, USB, wireless, and watchdog behavior.",
            "- Reporting: record compile success, warnings, binary size, RAM use, static-rule pass rate, behavioral pass rate, and repair rounds.",
            "",
            "## Remaining Gaps",
            "",
            "- This benchmark covers task families, not every MCU, board, peripheral mux, package variant, or RTOS port.",
            "- Hardware-in-loop pass/fail still needs board-specific harnesses and reference solutions.",
            "- License review is required before bundling any upstream source code rather than generated task metadata.",
            "- Security, OTA, wireless, USB, and low-power tasks should receive reference implementations before leaderboard use.",
            "- Some generated tasks are intentionally cross-platform abstractions; platform-specific pin maps and exact SDK calls should be specialized before using them as strict compile benchmarks.",
            "",
        ]
    )


def write_report(tasks: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_report(tasks), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-out", type=Path, default=DEFAULT_TASKS_OUT)
    parser.add_argument("--catalog-out", type=Path, default=DEFAULT_CATALOG_OUT)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    args = parser.parse_args()

    tasks = generate_tasks()
    write_jsonl(tasks, args.tasks_out)
    write_source_catalog(args.catalog_out)
    write_report(tasks, args.report_out)
    print(f"wrote {len(tasks)} tasks to {args.tasks_out}")
    print(f"wrote source catalog to {args.catalog_out}")
    print(f"wrote data report to {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
