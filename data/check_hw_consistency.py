# -*- coding: utf-8 -*-
"""Hardware-consistency checks: do referenced pins/peripherals exist on the target chip?"""
import json
import re
from pathlib import Path

PATH = Path(__file__).parent / "tasks.jsonl"
tasks = [json.loads(l) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip()]

def task_text(t):
    parts = [t["prompt"]] + t["constraints"] + t["expected"] + t["evaluation"]
    return " ".join(parts)

issues = []

# ---------- pin validity ----------
# STM32F103C8T6, LQFP48: PA0-15, PB0-15, PC13-15, PD0-1 (crystal)
def check_f103_pin(port, num):
    if port == "A" or port == "B": return 0 <= num <= 15
    if port == "C": return 13 <= num <= 15
    if port == "D": return num in (0, 1)
    return False

# STM32F407VG, LQFP100: PA-PE 0-15 (PH0/PH1 crystal)
def check_f407_pin(port, num):
    return port in "ABCDE" and 0 <= num <= 15 or (port == "H" and num in (0, 1))

STM32_PIN_RE = re.compile(r"\bP([A-H])(\d{1,2})\b")
ESP_PIN_RE = re.compile(r"\bGPIO\s?(\d{1,2})\b")

ESP32_VALID = set(range(0, 20)) | {21, 22, 23, 25, 26, 27} | set(range(32, 40))
ESP32_INPUT_ONLY = set(range(34, 40))
ESP32_FLASH = set(range(6, 12))
RP2040_VALID = set(range(0, 29))
RP2040_ADC = {26, 27, 28, 29}

for t in tasks:
    text = task_text(t)
    plat = t["platform"]
    if plat.startswith("STM32"):
        for m in STM32_PIN_RE.finditer(text):
            port, num = m.group(1), int(m.group(2))
            ok = check_f103_pin(port, num) if "F103" in plat else check_f407_pin(port, num)
            if not ok:
                issues.append(f"[{t['id']}] {plat}: pin P{port}{num} not available on this package")
    elif "ESP32" in plat:
        for m in ESP_PIN_RE.finditer(text):
            n = int(m.group(1))
            if n not in ESP32_VALID:
                issues.append(f"[{t['id']}] ESP32: GPIO{n} does not exist")
            elif n in ESP32_FLASH:
                issues.append(f"[{t['id']}] ESP32: GPIO{n} is a flash pin, unusable")
            # input-only used as output?
            if n in ESP32_INPUT_ONLY and re.search(
                    rf"GPIO\s?{n}[^.]*?(output|drive|toggle|blink|LED|set_level)", text, re.I):
                issues.append(f"[{t['id']}] ESP32: GPIO{n} is input-only but task implies output")
    elif "RP2040" in plat or "Pico" in plat:
        for m in ESP_PIN_RE.finditer(text):
            n = int(m.group(1))
            if n not in RP2040_VALID and n != 25:
                issues.append(f"[{t['id']}] RP2040: GPIO{n} not exposed on Pico")
            if re.search(rf"ADC[^.]*GPIO\s?{n}|GPIO\s?{n}[^.]*ADC", text, re.I) and n not in RP2040_ADC:
                issues.append(f"[{t['id']}] RP2040: GPIO{n} has no ADC channel (ADC only on 26-29)")

# ---------- peripheral instance validity ----------
F103C8_PERIPH = {"TIM": {1,2,3,4}, "SPI": {1,2}, "I2C": {1,2}, "USART": {1,2,3}, "UART": set(), "ADC": {1,2}, "DAC": set(), "CAN": {1}}
F407_PERIPH  = {"TIM": set(range(1,15)), "SPI": {1,2,3}, "I2C": {1,2,3}, "USART": {1,2,3,6}, "UART": {4,5}, "ADC": {1,2,3}, "DAC": {1,2}, "CAN": {1,2}}
PERIPH_RE = re.compile(r"\b(TIM|SPI|I2C|USART|UART|ADC|DAC|CAN)(\d{1,2})\b")

for t in tasks:
    plat = t["platform"]
    if not plat.startswith("STM32"):
        continue
    table = F103C8_PERIPH if "F103" in plat else F407_PERIPH
    for m in PERIPH_RE.finditer(task_text(t)):
        p, n = m.group(1), int(m.group(2))
        if p in table and n not in table[p]:
            issues.append(f"[{t['id']}] {plat}: peripheral {p}{n} not present on this chip")

# ---------- ESP32 peripheral naming sanity ----------
for t in tasks:
    if "ESP32" not in t["platform"]:
        continue
    text = task_text(t)
    for m in re.finditer(r"\b(UART|I2C|SPI)(\d)\b", text):
        p, n = m.group(1), int(m.group(2))
        limits = {"UART": 2, "I2C": 1, "SPI": 3}
        if n > limits[p]:
            issues.append(f"[{t['id']}] ESP32: {p}{n} out of range")

# ---------- I2C address plausibility ----------
for t in tasks:
    text = task_text(t)
    for m in re.finditer(r"0x([0-9A-Fa-f]{2})\b", text):
        v = int(m.group(1), 16)
        # only flag when clearly used as an I2C device address
        window = text[max(0, m.start()-60):m.end()+60]
        if re.search(r"[Ii]2[Cc]|address", window) and v > 0x7F and "register" not in window.lower():
            issues.append(f"[{t['id']}] suspicious I2C address 0x{v:02X} (>7-bit)")

print(f"tasks checked: {len(tasks)}")
if issues:
    print(f"\nHARDWARE ISSUES: {len(issues)}")
    for i in issues:
        print(f"  [!] {i}")
else:
    print("no hardware-consistency issues found")
