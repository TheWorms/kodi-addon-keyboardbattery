[Français](README.md) · **English**

# Keyboard Battery Monitor

<!-- version:auto -->
**Version : 1.5.0**
<!-- /version:auto -->

Kodi addon (service + UI) that shows the **battery** and **information** of a
Bluetooth keyboard through BlueZ, with a **colored status screen** and
**customizable notifications** (startup, warning threshold, critical alert).

Built for **CoreELEC / LibreELEC** and other Linux Kodi setups (tested on Kodi 21
"Omega", ODROID-N2+). Developed with a *Microsoft Universal Foldable Keyboard*.

- **Repository**: `github.com/TheWorms/kodi-addon-keyboardbattery`
- **Kodi id**: `service.keyboardbattery`
- **Display name**: Keyboard Battery Monitor · **License**: MIT

---

## Home screen (addon launched)

```
▮▮▮▮▮▮▮▮▮▮▯▯▯▯  72% · On battery       ← colored gauge + state, read live
Keyboard info                         → name, MAC, pairing, services, battery
Refresh                               → re-reads the battery
Test notification                     → sample notification with your settings
Settings                              → opens the settings page
```

The gauge is **colored** by level: green (> 30%), amber (15–30%), red (≤ 15%),
and **cyan with ⚡** while the keyboard is charging.

> ⚠️ This screen appears when you **launch** the addon (Add-ons → Program add-ons
> → Keyboard Battery Monitor → OK). From the settings, the **Home → Show keyboard
> state** button opens the same colored view.

## Features

- **Home screen**: segmented colored battery gauge + state
  (*On battery* / *Charging* / *Disconnected*).
- **Keyboard info**: MAC, type, pairing, GATT services, battery.
- Configurable **notifications** (text with `{pct}` token, title, duration, sound):
  - at Kodi **startup**;
  - at a configurable **warning threshold** (80% by default);
  - a **critical** alert just before depletion (15% by default).
- Periodic checks stay **silent** while the battery is above the thresholds; each
  alert fires **once** per crossing (re-armed after charging).

## Requirements

- A Bluetooth keyboard that **exposes the GATT Battery Service**. To check, over
  SSH on the box (keyboard connected):
  ```bash
  bluetoothctl info <MAC>
  ```
  Look for a `Battery Percentage` line. If missing, the keyboard does not report
  its charge and no addon can display it.
- `bluetoothctl` available in `PATH` (standard on CoreELEC/LibreELEC).

## Find the MAC address

```bash
bluetoothctl devices        # lists paired devices (MAC + name)
```

## Install

### Via the TheWorms repository (recommended, auto-updates)

1. Install the repository:
   `https://raw.githubusercontent.com/TheWorms/kodi-repo/main/zips/repository.theworms/repository.theworms.zip`
2. Add-ons → **Install from repository** → *TheWorms Repository* →
   *Program add-ons* / *Services* → **Keyboard Battery Monitor** → Install.

### Manual (zip)

1. Get `service.keyboardbattery-x.y.z.zip`.
2. System → Add-ons → enable **Unknown sources**.
3. Add-ons → **Install from zip file**.

After installing, open the settings and enter the keyboard **MAC address**.

## Settings

| Tab | Setting | Default | Description |
|---|---|---|---|
| Home | Show keyboard state | — | Opens the colored view (gauge + %) |
| Keyboard | MAC address | — | Keyboard MAC (`bluetoothctl devices`) |
| Keyboard | Check interval | 30 min | Polling frequency |
| Notifications | Notify at startup | on | Battery when Kodi starts |
| Notifications | Warning threshold | 80% | Notify below this |
| Notifications | Critical threshold | 15% | Urgent alert before depletion |
| Notifications | Messages | — | Customizable texts (`{pct}` token) |
| Appearance | Title / Duration / Sound | — | Notification styling + *Test* button |

## "Charging" detection (heuristic)

BlueZ (`org.bluez.Battery1`) only exposes the **percentage**, not a charge state.
The addon infers "charging" when the percentage **rises** between two readings.
This is **indicative**: up to one interval of latency, and rarely observable if
the keyboard is folded (hence disconnected) while charging.

## Troubleshooting

- **`bluetoothctl failed` in the log** → the binary is not in Kodi's `PATH`, or
  `bluetoothd` is not running.
- **Battery "unavailable" / "Disconnected"** → keyboard folded: unfold it and
  reopen the view.
- **A changed title/message does not apply** → confirm the settings (OK) before
  testing; the *Test* button reads the **saved** values.

## License

MIT — see `LICENSE.txt`.
