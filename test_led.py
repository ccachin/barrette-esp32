# test_led.py - teste la LED WS2812 : rouge, vert, bleu, blanc, puis arc-en-ciel (Ctrl+C pour arreter).
# Si les couleurs sont fausses : changer LED_ORDER dans config.py ("GRB", "BRG"...).
import time
import config
from led import Led

led = Led(config.LED_PIN, config.LED_COUNT, 40, config.LED_ORDER)
for nom, c in (("ROUGE", (255, 0, 0)), ("VERT", (0, 255, 0)), ("BLEU", (0, 0, 255)), ("BLANC", (255, 255, 255))):
    print(nom)
    for i in range(led.n):
        led._put(i, c)
    led.np.write()
    time.sleep(1)
print("arc-en-ciel")
t = 0
while True:
    led.update(t, ("rainbow",))
    t += 30
    time.sleep_ms(30)
