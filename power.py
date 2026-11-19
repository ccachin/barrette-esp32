# power.py - niveau de batterie (ADC) et veille profonde pour la Waveshare ESP32-S3-LCD-1.47B.
# La tension de la batterie arrive sur GPIO1 via un pont diviseur 200k / 100k (VBAT = V_ADC x 3).
import time
from machine import Pin, ADC, deepsleep, reset_cause, DEEPSLEEP_RESET

BAT_PIN = 1
DIVIDER = 3.0

# courbe de decharge d'une LiPo (tension au repos -> % approximatif)
_CURVE = ((3.30, 0), (3.50, 3), (3.60, 10), (3.70, 25), (3.80, 45),
          (3.90, 62), (4.00, 78), (4.10, 90), (4.20, 100))

_adc = None


def woke_from_sleep():
    """True si la carte vient de se reveiller d'une veille profonde (et non d'un branchement / reset)."""
    return reset_cause() == DEEPSLEEP_RESET


def voltage(cal=1.0, n=16):
    """Tension de la batterie en volts (moyenne de n mesures). cal : coefficient de correction (voir BAT_CAL)."""
    global _adc
    if _adc is None:
        _adc = ADC(Pin(BAT_PIN))
        _adc.atten(ADC.ATTN_11DB)
    s = 0
    for _ in range(n):
        try:
            s += _adc.read_uv() / 1_000_000          # tension calibree en usine
        except AttributeError:
            s += _adc.read_u16() * 3.3 / 65535       # anciennes versions de MicroPython : valeur approximative
        time.sleep_ms(2)
    return s / n * DIVIDER * cal


def percent(v):
    if v <= _CURVE[0][0]:
        return 0
    if v >= _CURVE[-1][0]:
        return 100
    for (v0, p0), (v1, p1) in zip(_CURVE, _CURVE[1:]):
        if v <= v1:
            return int(p0 + (p1 - p0) * (v - v0) / (v1 - v0))
    return 100


def deep_sleep(display=None, led=None, wake_pin=0):
    """Eteint ecran + LED et passe en veille profonde. Reveil : appui sur BOOT (GPIO0) ; la carte redemarre alors."""
    if led:
        try:
            for i in range(len(led.np)):
                led.np[i] = (0, 0, 0)
            led.np.write()
        except Exception:
            pass
    if display:
        try:
            display.bl.duty_u16(0)
            display._cmd(0x28)                       # affichage OFF
            display._cmd(0x10)                       # ST7789 en veille (SLPIN)
        except Exception:
            pass
    try:
        import esp32
        esp32.wake_on_ext0(pin=Pin(wake_pin, Pin.IN, Pin.PULL_UP), level=0)
    except Exception as e:
        print("reveil BOOT impossible :", e)
    deepsleep()
