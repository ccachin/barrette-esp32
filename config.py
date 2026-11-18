# config.py - C'EST LE FICHIER A MODIFIER pour personnaliser la barrette.
from scenes import *
from scenes_fx import *
from led import leds            # leds(scene, effet...) : choisir l'effet de la LED pour une scene

# --- Materiel ---------------------------------------------------------------
# Brochage Waveshare ESP32-S3-LCD-1.47B (USB-C) : retroeclairage sur GPIO46.
# (Sur le modele USB-A d'origine, c'est bl=48.) Si l'ecran reste noir : verifier ici.
PINS = dict(sck=40, mosi=45, cs=42, dc=41, rst=39, bl=46)
ROTATION = 1            # 1 = paysage ; 3 = paysage retourne ; 0/2 = portrait
SPI_BAUD = 40_000_000   # essayer 80_000_000 si stable
INVERT = True           # mettre False si les couleurs sont en negatif
BGR = False             # mettre True si rouge et bleu sont inverses

# --- LED WS2812 sous l'ecran (GPIO38) -----------------------------------------
LED_ENABLED = True
LED_PIN = 38
LED_COUNT = 1           # mettre 2, 3... s'il y a plusieurs LED
LED_BRIGHTNESS = 30     # 0-100 (les WS2812 sont tres lumineuses)
LED_ORDER = "GRB"       # essayer "GRB" ou "BRG" si les couleurs sont fausses (voir test_led.py)

# --- Economie d'energie (batterie) ---------------------------------------------
CPU_MHZ = 160           # 80 / 160 / 240 : moins = moins de consommation (mais animations moins fluides)
FRAME_MS = 40           # 40 = 25 images/s max ; 60 = 16 images/s (plus econome)
WIFI_AUTO_OFF = 120     # le Wi-Fi s'eteint 120 s apres le dernier telephone connecte (0 = jamais)
                        # Appui LONG (1,5 s) sur BOOT : rallume / eteint le Wi-Fi
WIFI_TXPOWER = 8        # puissance d'emission Wi-Fi en dBm (8 suffit pour un telephone a 1-2 m ;
                        # moins = moins de chaleur et de consommation ; 0/None = reglage par defaut)

# --- Reglages par defaut (modifiables ensuite depuis le telephone) ---------
MESSAGE = "Bonjour !"
BRIGHTNESS = 60         # 0-100

# --- Wi-Fi : la barrette cree son propre reseau pour changer le message -----
WEB = True
AP_SSID = "Barrette"
AP_PASSWORD = "barrette123"     # 8 caracteres minimum. CHANGE-LE (dans config_local.py) : ce mot de passe est public !
WIFI_AT_BOOT = True             # True : Wi-Fi + QR au demarrage ; False : seulement apres un appui LONG sur BOOT
WIFI_QR_SECONDS = 25            # le QR reste affiche jusqu'a ce qu'un telephone se connecte (ou ce delai)
WIFI_MAX_CLIENTS = 2            # nombre maximum de telephones connectes en meme temps
WIFI_RANDOM_PASSWORD = False    # True : nouveau mot de passe a CHAQUE activation du Wi-Fi (affiche seulement dans le QR)
SHOW_PASSWORD = False           # True : ecrit aussi le mot de passe en clair sur l'ecran

# --- La playlist : les scenes s'enchainent dans cet ordre ------------------
PLAYLIST = [
    Scroll(),                                   # defile le MESSAGE ci-dessus
    Synthwave(duration=12),                     # soleil retro + grille 80s
    Equalizer(duration=12),                     # egaliseur electro (bpm=128)
    Neon("Hello", color=(255, 40, 170), duration=8),
    Sparkles(duration=10),                      # paillettes
    Glitch(duration=8),                         # texte cyberpunk (utilise MESSAGE)
    Waves(duration=12),                         # vagues pastel
    Dancefloor(duration=12),                    # piste disco
    Fireworks(duration=12),
    Rings(duration=10),                         # ondes neon
    Spiro(duration=16),                         # spirographe
    leds(Hearts(duration=8), "beat", (255, 0, 100), 140),   # exemple : effet LED choisi (voir led.py)
    Neon("Love", color=(0, 220, 255), duration=8),
    Rainbow(duration=6),
    Gallery(seconds=6),                         # diaporama des images envoyees par la page web
    Plasma(duration=8),
    Stars(duration=8),
    Matrix(duration=8),
    # Anim("frames/mon_anim", fps=12, loops=3), # images converties avec tools/gif2raw.py
]


# --- Reglages personnels -------------------------------------------------------
# Cree un fichier config_local.py (copie de config_local.example.py) pour y mettre ton mot de passe Wi-Fi,
# ta LED, etc. Il est ignore par git : tes reglages ne partent jamais sur GitHub.
try:
    from config_local import *
except ImportError:
    pass
