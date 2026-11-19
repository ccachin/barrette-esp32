# main.py - lance la barrette au demarrage. Normalement, pas besoin de le modifier.
import asyncio
import gc
import json
import os
import sys
from time import ticks_ms, ticks_diff
from machine import Pin, freq

import config
freq(getattr(config, "CPU_MHZ", 160) * 1_000_000)      # AVANT le reste : moins de MHz = moins de mA

from display import Display
from led import Led, led_mode, OVERRIDES, LED_CHOICES
from scenes_fx import Gallery
from gfx import WHITE, BLACK, GREEN, ORANGE, RED
import qr
import power

FRAME_MS = getattr(config, "FRAME_MS", 40)               # 40 ms = 25 images/s max
WIFI_AUTO_OFF = getattr(config, "WIFI_AUTO_OFF", 120)    # secondes ; 0 = Wi-Fi toujours allume
PLAYLIST = config.PLAYLIST

S = {"message": config.MESSAGE, "brightness": config.BRIGHTNESS, "scene": -1, "rev": 0,
     "led": "auto", "led_brightness": config.LED_BRIGHTNESS, "image": "", "up": -100000, "page": -100000}
try:
    with open("settings.json") as f:
        S.update(json.load(f))
except (OSError, ValueError):
    pass
S["up"] = S["page"] = -100000
if S["scene"] >= len(PLAYLIST):
    S["scene"] = -1
if S["led"] != "auto" and S["led"] not in OVERRIDES:
    S["led"] = "auto"

if config.WEB:
    from web import start_ap, stop_ap, ap_clients, serve
    try:
        os.mkdir("images")
    except OSError:
        pass


def save():
    try:
        with open("settings.json", "w") as f:
            json.dump({k: S[k] for k in ("message", "brightness", "scene", "led",
                                         "led_brightness", "image")}, f)
    except OSError:
        pass


d = Display(config.PINS, rotation=config.ROTATION, baudrate=config.SPI_BAUD,
            brightness=S["brightness"], invert=config.INVERT, bgr=config.BGR)
led = None
if config.LED_ENABLED:
    try:
        led = Led(config.LED_PIN, config.LED_COUNT, S["led_brightness"], config.LED_ORDER)
    except Exception as e:
        print("LED :", e)
button = Pin(0, Pin.IN, Pin.PULL_UP)        # BOOT : appui court = scene suivante, appui long = Wi-Fi


def on_change():
    S["rev"] += 1
    d.brightness(S["brightness"])
    if led:
        led.set_brightness(S["led_brightness"])
    save()


def label(i, sc):
    return "%d. %s" % (i + 1, sc.title)


def splash(lines):
    d.fill(0)
    for i, ln in enumerate(lines):
        d.text(ln, 8, 20 + i * 14, WHITE)
    d.show()


wifi = {"on": False, "srv": False, "t0": 0, "chk": 0}

# --- Batterie -----------------------------------------------------------------
BAT_CAL = getattr(config, "BAT_CAL", 1.0)              # a regler avec un multimetre (voir config.py)
BAT_CUTOFF = getattr(config, "BAT_CUTOFF", 3.30)       # en dessous : veille profonde pour proteger la batterie (0 = jamais)
BATTERY_ICON = getattr(config, "BATTERY_ICON", False)  # petite icone sur toutes les scenes (non par defaut : voir la scene Battery)
bat = {"v": 0.0, "pct": 100, "t": -100000, "show": 0}


def bat_update(now, force=False):
    if force or ticks_diff(now, bat["t"]) > 20000:
        bat["t"] = now
        try:
            bat["v"] = power.voltage(BAT_CAL)
            bat["pct"] = power.percent(bat["v"])
        except Exception as e:
            print("batterie :", e)


