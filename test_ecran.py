# test_ecran.py - verifie ecran, couleurs et orientation. Lancer dans Thonny (F5).
import config
from display import Display
from gfx import *

d = Display(config.PINS, rotation=config.ROTATION, baudrate=config.SPI_BAUD,
            brightness=80, invert=config.INVERT, bgr=config.BGR)
w, h = d.width, d.height
d.fill(0)
bars = (("ROUGE", RED), ("VERT", GREEN), ("BLEU", BLUE), ("BLANC", WHITE))
bw = w // 4
for i, (nom, col) in enumerate(bars):
    d.fill_rect(i * bw, 0, bw, h - 30, col)
    d.text(nom, i * bw + 4, 8, BLACK if col != BLUE else WHITE)
d.rect(0, 0, w, h, WHITE)                     # cadre 1 px : doit toucher les 4 bords
d.text("TEST %dx%d  coin haut-gauche ->" % (w, h), 4, h - 20, WHITE)
d.show()
print("Si ROUGE n'est pas rouge : BGR = True. Si negatif : INVERT = False.")
print("Si le cadre est decale/coupe : voir offsets (display.py) ou PINS.")
