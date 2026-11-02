# Dänemark Attraktionen – tägliche Datei

Dieses Repository erzeugt jeden Tag automatisch die Datei `data/attractions.json` mit
Museen, Freizeitparks, Zoos, Burgen und weiteren Sehenswürdigkeiten in Dänemark.
Das WordPress-Plugin „Dänemark Attraktionen-Karte“ ruft nur diese Datei ab und
braucht dafür keine überlasteten öffentlichen Overpass-Server.

Ablauf: GitHub lädt täglich den Dänemark-Auszug von OpenStreetMap
([Geofabrik](https://download.geofabrik.de/europe/denmark.html)), filtert die
Attraktionen heraus und speichert das Ergebnis hier.
Kostenlos, solange das Repository öffentlich ist.

## Einrichtung (einmalig, ca. 15 Minuten)

1. **GitHub-Konto anlegen** (falls noch keins vorhanden): <https://github.com/signup>, kostenlos.
2. **Neues Repository anlegen:** oben rechts auf **+ → New repository**.
   - Name: `dk-attraktionen-daten`
   - Sichtbarkeit: **Public** (nötig, damit das Plugin die Datei ohne Anmeldung abrufen kann)
   - **Keine** Häkchen bei „Add a README“, „.gitignore“ oder „license“ setzen.
   - Auf **Create repository** klicken.
3. **Dateien hochladen:** Auf der nächsten Seite auf den Link **uploading an existing file**
   klicken. Dann den **Inhalt** des entpackten Ordners `dk-attraktionen-daten` (nicht den Ordner selbst)
   in das Browserfenster ziehen: die Ordner `.github` und `scripts` sowie diese Datei.
   Unten auf **Commit changes** klicken.
   - *Mac:* Der Ordner `.github` ist im Finder versteckt. Mit **Cmd + Shift + .** einblenden.
   - *Falls `.github` sich nicht hochladen lässt:* **Add file → Create new file**, im Namensfeld
     `.github/workflows/update.yml` eintippen (die Schrägstriche legen die Ordner an),
     den Inhalt der Datei `update.yml` hineinkopieren und **Commit changes** klicken.
4. **Ersten Lauf starten:** Reiter **Actions** öffnen. Erscheint eine Meldung
   „Workflows aren’t being run“, auf **I understand my workflows, go ahead and enable them**
   klicken. Links **Daten aktualisieren** wählen, rechts **Run workflow → Run workflow**.
   Nach 3 bis 10 Minuten steht ein grünes Häkchen vor dem Lauf.
5. **Adresse der Datei kopieren:** Im Reiter **Code** den Ordner `data` öffnen, auf
   `attractions.json` klicken, oben rechts auf **Raw** klicken und die Adresse aus der
   Adresszeile des Browsers kopieren. Sie sieht so aus:
   `https://raw.githubusercontent.com/DEIN-NAME/dk-attraktionen-daten/main/data/attractions.json`
6. **Im WordPress-Backend:** Menü **DK Attraktionen**, Feld **Datenquelle**: Adresse einfügen,
   **Speichern**, danach **Jetzt aktualisieren**.

Ab jetzt aktualisiert sich alles selbst: GitHub erneuert die Datei täglich, das Plugin holt sie
jede Nacht gegen 3:30 Uhr ab.

## Wenn etwas nicht klappt

- **Roter Haken bei einem Lauf (Reiter Actions):** Lauf anklicken, den rot markierten Schritt
  aufklappen und den Text kopieren. GitHub schickt bei Fehlern außerdem eine E-Mail.
- **Das Plugin meldet „HTTP 404“:** Die Adresse stimmt nicht, oder der erste Lauf ist noch nicht
  fertig. Das Repository muss öffentlich sein.
- **Seltener aktualisieren:** In `.github/workflows/update.yml` die Zeile `cron: "30 1 * * *"`
  ändern, zum Beispiel `"30 1 * * 1"` für einmal pro Woche (montags).

## Lizenz und Quellenangabe

Die Daten stammen aus OpenStreetMap, © OpenStreetMap-Mitwirkende, verfügbar unter der
[Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). Auf der Karte
wird die Namensnennung angezeigt. Der Auszug stammt von Geofabrik.
