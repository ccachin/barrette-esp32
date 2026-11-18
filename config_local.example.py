# config_local.example.py - copie ce fichier en "config_local.py" sur la carte (et dans ton dossier de travail).
# Tout ce que tu ecris ici remplace les valeurs de config.py. Ce fichier n'est PAS envoye sur GitHub.
AP_SSID = "MaBarrette"
AP_PASSWORD = "change-moi-12345"      # 8 caracteres minimum
LED_ORDER = "GRB"                      # ordre des couleurs de la LED WS2812 (voir test_led.py)
MESSAGE = "Bonjour !"

# Exemple : remplacer toute la playlist
# PLAYLIST = [
#     Scroll(),
#     Synthwave(duration=12),
#     Neon("Hello", color=(255, 40, 170), duration=8),
# ]
