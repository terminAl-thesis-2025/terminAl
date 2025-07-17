# terminAl

Ein KI-basiertes CLI-Assistenzsystem für Linux-Systeme, das die Einstiegshürden für Absolvierende wirtschaftsnaher Studiengänge reduziert.

## Über das Projekt

terminAl ist ein Proof of Concept (PoC), der im Rahmen einer Bachelorarbeit entwickelt wurde. Das System ermöglicht es Benutzenden, natürlichsprachliche Anfragen zu stellen und diese in ausführbare Linux-Befehle oder PostgreSQL-Abfragen umzuwandeln. 

⚠️ **Hinweis:** Dies ist ein Proof of Concept und keine produktionsreife Anwendung.

⚠️ **Hinweis:** Dieses System führt Befehle auf dem System aus. Alle vorgeschlagenen Befehle sorgfältig prüfen, bevor diese genehmigt werden.

## Systemanforderungen

- **Betriebssystem:** Ubuntu/Debian-basierte Linux-Distribution
- **Python:** Version 3.8 oder höher
- **Hardware:** 
  - CUDA-kompatible GPU empfohlen (für bessere Performance)

## Dependencies

Das System benötigt folgende externe Komponenten:

- **Ollama:** Lokaler LLM-Server für die KI-Inferenz
- **PostgreSQL:** Datenbankserver für SQL-Funktionalität
- **Python-Dependencies:** Siehe `requirements.txt`

## Installation

1. **Repository klonen:**
   ```bash
   git clone <repository-url>
   cd terminAl
   ```

2. **Python-Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfiguration:**
   - `example.env` zu `.env` kopieren und die Werte an die Umgebung anpassen
   - `settings/settings.json` für erweiterte Konfiguration bearbeiten

4. **Externe Services einrichten:**
   - Ollama installieren und konfigurieren
   - PostgreSQL installieren und konfigurieren
   - Kompatibles LLM-Modell in Ollama laden

## Konfiguration

### Umgebungsvariablen (.env)

Die `example.env` Datei enthält alle erforderlichen Umgebungsvariablen. Diese zu `.env` kopieren und die Werte entsprechend anpassen:

```bash
cp example.env .env
# Anschließend die .env Datei bearbeiten
```

### Einstellungen (settings.json)

Die Hauptkonfiguration erfolgt über `settings/settings.json`. Hier können folgende Aspekte konfiguriert werden:

- **Ollama-Einstellungen:** Modell, URL, verfügbare Modelle
- **ChromaDB-Einstellungen:** Vektordatenbank-Konfiguration
- **PostgreSQL-Einstellungen:** Datenbankverbindungen
- **System-Mapping:** Verzeichnisstruktur-Erfassung

## Verwendung

### Starten der Anwendung

```bash
python main.py
```

### Grundlegende Bedienung

- **Normale Anfragen:** Fragen in natürlicher Sprache eingeben
- **Kontextsuche:** `<Begriff>` für gezielte Suche in der Vektordatenbank verwenden
- **Systembefehle:** `\befehl` für interne Funktionen nutzen

### Wichtige Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `\help` | Zeigt alle verfügbaren Befehle |
| `\info` | Systeminformationen anzeigen |
| `\update now` | Manuelle Aktualisierung der Systemstruktur |
| `\psql login <db>` | PostgreSQL-Datenbankverbindung |
| `\search <Begriff>` | Volltextsuche in der Datenbank |
| `\model list` | Verfügbare LLM-Modelle anzeigen |
| `\clear` | Terminal bereinigen |
| `\exit` | Anwendung beenden |

### Beispiel-Workflows

**Linux-Dateiverwaltung:**
```
terminAl --> : Erstelle einen Ordner namens "projekt" im Home-Verzeichnis
terminAl --> : Zeige alle .txt Dateien im aktuellen Verzeichnis
terminAl --> : Ändere die Berechtigung der Datei <config.txt> zu 644
```

**PostgreSQL-Abfragen:**
```
terminAl --> : \psql login testdb
terminAl (psql: testdb) --> : Erstelle eine Tabelle für Benutzerdaten
terminAl (psql: testdb) --> : Zeige alle Tabellen in der Datenbank
```

## Funktionen

### Kernfunktionen

- **Natürlichsprachliche Befehlsübersetzung:** Konvertiert deutsche Anfragen in Linux-Befehle oder SQL-Abfragen
- **Kontextbewusste Suche:** Integrierte Vektordatenbank für systemspezifische Informationen
- **Sicherheitsbewertung:** Automatische Risikobewertung für vorgeschlagene Befehle
- **PostgreSQL-Integration:** Nahtlose Datenbankinteraktion mit Tabellenerkennung

### Erweiterte Funktionen

- **Automatische Systemerkennung:** Kontinuierliche Aktualisierung der Verzeichnisstruktur
- **Befehlsvalidierung:** Syntax-Prüfung vor Ausführung
- **Interaktive Genehmigung:** Bestätigung durch Benutzende für kritische Operationen

## Projektstruktur

```
terminAl/
├── functions/           # Kernfunktionalität
│   ├── ollama_client.py
│   ├── async_chromadb_*.py
│   ├── system_mapping.py
│   └── userfunctions.py
├── settings/            # Konfigurationsdateien
│   ├── settings.json
│   └── system_prompts.py
├── divers/             # Hilfsdateien und ASCII-Art
├── main.py             # Haupteinstiegspunkt
└── requirements.txt    # Python-Dependencies
```
---
## Lizenz
Siehe `LICENSE` Datei für Details.

### Verwendete LLM-Modelle
Dieses Projekt wurde mit Meta Llama-Modellen (Llama 3.1 und Llama 3.2) entwickelt und getestet. Bei der Verwendung von Llama-Modellen gelten die entsprechenden Lizenzbedingungen von Meta:

- **Llama 3.1:** Unterliegt der Llama 3.1 Community License von Meta
- **Llama 3.2:** Unterliegt der Llama 3.2 Community License von Meta

Für kommerzielle Nutzung oder bei mehr als 700 Millionen monatlich aktiven Nutzenden sind separate Lizenzvereinbarungen mit Meta erforderlich. Weitere Informationen und die vollständigen Lizenzbedingungen finden sich auf der Meta Llama Website.

---
