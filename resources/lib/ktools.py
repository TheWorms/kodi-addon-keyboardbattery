# -*- coding: utf-8 -*-
"""
kodi-addon-keyboardbattery : fonctions partagees (service + UI).
Interroge BlueZ via `bluetoothctl info <MAC>`, parse la sortie, persiste
l'etat pour une detection heuristique de la charge, et rend une jauge texte.
"""

import json
import os
import re
import subprocess
import time

import xbmc
import xbmcaddon
import xbmcgui

try:
    import xbmcvfs
    def _translate(p):
        return xbmcvfs.translatePath(p)
except Exception:
    def _translate(p):
        return p

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')


def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_NAME, msg), level)


# ---------------------------------------------------------------- reglages ---
# Lecture sur une instance fraiche : garantit des valeurs a jour cote service
# (un objet Addon() long-vivant peut mettre en cache les reglages).
def s_str(key, default=''):
    try:
        v = xbmcaddon.Addon().getSettingString(key)
        return v if v else default
    except Exception:
        return default


def s_int(key, default=0):
    try:
        return int(xbmcaddon.Addon().getSettingInt(key))
    except Exception:
        return default


def s_bool(key, default=False):
    try:
        return bool(xbmcaddon.Addon().getSettingBool(key))
    except Exception:
        return default


def get_mac():
    return (s_str('mac') or '').strip()


# ---------------------------------------------------------- persistance etat ---
def _state_path():
    prof = _translate(ADDON.getAddonInfo('profile'))
    try:
        if not os.path.isdir(prof):
            os.makedirs(prof)
    except Exception:
        pass
    return os.path.join(prof, 'state.json')


