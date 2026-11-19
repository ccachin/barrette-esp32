# test_batterie.py - affiche la tension de la batterie (Thonny : ouvre ce fichier et clique sur Run).
# Compare avec un multimetre sur les pastilles BAT / G, puis ajuste BAT_CAL dans config_local.py.
import time
import power

print("GPIO1, pont 200k/100k : VBAT = V_ADC x 3")
for _ in range(20):
    v = power.voltage()
    print("%.3f V  ->  %d %%" % (v, power.percent(v)))
    time.sleep(1)
