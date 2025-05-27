# Standard Bibliotheken
import asyncio  # Für asynchrone Programmierung
import json  # Für JSON Verarbeitung
import os  # Für Betriebssystemfunktionen
import re  # Für reguläre Ausdrücke
import shlex  # Für Shell-Argument-Parsing
import sys  # Für Systemfunktionen

# Externe Bibliotheken
from dotenv import load_dotenv  # Laden von Umgebungsvariablen aus .env Dateien
from icecream import ic  # Für verbesserte Debug-Ausgaben

# Eigene Module
from functions.ollama_client import OllamaClient
from functions.userfunctions import UserFunctions
from functions.async_chromadb_updater import AsyncChromaDBUpdater
from functions.async_chromadb_retriever import AsyncChromaDBRetriever
from functions.async_environment_retriever import environment_retriever
from functions.terminal_guard import TerminAlGuard

# Umgebungsvariablen aus .env Datei laden
load_dotenv("./.env")
terminal_path = os.getenv("TERMINAL_PATH")  # Pfad zum Terminal-Verzeichnis


class TerminAl:
    """
    Hauptklasse für das TerminAl-Programm, das eine intelligente Terminal-Schnittstelle bietet.
    Verwaltet ChromaDB für Vektorsuche und interagiert mit dem Ollama-Sprachmodell.
    """

    def __init__(self):
        """
        Initialisiert die TerminAl-Instanz mit allen erforderlichen Komponenten.
        """
        self.settings = json.load(
            open(terminal_path + "settings/settings.json"))  # Lädt Einstellungen aus der JSON-Datei
        self.env = os.getenv("ollama_key")  # API-Schlüssel für Ollama
        self.chroma_updater = AsyncChromaDBUpdater()  # Komponente für ChromaDB-Updates
        self.ollama_client = OllamaClient()  # Client für die Kommunikation mit dem Ollama-Modell
        self.chroma_retriever = AsyncChromaDBRetriever()  # Komponente für ChromaDB-Abfragen
        self.current_user_database = None  # Aktuelle Datenbankverbindung des Benutzers
        self.manual_update_task = None  # Task für manuelles Update initialisieren
        self.guard = TerminAlGuard()

    async def check(self):
        """
        Überprüft die Einstellungen und Umgebungsvariablen (Hilfsfunktion für Debugging).
        """
        print(self.settings)
        print(self.env)

    async def run(self):
        """
        Hauptausführungsroutine, die die Benutzeroberfläche startet und Eingaben verarbeitet.
        """
        await UserFunctions.clear(option="logo")  # Terminal bereinigen

        print("Willkommen bei terminAl!\nZeige Benutzerhandbuch mit: \\help")

        # ChromaDB-Update-Zyklus als Hintergrundtask starten
        update_task = asyncio.create_task(self.chroma_updater.start_update_cycle())

        # Haupteingabeschleife ausführen
        try:
            while True:
                user_input = await self.get_user_input()  # Benutzereingabe asynchron erhalten

                # Verwenden der bestehenden UserFunctions-Klasse für die Standardbefehle
                if user_input.startswith(r"\update"):
                    action = user_input.split(" ")[1]  # Aktionsbefehl extrahieren
                    match action:
                        case "on":
                            await self.chroma_updater.auto_update_on()  # Automatisches Update aktivieren
                            print("Automatisches Update wurde aktiviert.")
                        case "off":
                            await self.chroma_updater.auto_update_off()  # Automatisches Update deaktivieren
                            print("Automatisches Update wurde deaktiviert.")
                        case "now":
                            print("Update startet. Bitte warten.")
                            if not self.manual_update_task or self.manual_update_task.done():
                                print("Bitte warten bis das Update beendet ist.")
                                # Manuelles Update als Task starten
                                self.manual_update_task = asyncio.create_task(self.chroma_updater.update_system_mapping())
                                await self.manual_update_task  # Auf Abschluss warten
                                print("Update abgeschlossen.")
                        case "status":
                            # Status und Zeitpunkt des letzten Updates anzeigen
                            update_status = self.chroma_updater.chroma_settings.get("chroma_auto_update",
                                                                                    "Status nicht verfügbar")
                            latest_update = self.chroma_updater.chroma_settings.get("chroma_latest_update",
                                                                                    "Keine Information verfügbar")
                            print(f"Auto Update Status:         {update_status}")
                            print(f"Letztes Update:             {latest_update}")
                        case _:
                            print(f"Unbekannter Befehl: {action}")

                elif user_input.startswith(r"\cmd"):
                    # Befehl an das Betriebssystem weiterleiten
                    command = user_input.split()[1:]
                    await UserFunctions.cmd(command)

                elif user_input.startswith(r"\exit"):
                    # Anwendung beenden
                    await UserFunctions.exit()

                elif user_input.startswith(r"\help"):
                    # Hilfetext anzeigen
                    await UserFunctions.help()

                elif user_input.startswith(r"\info"):
                    # Systeminformationen anzeigen
                    update_device = self.chroma_updater.device
                    update_device_name = self.chroma_updater.device_name
                    update_device_memory = self.chroma_updater.device_memory
                    UserFunctions.info(device=update_device,
                                       name=update_device_name,
                                       memory=update_device_memory)

                elif user_input.startswith(r"\search"):
                    # Volltextsuche in ChromaDB durchführen
                    user_input = user_input.split(" ")
                    await self.chroma_retriever.fulltext_search(user_input[1:], top_k=10)

                elif user_input.startswith(r"\clear"):
                    # Terminal bereinigen
                    option = user_input.split(" ")
                    if len(option) > 1:
                        option = option[1]
                    else:
                        option = None
                    await UserFunctions.clear(option=option)

                elif user_input.startswith(r"\psql"):
                    # PostgreSQL-Datenbankverbindung herstellen
                    parts = user_input.split(" ")
                    if len(parts) >= 2:
                        current_user_database = await UserFunctions.psql(parts[1:])

                        match current_user_database:
                            case True | False:
                                pass
                            case None:
                                self.current_user_database = None
                            case list() as db_conn:  # Match any list and capture it as db_conn
                                self.current_user_database = db_conn
                            case _:
                                ic()
                                ic(f"Unerwartete Datenbankkonfiguration: {type(current_user_database)}")
                    else:
                        print("Bitte gib entweder 'list' oder einen Datenbanknamen an.")

                elif user_input.startswith(r"\chromadb_collections"):
                    # ChromaDB-Sammlungen auflisten
                    self.chroma_updater.list_collections()

                elif user_input.startswith(r"\model"):
                    user_input = user_input.split(" ")
                    await UserFunctions.model(user_input[1:])

                elif user_input.startswith("\\"):
                    # Unbekannter Befehl
                    print("Unbekannter Befehl. Zeige alle Befehle mit \\help")

                else:
                    print("Prompt wird bearbeitet...")
                    # Schlüsselwörter aus der Benutzereingabe extrahieren
                    keywords = self.extract_keywords(user_input)

                    # Kontext basierend auf dem Datenbankstatus abrufen
                    if not self.current_user_database:
                        # Wenn keine Datenbankverbindung besteht, nur Vektor- und Umgebungskontext holen
                        vector_context, environment_context = await asyncio.gather(
                            self.chroma_retriever.fulltext_search(keywords, top_k=5),
                            environment_retriever()
                        )
                    elif self.current_user_database:
                        # Wenn Datenbankverbindung besteht, zusätzlich PostgreSQL-Kontext holen
                        vector_context, environment_context, postgres_context = await asyncio.gather(
                            self.chroma_retriever.fulltext_search(keywords, top_k=5),
                            environment_retriever(),
                            UserFunctions.psql(user_input=["list", self.current_user_database[5]])
                        )

                    # Spitzklammern entfernen, um Verwirrung des Modells zu vermeiden
                    cleaned_user_input = self.clean_input(user_input)

                    # Prompterstellung für das Sprachmodell mit relevanten Kontextinformationen
                    full_prompt = (
                        "Nutze die folgenden Kontextinformationen, wenn sie bei der Beantwortung der Benutzerfrage hilfreich sind.\n"
                        "Falls Pfade oder Dateinamen angegeben sind, kannst du daraus Ordner ableiten (z.B. durch Entfernen von Dateinamen oder Kürzen auf relevante Teilpfade).\n"
                        "Vermeide generische Platzhalter wie `/home/user/...` oder `*.pdf`, aber passe Pfade **sinnvoll** an, wenn sie eindeutig auf einen Zielordner hinweisen.\n"
                        "Wenn ein Pfad Leerzeichen enthält, setze ihn in einfache Anführungszeichen (z.B. `'... Ordner mit Leerzeichen'`).\n\n"
                        "### BEGINN AKTUELLE UMGEBUNGSINFORMATIONEN\n"
                        f"{json.dumps(environment_context, indent=2, ensure_ascii=False)}\n"
                        "### ENDE AKTUELLE UMGEBUNGSINFORMATIONEN\n\n"
                        "# BEGINN USERPROMPT\n"
                        f"{cleaned_user_input}\n"
                        "Nutze dazu die folgenden Pfade oder Datenbankdetails, wenn vorhanden. Priorisiere den Kontext über Umgebungsinformationen, falls nötig:"
                        f"{postgres_context if self.current_user_database else vector_context}\n"
                        "# ENDE USERPROMPT\n"
                    )

                    # Anfrage an das Ollama-Modell senden
                    result = await self.ollama_client.query(prompt=full_prompt)


                    # Versuchen, die Ergebniszeichenkette vor dem Parsen zu korrigieren
                    try:
                        safe_result = self.fix_json_escapes(result)
                        parsed = json.loads(safe_result)
                    except json.JSONDecodeError as e:
                        ic() # JSON konnte nicht geparsed werden
                        ic(f"Modell hat ungültiges JSON-Format zurückgegeben: {e}")
                        ic("Antwort vom Modell:")
                        ic(result)
                        continue

                    # Befehl aus der Modellantwort extrahieren
                    command = parsed.get("command")
                    risk_level = parsed.get("risk_level")
                    detailed_description = parsed.get("detailed_description")

                    # Beende Iteration wenn kein Befehl vorhanden ist
                    if not command:
                        ic()
                        ic("Keinen Befehl vom Modell erhalten.")
                        continue

                    # Warnung wenn kein risk_level angegeben wurde
                    if risk_level is None:
                        ic()
                        ic("Warnung: Modell hat kein risk_level zurückgeliefert.")
                    else:
                        # Erst den Guard prüfen
                        try:
                            await self.guard.check(command, risk_level)  # Zeigt Warnung bei Abweichung
                        except Exception as e:
                            ic()
                            ic(f"Fehler bei der Überprüfung durch den Guard: {e}")
                            continue

                    # Danach Informationen für den Benutzer anzeigen
                    print("\n--- Vorschlag vom Modell ---")
                    print(f"🖥️  Befehl                : {command}")
                    print(f"🛡️  Risikoeinschätzung    : {risk_level}")
                    if detailed_description:
                        print(f"ℹ️  Beschreibung      : {detailed_description}")
                    print("----------------------------")
                    # Benutzerentscheidung für Befehlsausführung einholen
                    if command:
                        decision = input("Befehl genehmigen oder ablehnen (J/N): ").lower()
                    else:
                        print("Keinen Befehl erhalten.")
                        continue

                    # Befehl basierend auf der Benutzerentscheidung und dem Typ ausführen
                    if decision == "j":
                        if parsed["tool"] == "sql" and self.current_user_database:
                            # Spezialfälle in der Funktion psql_command abwickeln
                            command_list = self.psql_command(command)

                            # SQL-Befehl mit aktiver Datenbankverbindung ausführen
                            await UserFunctions.cmd(command_list)
                        elif parsed["tool"] == "sql" and not self.current_user_database:
                            print("Bitte zuerst \\psql login <Datenbankname> ausführen.")
                        elif parsed["tool"] == "bash" and self.current_user_database:
                            print("Bitte von Datenbank abmelden oder reinen SQL-Befehl eingeben.")
                        elif parsed["tool"] == "bash" and not self.current_user_database:
                            # shlex teilt den command unter berücksichtigung von Anführungszeichen
                            command_list = shlex.split(command)
                            # "sudo" entfernen, falls vorhanden (Prozess läuft bereits als root)
                            command_list = [item for item in command_list if item.lower() != "sudo"]
                            await UserFunctions.cmd(command_list)
                    elif decision == "n":
                        print("Befehl wurde abgelehnt!")
                    else:
                        print("Abbruch aufgrund ungültiger Eingabe!")

        except KeyboardInterrupt:
            print("\nBeenden der Anwendung...")
        finally:
            # Alle laufenden Tasks beim Beenden abbrechen
            update_task.cancel()

            # Auch manuellen Update-Task abbrechen, falls er existiert und noch läuft
            if self.manual_update_task and not self.manual_update_task.done():
                self.manual_update_task.cancel()

            # Warten, bis alle Tasks ordnungsgemäß abgebrochen wurden
            try:
                await update_task
                if self.manual_update_task:
                    await self.manual_update_task
            except asyncio.CancelledError:
                pass

    async def get_user_input(self):
        """
        Nicht-blockierende Benutzereingabe, die den Event-Loop nicht blockiert.
        Passt die Eingabeaufforderung basierend auf dem aktuellen Datenbankstatus an.

        Returns:
            str: Die vom Benutzer eingegebene Zeichenkette
        """
        try:
            # Prompt basierend auf dem Datenbankstatus erstellen
            if self.current_user_database:
                prompt = f"terminAl (psql: {self.current_user_database[5]}) --> : "
            else:
                prompt = "terminAl --> : "

            loop = asyncio.get_event_loop()
            # Input-Funktion und ihr Argument direkt an run_in_executor übergeben
            user_input = await loop.run_in_executor(None, input, prompt)
            return user_input
        except (EOFError, KeyboardInterrupt):
            return r"\exit"

    def extract_keywords(self, user_input: str) -> list[str]:
        """
        Extrahiert Schlüsselwörter, die in spitzen Klammern eingeschlossen sind: <Schlüsselwort>

        Args:
            user_input: Die Benutzereingabe, die analysiert werden soll

        Returns:
            list[str]: Liste der gefundenen Schlüsselwörter
        """
        return re.findall(r"<([^<>]+)>", user_input)

    def clean_input(self, user_input: str) -> str:
        """
        Entfernt spitze Klammern aus der Benutzereingabe.

        Args:
            user_input: Die zu bereinigende Benutzereingabe

        Returns:
            str: Die bereinigte Eingabe ohne spitze Klammern
        """
        return re.sub(r"[<>]", "", user_input)

    def fix_json_escapes(self, s):
        r"""
        Korrigiert fehlerhaft formatierte JSON-Escapes in der Zeichenkette.
        Ersetzt: nicht-escapte \ → \\ sofern es nicht bereits \\ oder Teil von \" ist.
        """
        s = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', s)
        return s

    def psql_command(self, command):
        """
        Verarbeitet SQL-Befehle für die PostgreSQL-Datenbankverbindung.
        Behandelt verschiedene Befehlsformate und bereitet sie für die Ausführung vor.

        Args:
            command: Der auszuführende SQL-Befehl (str oder list)

        Returns:
            list: Eine Liste mit dem vollständigen Befehl für die Ausführung
        """
        command_list = self.current_user_database.copy()  # Kopie der Datenbank-Verbindungsparameter erstellen

        if "-f" in command:
            # Sonderbehandlung für Dateiimport-Befehle mit dem "-f" Flag
            # Bei Dateiimports muss das vorhandene "-c" Flag durch "-f" ersetzt werden
            # und der Befehlsaufbau angepasst werden

            # Shell-Argument-Parsing für korrekte Behandlung von Anführungszeichen im Befehl
            command = shlex.split(command)

            # Das letzte Element (normalerweise "-c" Flag) aus der Verbindungsparameter-Liste entfernen,
            # da wir es mit den neuen Parametern aus dem Modellbefehl ersetzen werden
            command_list.pop()

            # Die letzten zwei Elemente vom empfohlenen Befehl anhängen
            # ("-f"-Flag und der Pfad zur SQL-Datei)
            command_list.extend(command[-2:])

            return command_list

        else:
            # Bei String-Befehlen, als neues Listenelement anhängen
            if isinstance(command, str):
                command_list.append(command)
            # Bei Listen-Befehlen, die Liste erweitern
            elif isinstance(command, list):
                command_list.extend(command)

            return command_list

async def main():
    """
    Haupteinstiegspunkt für die Anwendung.
    Erstellt und startet die TerminAl-Instanz.
    """
    app = TerminAl()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
        sys.exit(0)