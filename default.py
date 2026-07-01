# -*- coding: utf-8 -*-
"""
kodi-addon-keyboardbattery : interface lancable (menu Programmes).
- sans argument : ecran Accueil (etat + jauge) puis actions
- argument "test" : notification de test avec les reglages courants
"""

import os
import sys

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))

import xbmcgui

import ktools as kt


def _info_text(info):
    def yn(v):
        return {'yes': 'oui', 'no': 'non'}.get((v or '').lower(), v or '-')
    lines = [
        "[B]%s[/B]" % (info.get('name') or 'Clavier'), "",
        "MAC        : %s" % info.get('mac', '-'),
        "Type       : %s" % (info.get('type') or '-'),
        "Connecte   : %s" % yn(info.get('connected')),
        "Appaire    : %s" % yn(info.get('paired')),
        "Bonded     : %s" % yn(info.get('bonded')),
        "Trusted    : %s" % yn(info.get('trusted')),
        "Apparence  : %s" % (info.get('appearance') or '-'),
        "Modalias   : %s" % (info.get('modalias') or '-'),
        "Batterie   : %s" % (("%s%%" % info['battery']) if info.get('battery') else 'non disponible'),
        "", "[B]Services[/B]",
    ]
    for svc in info.get('services', []):
        lines.append("  - %s" % svc)
    return "\n".join(lines)


def show_info():
    mac = kt.get_mac()
    if not mac:
        xbmcgui.Dialog().ok(kt.ADDON_NAME, "Aucune adresse MAC configuree.")
        return
    info = kt.read_info(mac)
    if not info:
        xbmcgui.Dialog().ok(kt.ADDON_NAME,
                            "Impossible de lire le clavier.\n"
                            "Verifiez qu'il est appaire et que bluetoothd tourne.")
        return
    xbmcgui.Dialog().textviewer("Infos clavier", _info_text(info))


def test_notification():
    mac = kt.get_mac()
    pct = None
    if mac:
        pct, _ = kt.read_battery(mac)
    if pct is None:
        pct = 50
    msg = kt.format_msg(kt.s_str('msg_threshold', 'Batterie clavier : {pct}%'), pct)
    kt.notify(msg)


def show_state():
    """Fenetre d'etat colorisee (jauge + % + etat), lue en direct."""
    mac = kt.get_mac()
    if not mac:
        xbmcgui.Dialog().ok(kt.ADDON_NAME, "Aucune adresse MAC configurée.")
        return
    pct, connected, charging = kt.read_state(mac)
    line = kt.status_colored(pct, connected, charging)
    xbmcgui.Dialog().ok("État du clavier", "\n" + line + "\n")


def _headline():
    """Ligne d'etat + jauge pour l'en-tete de l'ecran Accueil."""
    mac = kt.get_mac()
    if not mac:
        return "Aucune adresse MAC configuree", False
    return kt.status_text(mac), True


def home():
    while True:
        head, ok = _headline()
        if not ok and kt.get_mac() == '':
            xbmcgui.Dialog().ok(kt.ADDON_NAME,
                                "Aucune adresse MAC configuree.\nOuvrez les reglages.")
            kt.ADDON.openSettings()
            return
        choice = xbmcgui.Dialog().select(head, [
            "Infos du clavier",
            "Actualiser",
            "Tester la notification",
            "Reglages",
        ])
        if choice == 0:
            show_info()
        elif choice == 1:
            continue
        elif choice == 2:
            test_notification()
        elif choice == 3:
            kt.ADDON.openSettings()
            break
        else:
            break


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_notification()
    elif len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_state()
    else:
        home()
