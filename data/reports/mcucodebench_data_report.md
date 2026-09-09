# MCU-CodeBench Expanded Data Report

## Research Conclusion

No single public dataset found in this workspace can be adopted as a complete MCU firmware code-generation benchmark. The practical path is to build MCU-CodeBench from original task metadata, using public SDK examples and embedded projects as scenario/API references. This avoids copying vendor or GPL example code while still grounding tasks in real MCU development workflows.

Recommended upstream sources are split into three groups:

- Vendor SDK examples: STM32CubeF1/F4, ESP-IDF, Pico SDK, Zephyr, Arduino AVR, and Mbed OS. These are the best references for buildable API patterns and board-specific behavior.
- Middleware and subsystem projects: FreeRTOS, TinyUSB, littlefs, and FatFs. These cover RTOS primitives, USB classes, and storage workflows that the current seed set barely exercises.
- Bare-metal reference examples: libopencm3 examples. Useful for peripheral coverage, but license review is required before bundling code.

## Summary

- Existing seed tasks in tasks.jsonl: 80
- Generated tasks: 324
- Data expansion factor over seed: 4.0x
- Scenarios covered: 18 / 18
- Platforms covered: 6
- Difficulty distribution: easy: 108, medium: 108, hard: 108
- Task records include prompt, constraints, expected artifacts, evaluation hooks, failure labels, scenario, and source_refs.
- The generated JSONL is deterministic; re-run scripts/generate_extended_tasks.py after editing the taxonomy or source catalog.

## Coverage Taxonomy

The taxonomy treats MCU firmware development as 18 task families. Each family has one easy, medium, and hard task for each supported platform/framework pair. This gives balanced coverage across peripheral work, concurrency, power, boot/update, connectivity, storage, security, testability, and reliability.

## Scenario Coverage

| Scenario | Category | Tasks |
| --- | --- | --- |
| digital_io | GPIO | 18 |
| analog_io | ADC/DAC | 18 |
| timing_pwm | Timer/PWM | 18 |
| serial_uart | UART | 18 |
| serial_i2c | I2C | 18 |
| serial_spi | SPI | 18 |
| interrupts_dma | Interrupt/DMA | 18 |
| rtos_concurrency | RTOS | 18 |
| clocks_power | Clock/Power | 18 |
| boot_flash_ota | Boot/Flash/OTA | 18 |
| storage_filesystem | Storage/FS | 18 |
| usb | USB | 18 |
| wireless_network | Wireless/Network | 18 |
| security_crypto | Security/Crypto | 18 |
| sensors_actuators | Sensors/Actuators | 18 |
| control_dsp | Control/DSP | 18 |
| debug_test | Debug/Test | 18 |
| safety_reliability | Safety/Reliability | 18 |

## Platform Coverage

| Platform | Framework | Tasks |
| --- | --- | --- |
| ATmega328P | Arduino AVR | 54 |
| ESP32-WROOM-32 | ESP-IDF | 54 |
| RP2040 Pico | Pico SDK | 54 |
| STM32F103C8T6 | STM32 HAL | 54 |
| STM32F407VG | STM32 HAL | 54 |
| nRF52840 DK | Zephyr | 54 |

## Public Sources Considered

| Source | License note | Referenced tasks | URL |
| --- | --- | --- | --- |
| Arduino AVR core libraries and examples | LGPL-2.1 | 54 | https://github.com/arduino/ArduinoCore-avr |
| Espressif ESP-IDF examples | Apache-2.0 | 84 | https://github.com/espressif/esp-idf/tree/master/examples |
| FatFs generic FAT filesystem | FatFs license; permissive but review before redistribution | 18 | http://elm-chan.org/fsw/ff/00index_e.html |
| FreeRTOS demos | MIT | 18 | https://github.com/FreeRTOS/FreeRTOS/tree/main/FreeRTOS/Demo |
| libopencm3 examples | GPL-3.0-or-later for examples; use as reference unless license review permits code import | 108 | https://github.com/libopencm3/libopencm3-examples |
| littlefs embedded filesystem | BSD-3-Clause | 18 | https://github.com/littlefs-project/littlefs |
| Arm Mbed OS examples | Apache-2.0 | 18 | https://github.com/ARMmbed/mbed-os-example-blinky |
| Raspberry Pi Pico examples | BSD-3-Clause | 54 | https://github.com/raspberrypi/pico-examples |
| STMicroelectronics STM32CubeF1 examples | STMicroelectronics software license; use as reference unless license review permits code import | 54 | https://github.com/STMicroelectronics/STM32CubeF1 |
| STMicroelectronics STM32CubeF4 examples | STMicroelectronics software license; use as reference unless license review permits code import | 84 | https://github.com/STMicroelectronics/STM32CubeF4 |
| TinyUSB examples | MIT | 18 | https://github.com/hathach/tinyusb/tree/master/examples |
| Zephyr samples | Apache-2.0 | 114 | https://github.com/zephyrproject-rtos/zephyr/tree/main/samples |

## Inclusion Guidance

- Treat upstream repositories as scenario and API references unless their license permits copying code into this benchmark.
- Prefer importing metadata, build commands, and small original tasks over copying complete example source files.
- For vendor SDKs with restrictive terms, keep only derived prompts and point evaluators at locally installed SDK examples.
- Freeze SDK versions, board packages, compiler versions, and build commands before publishing model scores.
- Add reference implementations only after each platform target has a pinned board, toolchain, SDK commit, and CI or hardware-in-loop runner.

## Suggested Evaluation Gates

- JSONL integrity: schema, unique IDs, non-empty constraints, expected outputs, evaluation hooks, failure modes, and resolvable source_refs.
- Static checks: forbidden API use, pin/peripheral validity, blocking calls in ISR/RTOS contexts, bounds checks, and flash-write safety.
- Build checks: compile each generated answer against the pinned SDK project or mock-compatible host build.
- Behavioral checks: host tests for pure logic and hardware-in-loop tests for timing, bus transactions, low-power wakeup, USB, wireless, and watchdog behavior.
- Reporting: record compile success, warnings, binary size, RAM use, static-rule pass rate, behavioral pass rate, and repair rounds.

## Remaining Gaps

- This benchmark covers task families, not every MCU, board, peripheral mux, package variant, or RTOS port.
- Hardware-in-loop pass/fail still needs board-specific harnesses and reference solutions.
- License review is required before bundling any upstream source code rather than generated task metadata.
- Security, OTA, wireless, USB, and low-power tasks should receive reference implementations before leaderboard use.
- Some generated tasks are intentionally cross-platform abstractions; platform-specific pin maps and exact SDK calls should be specialized before using them as strict compile benchmarks.
