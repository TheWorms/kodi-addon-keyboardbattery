**Français** · [English](readme.en.md)

# Keyboard Battery Monitor

Addon Kodi (service + interface) qui affiche la **batterie** et les **informations**
d'un clavier Bluetooth via BlueZ, avec un **écran d'état en couleur** et des
**notifications personnalisables** (démarrage, seuil, alerte critique).

Conçu pour **CoreELEC / LibreELEC** et les autres Kodi sous Linux (testé Kodi 21
« Omega », ODROID-N2+). Développé avec un *Microsoft Universal Foldable Keyboard*.

- **Dépôt** : `github.com/TheWorms/kodi-addon-keyboardbattery`
- **Identifiant Kodi** : `service.keyboardbattery`
- **Nom affiché** : Keyboard Battery Monitor · **Licence** : MIT

---

## L'écran d'accueil (addon lancé)

```
▮▮▮▮▮▮▮▮▮▮▯▯▯▯  72% · Sur batterie     ← jauge colorée + état, lue en direct
Infos du clavier                      → nom, MAC, appairage, services, batterie
Actualiser                            → relit la batterie
Tester la notification                → notif d'exemple avec tes réglages
Réglages                              → ouvre la page de réglages
```

La jauge est **colorée** selon le niveau : vert (> 30 %), ambre (15–30 %), rouge
(≤ 15 %), et **cyan avec ⚡** quand le clavier se recharge.

> ⚠️ Cet écran apparaît quand tu **lances** l'addon (Add-ons → Extensions
> programmes → Keyboard Battery Monitor → OK). Depuis les réglages, l'onglet
> **Accueil → Afficher l'état du clavier** ouvre la même vue colorée.

## Fonctions

- **Écran d'accueil** : jauge de batterie à segments en couleur + état
  (*Sur batterie* / *En charge* / *Déconnecté*).
- **Infos clavier** : MAC, type, appairage, services GATT, batterie.
- **Notifications** configurables (texte avec jeton `{pct}`, titre, durée, son) :
  - au **démarrage** de Kodi ;
  - à un **seuil d'alerte** paramétrable (80 % par défaut) ;
  - une alerte **critique** juste avant l'épuisement (15 % par défaut).
- Les vérifications périodiques sont **silencieuses** tant que la batterie reste
  au-dessus des seuils ; chaque alerte n'est émise **qu'une fois** par
  franchissement (réarmée après recharge).

## Prérequis

- Un clavier Bluetooth qui **expose le Battery Service GATT**. Pour vérifier, en
  SSH sur la box (clavier connecté) :
  ```bash
  bluetoothctl info <MAC>
  ```
  Cherche une ligne `Battery Percentage`. Si elle est absente, le clavier ne
  remonte pas sa charge et aucun addon ne pourra l'afficher.
- `bluetoothctl` accessible dans le `PATH` (standard sur CoreELEC/LibreELEC).

## Trouver l'adresse MAC

```bash
bluetoothctl devices        # liste les appareils appairés (MAC + nom)
```

## Installer

### Via le dépôt TheWorms (recommandé, mises à jour automatiques)

1. Installe le dépôt :
   `https://raw.githubusercontent.com/TheWorms/kodi-repo/main/zips/repository.theworms/repository.theworms.zip`
2. Add-ons → **Installer depuis un dépôt** → *TheWorms Repository* →
   *Extensions programmes* / *Services* → **Keyboard Battery Monitor** → Installer.

### Manuelle (zip)

1. Récupère `service.keyboardbattery-x.y.z.zip`.
2. Système → Add-ons → active **Sources inconnues**.
3. Add-ons → **Installer depuis un fichier zip**.

Après installation, ouvre les réglages et renseigne l'**adresse MAC** du clavier.

## Réglages

| Onglet | Réglage | Défaut | Description |
|---|---|---|---|
| Accueil | Afficher l'état du clavier | — | Ouvre la vue colorée (jauge + %) |
| Clavier | Adresse MAC | — | MAC du clavier (`bluetoothctl devices`) |
| Clavier | Intervalle de vérification | 30 min | Fréquence de relevé |
| Notifications | Notifier au démarrage | activé | Batterie au lancement de Kodi |
| Notifications | Seuil d'alerte | 80 % | Notification sous ce seuil |
| Notifications | Seuil critique | 15 % | Alerte urgente avant épuisement |
| Notifications | Messages | — | Textes personnalisables (jeton `{pct}`) |
| Apparence | Titre / Durée / Son | — | Habillage des notifications + bouton *Tester* |

## Détection « en charge » (heuristique)

BlueZ (`org.bluez.Battery1`) n'expose que le **pourcentage**, pas d'état de charge.
L'addon déduit « en charge » quand le pourcentage **augmente** entre deux relevés.
C'est **indicatif** : latence d'un intervalle, et rarement observable si le clavier
est replié (donc déconnecté) pendant la charge.

## Dépannage

- **`bluetoothctl a échoué` dans le journal** → le binaire n'est pas dans le
  `PATH` du process Kodi, ou `bluetoothd` ne tourne pas.
- **Batterie « non disponible » / « Déconnecté »** → clavier replié : déplie-le
  puis relance la vue.
- **Un titre/message modifié ne s'applique pas** → valide les réglages (OK) avant
  de tester ; le bouton *Tester* lit les valeurs **enregistrées**.

## Licence

MIT — voir `LICENSE.txt`.