def draw_battery(x, y):
    """Petite icone de batterie 22 x 10 (rien a envoyer a l'ecran : le fond est redessine par la scene)."""
    pct = bat["pct"]
    col = GREEN if pct > 30 else (ORANGE if pct > 15 else RED)
    d.fill_rect(x - 2, y - 2, 28, 14, BLACK)
    d.rect(x, y, 22, 10, WHITE)
    d.fill_rect(x + 22, y + 3, 2, 4, WHITE)
    d.fill_rect(x + 2, y + 2, max(1, 18 * pct // 100), 6, col)


async def go_sleep(reason="Veille"):
    """Veille profonde : l'ecran et la LED s'eteignent, un appui sur BOOT reveille la barrette (elle redemarre)."""
    if config.WEB and wifi["on"]:
        wifi_off()
    bat_update(ticks_ms(), True)
    d.fill(0)
    d.text(reason, 8, 20, WHITE)
    d.text("Batterie : %d %% (%.2f V)" % (bat["pct"], bat["v"]), 8, 40, WHITE)
    d.text("BOOT = reveil", 8, 60, WHITE)
    d.show()
    await asyncio.sleep(2)
    while button.value() == 0:                       # il faut relacher BOOT, sinon on se reveille aussitot
        await asyncio.sleep_ms(50)
    await asyncio.sleep_ms(300)
    power.deep_sleep(d, led)


def random_password():
    return "%08d" % (int.from_bytes(os.urandom(4), "big") % 100000000)


def wifi_payload(ssid, pwd):
    def esc(s):
        for ch in '\\;,:"':
            s = s.replace(ch, "\\" + ch)
        return s
    if pwd and len(pwd) >= 8:
        return "WIFI:T:WPA;S:%s;P:%s;;" % (esc(ssid), esc(pwd))
    return "WIFI:T:nopass;S:%s;;" % esc(ssid)


def show_connect(ip, pwd):
    """Ecran de connexion : QR Wi-Fi (le telephone le scanne) + infos."""
    d.fill(0)
    ssid = config.AP_SSID
    try:
        m = qr.encode(wifi_payload(ssid, pwd))
    except Exception as e:
        print("QR :", e)
        m = None
    land = d.width >= d.height
    side = 0
    if m:
        box = max(1, (d.height if land else d.width) // (len(m) + 4))
        y0 = (d.height - (len(m) + 4) * box) // 2 if land else 2
        side = qr.draw(d, m, 2, y0, box)
    if land:
        tx, ty, cols = side + 8, 14, (d.width - side - 8) // 8
    else:
        tx, ty, cols = 4, side + 10, d.width // 8
    lines = ["Wi-Fi :", ssid, "", "Scanne le QR", "pour te connecter", "",
             "ou ouvre :", "http://" + ip, "", "Batterie %d %%" % bat["pct"]]
    if getattr(config, "SHOW_PASSWORD", False):
        lines += ["", "Mdp : " + pwd]
    if not pwd or len(pwd) < 8:
        lines += ["", "RESEAU OUVERT !"]
    for i, ln in enumerate(lines):
        d.text(ln[:cols], tx, ty + i * 12, WHITE)
    d.show()


def show_url(ip):
    """Etape 2 : QR de l'adresse de la page de reglages (ouvre directement le navigateur)."""
    d.fill(0)
    try:
        mt = qr.encode("http://" + ip + "/")
    except Exception as e:
        print("QR :", e)
        return
    land = d.width >= d.height
    box = max(1, (d.height if land else d.width) // (len(mt) + 4))
    y0 = (d.height - (len(mt) + 4) * box) // 2 if land else 2
    side = qr.draw(d, mt, 2, y0, box)
    if land:
        tx, ty, cols = side + 8, 14, (d.width - side - 8) // 8
    else:
        tx, ty, cols = 4, side + 10, d.width // 8
    for i, ln in enumerate(["Etape 2 :", "Scanne ce QR pour", "ouvrir la page", "des reglages", "",
                            "ou touche la", "notification", "'Se connecter'"]):
        d.text(ln[:cols], tx, ty + i * 12, WHITE)
    d.show()


async def wifi_on():
    pwd = random_password() if getattr(config, "WIFI_RANDOM_PASSWORD", False) else config.AP_PASSWORD
    ip = start_ap(config.AP_SSID, pwd, getattr(config, "WIFI_TXPOWER", 8),
                  getattr(config, "WIFI_MAX_CLIENTS", 2))
    wifi["on"] = True
    wifi["t0"] = wifi["chk"] = ticks_ms()
    if not wifi["srv"]:
        wifi["srv"] = True
        gal = -1
        for k, s in enumerate(PLAYLIST):
            if isinstance(s, Gallery):
                gal = k
                break
        asyncio.create_task(serve(S, [label(k, s) for k, s in enumerate(PLAYLIST)], on_change,
                                  LED_CHOICES, d.width, d.height, gal, ip=ip))
    secs = getattr(config, "WIFI_QR_SECONDS", 25) * 1000
    show_connect(ip, pwd)                             # etape 1 : QR du Wi-Fi
    t0 = ticks_ms()
    while button.value() == 0:
        await asyncio.sleep_ms(50)
    joined = False
    while ticks_diff(ticks_ms(), t0) < secs:
        if ap_clients():
            joined = True
            break
        if button.value() == 0:
            break
        await asyncio.sleep_ms(200)
    if joined:                                        # etape 2 : QR de la page de reglages
        show_url(ip)
        t0 = ticks_ms()
        while ticks_diff(ticks_ms(), t0) < secs:
            if ticks_diff(S["page"], t0) > 0 or button.value() == 0:
                break                                 # la page est ouverte (ou appui sur BOOT)
            await asyncio.sleep_ms(200)
    while button.value() == 0:
        await asyncio.sleep_ms(50)
    wifi["t0"] = wifi["chk"] = ticks_ms()


def wifi_off():
    stop_ap()
    wifi["on"] = False


async def player():
    i = 0
    was_down = False
    press_t = 0
    hint = False
    while True:
        sel = S["scene"]
        if 0 <= sel < len(PLAYLIST):
            sc = PLAYLIST[sel]
        else:
            i %= len(PLAYLIST)
            sc = PLAYLIST[i]
            i += 1
        gc.collect()
        sc.start(d, S)
        rev = S["rev"]
        t0 = ticks_ms()
        while rev == S["rev"]:
            f0 = ticks_ms()
            if ticks_diff(f0, S["up"]) < 1500:             # envoi d'image en cours : on fige l'ecran
                await asyncio.sleep_ms(40)
                continue
            t = ticks_diff(f0, t0)
            done = sc.frame(d, S, t)
            if not sc.direct:
                if BATTERY_ICON is True or (BATTERY_ICON and (ticks_diff(bat["show"], f0) > 0 or bat["pct"] < 20)):
                    draw_battery(d.width - 28, 4)
                d.show()
            if led:
                led.update(t, led_mode(sc, S["led"]))
            if done or (sc.duration and t > sc.duration * 1000):
                break

            # Wi-Fi : s'eteint tout seul quand plus personne n'est connecte
            if config.WEB and wifi["on"] and WIFI_AUTO_OFF and ticks_diff(f0, wifi["chk"]) > 1000:
                wifi["chk"] = f0
                if ap_clients() or ticks_diff(f0, S["up"]) < 5000:
                    wifi["t0"] = f0
                elif ticks_diff(f0, wifi["t0"]) > WIFI_AUTO_OFF * 1000:
                    wifi_off()

            # Batterie : mesure toutes les 20 s, protection si elle est vide
            bat_update(f0)
            if BAT_CUTOFF and bat["v"] > 1.0 and bat["v"] < BAT_CUTOFF and ticks_diff(f0, S["up"]) > 5000:
                await go_sleep("Batterie vide")

            # Bouton BOOT : court = scene suivante ; 1,5-4 s (relache) = Wi-Fi on/off ; 4 s maintenu = veille
            down = button.value() == 0
            if down and not was_down:
                press_t = f0
            held = ticks_diff(f0, press_t) if down else 0
            if down and held > 1500:
                if not hint:
                    hint = True
                    d.fill_rect(0, d.height - 38, d.width, 38, BLACK)
                    d.text("Relache : Wi-Fi", 8, d.height - 34, WHITE)
                    d.text("Garde : veille", 8, d.height - 22, WHITE)
                    d.show()
                if held > 4000:
                    await go_sleep()
                was_down = True
                await asyncio.sleep_ms(50)
                continue
            if was_down and not down:
                was_down = hint = False
                bat["show"] = f0 + 4000
                if ticks_diff(f0, press_t) > 1500:              # appui long relache : Wi-Fi on / off
                    if config.WEB:
                        if wifi["on"]:
                            wifi_off()
                            splash(["Wi-Fi eteint"])
                            await asyncio.sleep(1)
                        else:
                            await wifi_on()
                elif S["scene"] >= 0:                           # appui court : scene suivante
                    S["scene"] = (S["scene"] + 1) % len(PLAYLIST)
                break
            was_down = down
            await asyncio.sleep_ms(max(1, FRAME_MS - ticks_diff(ticks_ms(), f0)))


async def main():
    bat_update(ticks_ms(), True)
    bat["show"] = ticks_ms() + 4000
    if BAT_CUTOFF and 1.0 < bat["v"] < BAT_CUTOFF:       # reveil avec une batterie vide : on repart dormir
        await go_sleep("Batterie vide")
    if config.WEB and getattr(config, "WIFI_AT_BOOT", True) and not power.woke_from_sleep():
        await wifi_on()                                  # (pas de QR apres un reveil de veille : on voit tout de suite les scenes)
    await player()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    raise
except Exception as e:
    d.fill(0)
    d.text("ERREUR :", 4, 4, WHITE)
    d.text(str(e)[:38], 4, 20, WHITE)
    d.show()
    sys.print_exception(e)
