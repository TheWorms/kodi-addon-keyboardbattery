# -*- coding: utf-8 -*-
"""
kodi-addon-keyboardbattery : service en arriere-plan.
- notification a la (re)connexion du clavier, via evenements D-Bus BlueZ
  (dbus-monitor bloquant : zero polling, zero CPU au repos) ;
- controles de seuil/critique selon l'intervalle configure ;
- notification de demarrage.
Textes, titre, duree et son personnalisables via les reglages.
"""

import os
import re
import subprocess
import sys
import threading
import time

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))

import xbmc

import ktools as kt

# anti-doublon demarrage/connexion : timestamp de la derniere notif batterie
_last_notify = {'ts': 0.0}
_NOTIFY_DEBOUNCE = 10  # secondes


def _notify_battery(msg, warning=False):
    _last_notify['ts'] = time.time()
    kt.notify(msg, warning=warning)


def _mac_to_path_frag(mac):
    return 'dev_' + mac.replace(':', '_').upper()


# ------------------------------------------------------------- connexion ---
def _handle_connected():
    """Clavier vient de se (re)connecter : lire la batterie (avec retries,
    le temps que les services GATT soient resolus) puis notifier."""
    if not kt.s_bool('notify_connect', True):
        return
    if time.time() - _last_notify['ts'] < _NOTIFY_DEBOUNCE:
        return  # la notif de demarrage vient de partir, pas de doublon
    mac = kt.get_mac()
    pct = None
    for _ in range(5):                      # jusqu'a ~10 s
        time.sleep(2)
        pct, connected = kt.read_battery(mac)
        if pct is not None:
            break
        if not connected:                   # deja reparti
            return
    if pct is None:
        kt.log("Connexion detectee mais batterie non lisible")
        return
    critical = kt.s_int('critical_pct', 15)
    msg = kt.format_msg(
        kt.s_str('msg_connect', 'Clavier connecté — batterie : {pct}%'), pct)
    _notify_battery(msg, warning=(pct <= critical))
    kt.log("Notification de connexion emise (%d%%)" % pct)


def _dbus_monitor_loop(monitor, proc_holder):
    """Lit (bloquant) les signaux PropertiesChanged de org.bluez.Device1.
    Detecte 'Connected' -> boolean true pour la MAC configuree."""
    cmd = ['dbus-monitor', '--system',
           "type='signal',interface='org.freedesktop.DBus.Properties',"
           "member='PropertiesChanged',arg0='org.bluez.Device1'"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except Exception as e:
        kt.log("dbus-monitor indisponible (%s) : notification de connexion "
               "desactivee" % e, xbmc.LOGWARNING)
        return
    proc_holder['proc'] = proc
    kt.log("Ecoute des evenements de connexion Bluetooth (D-Bus)")

    cur_path = ''
    pending = False
    try:
        for raw in proc.stdout:
            if monitor.abortRequested():
                break
            line = raw.decode('utf-8', 'replace')
            if 'member=PropertiesChanged' in line:
                m = re.search(r'path=(\S+?);', line)
                cur_path = m.group(1) if m else ''
                pending = False
            elif '"Connected"' in line:
                pending = True
            elif pending and 'boolean' in line:
                is_true = 'true' in line
                pending = False
                if is_true and _mac_to_path_frag(kt.get_mac()) in cur_path:
                    _handle_connected()
    except Exception as e:
        kt.log("Moniteur D-Bus arrete: %s" % e, xbmc.LOGWARNING)


# ---------------------------------------------------------------- batterie ---
def _battery_check(state):
    mac = kt.get_mac()
    threshold = kt.s_int('threshold_pct', 80)
    critical = kt.s_int('critical_pct', 15)
    pct, connected, charging = kt.read_state(mac)
    if pct is None:
        kt.log("Batterie non lisible (deconnecte / replie ?)")
        return
    kt.log("Batterie %d%% (connecte=%s, charge=%s, seuil=%d, critique=%d)"
           % (pct, connected, charging, threshold, critical))

    if kt.s_bool('notify_critical', True) and pct <= critical:
        if not state['crit']:
            _notify_battery(kt.format_msg(
                kt.s_str('msg_critical',
                         'Batterie clavier presque vide : {pct}% - rechargez'),
                pct), warning=True)
            state['crit'] = True
        state['thr'] = True
    elif kt.s_bool('notify_threshold', True) and pct <= threshold:
        state['crit'] = False
        if not state['thr']:
            _notify_battery(kt.format_msg(
                kt.s_str('msg_threshold', 'Batterie clavier : {pct}%'), pct))
            state['thr'] = True
    else:
        state['thr'] = False
        state['crit'] = False


def main():
    monitor = xbmc.Monitor()
    kt.log("Service demarre")

    # moniteur de connexion : thread bloquant sur dbus-monitor (0 polling)
    proc_holder = {'proc': None}
    t = threading.Thread(target=_dbus_monitor_loop,
                         args=(monitor, proc_holder), daemon=True)
    t.start()

    if monitor.waitForAbort(45):
        _cleanup(proc_holder)
        return

    warned_no_mac = False
    state = {'thr': False, 'crit': False}

    # ---- notification de demarrage ----
    if kt.s_bool('notify_startup', True):
        mac = kt.get_mac()
        if mac:
            pct, connected, charging = kt.read_state(mac)
            critical = kt.s_int('critical_pct', 15)
            if pct is None:
                kt.notify("Clavier deconnecte (batterie non lisible)")
            else:
                msg = kt.format_msg(
                    kt.s_str('msg_startup', 'Batterie clavier : {pct}%'), pct)
                if charging:
                    msg += " (en charge)"
                elif not connected:
                    msg += " (dernier releve)"
                _notify_battery(msg, warning=(pct <= critical))

    # ---- boucle de controle batterie (intervalle configure) ----
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
            _battery_check(state)

        if monitor.waitForAbort(interval * 60):
            break

    _cleanup(proc_holder)
    kt.log("Service arrete")


def _cleanup(proc_holder):
    proc = proc_holder.get('proc')
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == '__main__':
    main()
