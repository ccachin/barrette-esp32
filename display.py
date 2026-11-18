# display.py - Pilote ST7789 172x320 (Waveshare ESP32-S3-LCD-1.47) en MicroPython pur.
# L'ecran est un "framebuffer" RGB565 en RAM (dans la PSRAM) : on dessine avec
# d.fill(), d.text(), d.fill_rect()... puis d.show() envoie tout a l'ecran.
import framebuf
import time
from machine import Pin, SPI, PWM


class Display(framebuf.FrameBuffer):
    def __init__(self, pins, rotation=1, baudrate=40_000_000,
                 brightness=60, invert=True, bgr=False):
        # pins = dict(sck=, mosi=, cs=, dc=, rst=, bl=)
        self.spi = SPI(1, baudrate=baudrate, polarity=0, phase=0,
                       sck=Pin(pins["sck"]), mosi=Pin(pins["mosi"]))
        self.cs = Pin(pins["cs"], Pin.OUT, value=1)
        self.dc = Pin(pins["dc"], Pin.OUT, value=0)
        self.rst = Pin(pins["rst"], Pin.OUT, value=1)
        self.bl = PWM(Pin(pins["bl"]), freq=2000, duty_u16=0)

        # La dalle fait 172 px sur 240 px de RAM controleur : 34 px de marge de chaque cote.
        if rotation in (1, 3):          # paysage 320 x 172
            w, h, self.xs, self.ys = 320, 172, 0, 34
        else:                           # portrait 172 x 320
            w, h, self.xs, self.ys = 172, 320, 34, 0
        self.width, self.height = w, h
        self.buf = bytearray(w * h * 2)
        super().__init__(self.buf, w, h, framebuf.RGB565)

        madctl = (0x00, 0x60, 0xC0, 0xA0)[rotation & 3]
        if bgr:
            madctl |= 0x08
        self._init(madctl, invert)
        self.fill(0)
        self.show()
        self.brightness(brightness)

    # --- bas niveau -------------------------------------------------------
    def _cmd(self, c, data=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes((c,)))
        if data:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def _init(self, madctl, invert):
        self.rst(1); time.sleep_ms(10)
        self.rst(0); time.sleep_ms(20)
        self.rst(1); time.sleep_ms(120)
        c = self._cmd
        c(0x01); time.sleep_ms(150)             # reset logiciel
        c(0x11); time.sleep_ms(120)             # sortie de veille
        c(0x3A, b"\x55")                        # RGB565
        c(0x36, bytes((madctl,)))               # orientation
        c(0xB2, b"\x0c\x0c\x00\x33\x33")
        c(0xB7, b"\x35")
        c(0xBB, b"\x35")
        c(0xC0, b"\x2c")
        c(0xC2, b"\x01")
        c(0xC3, b"\x13")
        c(0xC4, b"\x20")
        c(0xC6, b"\x0f")
        c(0xD0, b"\xa4\xa1")
        c(0x21 if invert else 0x20)             # inversion (necessaire sur dalle IPS)
        c(0x13)                                 # mode normal
        c(0x29); time.sleep_ms(50)              # affichage ON

    def _window(self):
        x0, y0 = self.xs, self.ys
        x1, y1 = x0 + self.width - 1, y0 + self.height - 1
        self._cmd(0x2A, bytes((x0 >> 8, x0 & 255, x1 >> 8, x1 & 255)))
        self._cmd(0x2B, bytes((y0 >> 8, y0 & 255, y1 >> 8, y1 & 255)))

    # --- API --------------------------------------------------------------
    def show(self):
        """Envoie le framebuffer a l'ecran."""
        self.show_raw(self.buf)

    def show_raw(self, data):
        """Envoie directement un buffer RGB565 (big-endian) a l'ecran."""
        self._window()
        self.cs(0)
        self.dc(0)
        self.spi.write(b"\x2c")
        self.dc(1)
        self.spi.write(data)
        self.cs(1)

    def brightness(self, pct):
        pct = max(0, min(100, int(pct)))
        self.bl.duty_u16(pct * 65535 // 100)