def load_state():
    try:
        with open(_state_path(), 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(d):
    try:
        with open(_state_path(), 'w') as f:
            json.dump(d, f)
    except Exception as e:
        log("save_state: %s" % e, xbmc.LOGWARNING)


# ------------------------------------------------------------- notifications ---
def format_msg(template, pct):
    return (template or '').replace('{pct}', str(pct))


def notify(message, warning=False, override_duration=None):
    title = s_str('notif_title') or ADDON_NAME
    secs = override_duration if override_duration is not None else s_int('notif_duration', 8)
    duration = max(1, secs) * 1000
    sound = s_bool('notif_sound', True)
    icon = xbmcgui.NOTIFICATION_WARNING if warning else (ADDON_ICON or xbmcgui.NOTIFICATION_INFO)
    xbmcgui.Dialog().notification(title, message, icon, duration, sound)


# ---------------------------------------------------------------- bluetooth ---
def _run_info(mac):
    try:
        out = subprocess.check_output(
            ['bluetoothctl', 'info', mac],
            stderr=subprocess.STDOUT, timeout=10)
        return out.decode('utf-8', 'replace')
    except Exception as e:
        log("bluetoothctl a echoue: %s" % e, xbmc.LOGWARNING)
        return ''


def _grep(pattern, text, default=None):
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default


def read_battery(mac):
    """(pourcentage:int|None, connecte:bool). None => info indisponible."""
    text = _run_info(mac)
    if not text:
        return None, False
    connected = re.search(r'Connected:\s*yes', text) is not None
    pct = _grep(r'Battery Percentage:\s*0x[0-9a-fA-F]+\s*\((\d+)\)', text)
    return (int(pct) if pct is not None else None), connected


def read_state(mac):
    """
    (pct:int|None, connecte:bool, en_charge:bool).
    'en_charge' est HEURISTIQUE : vrai si le pourcentage a augmente depuis le
    dernier releve (BlueZ n'expose pas d'etat de charge). Persiste l'historique.
    """
    pct, connected = read_battery(mac)
    st = load_state()
    last = st.get('pct')
    charging = bool(st.get('charging', False))

    if pct is not None and connected and isinstance(last, int):
        if pct > last:
            charging = True
        elif pct < last:
            charging = False
        # egal -> on conserve l'etat precedent
    elif not connected or pct is None:
        charging = False

    save_state({'pct': pct, 'connected': connected,
                'charging': charging, 'ts': time.time()})
    return pct, connected, charging


# UUID connus -> libelle lisible
_KNOWN_UUIDS = {
    '1800': 'Generic Access', '1801': 'Generic Attribute',
    '180a': 'Device Information', '180f': 'Battery Service',
    '1812': 'Human Interface Device (HID)', '1813': 'Scan Parameters',
}


def read_info(mac):
    text = _run_info(mac)
    if not text:
        return {}
    services = []
    for line in text.splitlines():
        m = re.search(r'UUID:\s*(.+?)\s*\(([0-9a-fA-F]{8})-', line)
        if m:
            short4 = m.group(2)[4:8].lower()
            services.append(_KNOWN_UUIDS.get(short4, m.group(1).strip()))
    return {
        'name': _grep(r'\n\s*Name:\s*(.+)', text) or _grep(r'\n\s*Alias:\s*(.+)', text),
        'mac': mac,
        'type': _grep(r'Device\s+\S+\s+\((\w+)\)', text),
        'appearance': _grep(r'Appearance:\s*(.+)', text),
        'paired': _grep(r'Paired:\s*(\w+)', text),
        'bonded': _grep(r'Bonded:\s*(\w+)', text),
        'trusted': _grep(r'Trusted:\s*(\w+)', text),
        'connected': _grep(r'Connected:\s*(\w+)', text),
        'modalias': _grep(r'Modalias:\s*(.+)', text),
        'battery': _grep(r'Battery Percentage:\s*0x[0-9a-fA-F]+\s*\((\d+)\)', text),
        'services': services,
    }


# ------------------------------------------------------------------- jauge ---
def gauge_bar(pct, segments=14):
    """Barre a segments : '▮' plein, '▯' vide. pct None -> tout vide."""
    if pct is None:
        return '▯' * segments
    filled = int(round(pct / 100.0 * segments))
    filled = max(0, min(segments, filled))
    return '▮' * filled + '▯' * (segments - filled)


# ------------------------------------------------------ ligne d'etat couleur ---
# Couleurs Kodi bbcode : [COLOR=AARRGGBB]...[/COLOR]
C_GREEN = 'FF7BC86C'
C_AMBER = 'FFE6B34D'
C_RED = 'FFE5654D'
C_CYAN = 'FF37C0D4'
C_DIM = '66FFFFFF'


def _level_color(pct):
    if pct <= 15:
        return C_RED
    if pct <= 30:
        return C_AMBER
    return C_GREEN


def _col(txt, color):
    return '[COLOR=%s]%s[/COLOR]' % (color, txt)


def gauge_colored(pct, charging=False, segments=14):
    """Jauge a segments colorisee (bbcode Kodi)."""
    if pct is None:
        return _col('▯' * segments, C_DIM)
    filled = max(0, min(segments, int(round(pct / 100.0 * segments))))
    fill_c = C_CYAN if charging else _level_color(pct)
    return _col('▮' * filled, fill_c) + _col('▯' * (segments - filled), C_DIM)


def status_colored(pct, connected, charging):
    """Ligne d'etat complete colorisee (jauge + % + etat)."""
    if pct is None:
        return gauge_colored(None) + '  ' + _col('Déconnecté', C_DIM)
    bar = gauge_colored(pct, charging)
    pct_c = C_CYAN if charging else _level_color(pct)
    pct_txt = _col('%d%%' % pct, pct_c)
    if not connected:
        etat = _col('Sur batterie (dernier relevé)', C_DIM)
    elif charging:
        etat = _col('⚡ En charge', C_CYAN)
    else:
        etat = 'Sur batterie'
    return '%s  %s · %s' % (bar, pct_txt, etat)


def status_text(mac):
    """Lit la batterie et renvoie la ligne d'etat colorisee prete a afficher."""
    if not mac:
        return 'Aucune adresse MAC configurée'
    pct, connected, charging = read_state(mac)
    return status_colored(pct, connected, charging)
