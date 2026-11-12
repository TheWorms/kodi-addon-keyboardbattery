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
def _handle_connected(monitor):
    """Clavier vient de se (re)connecter : lire la batterie (avec retries,
    le temps que les services GATT soient resolus) puis notifier."""
    if not kt.s_bool('notify_connect', True):
        return
    if time.time() - _last_notify['ts'] < _NOTIFY_DEBOUNCE:
        return  # la notif de demarrage vient de partir, pas de doublon
    mac = kt.get_mac()
    pct = None
    for _ in range(5):                      # jusqu'a ~10 s
        # Attente abortable : time.sleep bloquait l'extinction de Kodi
        # jusqu'a 10 s si elle survenait pendant les retries.
        if monitor.waitForAbort(2):
            return
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


_DBUS_RESTART_DELAY = 30  # secondes avant de relancer dbus-monitor


def _dbus_monitor_loop(monitor, proc_holder):
    """Garde l'ecoute D-Bus en vie : si dbus-monitor s'arrete (redemarrage
    de BlueZ ou du bus systeme), il est relance apres une pause. Avant, les
    notifications de connexion etaient perdues jusqu'au redemarrage de Kodi."""
    short_runs = 0
    while not monitor.abortRequested() and not proc_holder.get('stopped'):
        started = time.time()
        if not _dbus_monitor_once(monitor, proc_holder):
            return
        # dbus-monitor qui retombe aussitot a chaque essai (bus systeme
        # inaccessible) : on n'insiste pas indefiniment.
        short_runs = short_runs + 1 if time.time() - started < 10 else 0
        if short_runs >= 5:
            kt.log("dbus-monitor s'arrete aussitot lance : notification de "
                   "connexion desactivee", xbmc.LOGWARNING)
            return
        if proc_holder.get('stopped') or monitor.waitForAbort(_DBUS_RESTART_DELAY):
            return
        kt.log("dbus-monitor arrete : relance de l'ecoute Bluetooth")


def _dbus_monitor_once(monitor, proc_holder):
    """Lit (bloquant) les signaux PropertiesChanged de org.bluez.Device1.
    Detecte 'Connected' -> boolean true pour la MAC configuree.
    Retourne True si l'ecoute s'est arretee et peut etre relancee, False si
    dbus-monitor est indisponible ou si l'arret est demande."""
    cmd = ['dbus-monitor', '--system',
           "type='signal',interface='org.freedesktop.DBus.Properties',"
           "member='PropertiesChanged',arg0='org.bluez.Device1'"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except Exception as e:
        kt.log("dbus-monitor indisponible (%s) : notification de connexion "
               "desactivee" % e, xbmc.LOGWARNING)
        return False
    proc_holder['proc'] = proc
    # Abort demande AVANT ce Popen : _cleanup est deja passe (abort pendant
    # les 45 premieres secondes de main) et personne ne terminerait ce
    # dbus-monitor -> il survivait en processus orphelin a l'arret de Kodi.
    if proc_holder.get('stopped'):
        proc.terminate()
        return False
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
                    _handle_connected(monitor)
    except Exception as e:
        kt.log("Moniteur D-Bus arrete: %s" % e, xbmc.LOGWARNING)
    finally:
        # Terminer dbus-monitor depuis CE thread, quoi qu'il arrive : si
        # main() est deja sorti, _cleanup ne nous reverra jamais.
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)  # pas de processus zombie entre deux relances
        except Exception:
            pass
    return not monitor.abortRequested() and not proc_holder.get('stopped')


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
    proc_holder = {'proc': None, 'stopped': False}
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
                kt.notify(kt.L(30200, 'Clavier déconnecté (batterie non lisible)'))
            elif kt.s_bool('notify_critical', True) and pct <= critical:
                # Une seule notification : l'alerte critique remplace le
                # message de demarrage (elle suivait aussitot, en double).
                _notify_battery(kt.format_msg(
                    kt.s_str('msg_critical',
                             'Batterie clavier presque vide : {pct}% - rechargez'),
                    pct), warning=True)
                state['crit'] = True
                state['thr'] = True
            else:
                msg = kt.format_msg(
                    kt.s_str('msg_startup', 'Batterie clavier : {pct}%'), pct)
                if charging:
                    msg += ' ' + kt.L(30201, '(en charge)')
                elif not connected:
                    msg += ' ' + kt.L(30202, '(dernier relevé)')
                _notify_battery(msg, warning=(pct <= critical))
                # Le premier controle de seuil, juste apres, redisait la
                # meme chose : il attend maintenant la prochaine remontee
                # au-dessus du seuil.
                if pct <= kt.s_int('threshold_pct', 80):
                    state['thr'] = True

    # ---- boucle de controle batterie (intervalle configure) ----
    while not monitor.abortRequested():
        mac = kt.get_mac()
        interval = max(1, kt.s_int('interval', 30))

        if not mac:
            if not warned_no_mac:
                kt.notify(kt.L(30203, "Configurez l'adresse MAC du clavier dans les réglages"),
                          warning=True, override_duration=10)
                warned_no_mac = True
        else:
            warned_no_mac = False
            try:
                _battery_check(state)
            except Exception as e:
                # Un releve qui echoue ne doit pas arreter le service
                # jusqu'au prochain redemarrage de Kodi.
                kt.log("Controle batterie en erreur : %s" % e, xbmc.LOGERROR)

        if monitor.waitForAbort(interval * 60):
            break

    _cleanup(proc_holder)
    kt.log("Service arrete")


def _cleanup(proc_holder):
    # 'stopped' AVANT tout : si le thread lance son Popen apres ce cleanup
    # (abort pendant les 45 premieres secondes de main), il saura qu'il
    # doit terminer dbus-monitor lui-meme.
    proc_holder['stopped'] = True
    proc = proc_holder.get('proc')
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == '__main__':
    main()
