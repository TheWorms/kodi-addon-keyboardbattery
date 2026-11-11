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
        return {'yes': kt.L(30209, 'oui'), 'no': kt.L(30210, 'non')}.get((v or '').lower(), v or '-')
    def row(label, value):
        return "%s : %s" % (label.ljust(10), value)

    lines = [
        "[B]%s[/B]" % (info.get('name') or kt.L(30211, 'Clavier')), "",
        row("MAC", info.get('mac', '-')),
        row(kt.L(30212, 'Type'), info.get('type') or '-'),
        row(kt.L(30213, 'Connecté'), yn(info.get('connected'))),
        row(kt.L(30214, 'Appairé'), yn(info.get('paired'))),
        row("Bonded", yn(info.get('bonded'))),
        row("Trusted", yn(info.get('trusted'))),
        row(kt.L(30215, 'Apparence'), info.get('appearance') or '-'),
        row("Modalias", info.get('modalias') or '-'),
        row(kt.L(30216, 'Batterie'),
            ("%s%%" % info['battery']) if info.get('battery') else kt.L(30217, 'non disponible')),
        "", "[B]%s[/B]" % kt.L(30218, 'Services'),
    ]
    for svc in info.get('services', []):
        lines.append("  - %s" % svc)
    return "\n".join(lines)


def show_info():
    mac = kt.get_mac()
    if not mac:
        xbmcgui.Dialog().ok(kt.ADDON_NAME, kt.L(30208, 'Aucune adresse MAC configurée'))
        return
    info = kt.read_info(mac)
    if not info:
        xbmcgui.Dialog().ok(kt.ADDON_NAME, kt.L(
            30219, "Impossible de lire le clavier.[CR]"
                   "Vérifiez qu'il est appairé et que bluetoothd tourne."))
        return
    xbmcgui.Dialog().textviewer(kt.L(30220, 'Infos du clavier'), _info_text(info))


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
        xbmcgui.Dialog().ok(kt.ADDON_NAME, kt.L(30208, 'Aucune adresse MAC configurée'))
        return
    pct, connected, charging = kt.read_state(mac)
    line = kt.status_colored(pct, connected, charging)
    xbmcgui.Dialog().ok(kt.L(30221, 'État du clavier'), "\n" + line + "\n")


def _headline():
    """Ligne d'etat + jauge pour l'en-tete de l'ecran Accueil."""
    mac = kt.get_mac()
    if not mac:
        return kt.L(30208, 'Aucune adresse MAC configurée'), False
    return kt.status_text(mac), True


def home():
    while True:
        head, ok = _headline()
        if not ok and kt.get_mac() == '':
            xbmcgui.Dialog().ok(kt.ADDON_NAME, kt.L(
                30222, "Aucune adresse MAC configurée.[CR]Ouvrez les réglages."))
            kt.ADDON.openSettings()
            return
        choice = xbmcgui.Dialog().select(head, [
            kt.L(30220, 'Infos du clavier'),
            kt.L(30224, 'Actualiser'),
            kt.L(30225, 'Tester la notification'),
            kt.L(30226, 'Réglages'),
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
