# -*- coding: utf-8 -*-
"""
kodi-addon-keyboardbattery : service en arriere-plan.
Notifications batterie : demarrage, seuil configurable, seuil critique.
Textes, titre, duree et son personnalisables via les reglages.
"""

import os
import sys

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))

import xbmc

import ktools as kt


def main():
    monitor = xbmc.Monitor()
    kt.log("Service demarre")

    warned_threshold = False
    warned_critical = False
    warned_no_mac = False

    # laisse le temps au Bluetooth de se connecter apres le boot
    if monitor.waitForAbort(45):
        return

    # ---- notification de demarrage ----
    if kt.s_bool('notify_startup', True):
        mac = kt.get_mac()
        if mac:
            pct, connected, charging = kt.read_state(mac)
            if pct is None:
                kt.notify("Clavier deconnecte (batterie non lisible)")
            else:
                warn = pct <= kt.s_int('critical_pct', 15)
                msg = kt.format_msg(kt.s_str('msg_startup', 'Batterie clavier : {pct}%'), pct)
                if charging:
                    msg += " (en charge)"
                elif not connected:
                    msg += " (dernier releve)"
                kt.notify(msg, warning=warn)

    # ---- boucle de surveillance ----
    while not monitor.abortRequested():
        mac = kt.get_mac()
        interval = max(1, kt.s_int('interval', 30))

        if not mac:
            if not warned_no_mac:
                kt.notify("Configurez l'adresse MAC du clavier dans les reglages",
                          warning=True, override_duration=10)
                warned_no_mac = True
        else:
            warned_no_mac = False
            threshold = kt.s_int('threshold_pct', 80)
            critical = kt.s_int('critical_pct', 15)
            pct, connected, charging = kt.read_state(mac)

            if pct is not None:
                kt.log("Batterie %d%% (connecte=%s, charge=%s, seuil=%d, critique=%d)"
                       % (pct, connected, charging, threshold, critical))

                # critique : prioritaire
                if kt.s_bool('notify_critical', True) and pct <= critical:
                    if not warned_critical:
                        msg = kt.format_msg(
                            kt.s_str('msg_critical',
                                     'Batterie clavier presque vide : {pct}% - rechargez'), pct)
                        kt.notify(msg, warning=True)
                        warned_critical = True
                    warned_threshold = True  # ne pas doubler avec le seuil
                # seuil intermediaire
                elif kt.s_bool('notify_threshold', True) and pct <= threshold:
                    warned_critical = False
                    if not warned_threshold:
                        msg = kt.format_msg(
                            kt.s_str('msg_threshold', 'Batterie clavier : {pct}%'), pct)
                        kt.notify(msg)
                        warned_threshold = True
                # au-dessus de tout : reset (ex. apres recharge)
                else:
                    warned_threshold = False
                    warned_critical = False
            else:
                kt.log("Batterie non lisible (clavier deconnecte / replie ?)")

        if monitor.waitForAbort(interval * 60):
            break

    kt.log("Service arrete")


if __name__ == '__main__':
    main()
