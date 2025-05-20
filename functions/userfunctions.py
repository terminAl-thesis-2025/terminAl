# Standardbibliotheken
import json
import os
import subprocess
import sys

# Externe Bibliotheken
from dotenv import load_dotenv
from icecream import ic

# Interne Module
from divers.ascii_art import terminAl_ascii

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv("./.env")
# Hole den Pfad zur Terminal-Anwendung aus den Umgebungsvariablen
terminal_path = os.getenv("TERMINAL_PATH")


class UserFunctions:
    """
    Klasse, die Hilfsfunktionen für die Terminal-Anwendung enthält.
    """

    @classmethod
    async def exit(cls):
        """
        Beendet die Anwendung mit einer Abschiedsnachricht.
        """
        print("OK, bye...")
        sys.exit(0)

    @classmethod
    async def help(cls):
        """
        Zeigt eine Hilfeübersicht mit allen verfügbaren Befehlen an.
        """
        print("Verfügbare Befehle:")
        print("  Eingabe ohne \\      - Löst eine Anfrage an das KI-Modell aus.")
        print("                         Es können Keywords in <> angegeben werden, ")
        print("                         was eine Suche nach diesen Keywords in der ")
        print("                         Vektordatenbank auslöst")
        print("     <Begriff>          - Werden bei einer Anfrage an das KI-Modell")
        print("                          Begriffe in <> gesetzt, löst das System zuerst eine Suche")
        print("                          nach diesem Begriff aus und gibt die Resultate")
        print("                          an das KI-Modell weiter. Dies ist nützlich wenn")
        print("                          dem Modell der Pfad zur Datei zur Verfügung")
        print("                          gestellt werden soll.")
        print("  \\exit                - Beendet die Anwendung")
        print("  \\help                - Zeigt diese Hilfe an")
        print("  \\info                - Zeigt Informationen zur Anwendung")
        print("  \\cmd {Befehl}        - Führt einen Shell-Befehl direkt aus")
        print("     cd terminAl         - Zurück zur Applikation")
        print("  \\clear               - Leert den Bildschirm/Terminal")
        print("     logo                - Leert den Bildschirm/Terminal, und zeigt das logo an")
        print("  \\update              - DB-Update Befehle:")
        print("     on                  - Aktiviert automatische DB-Updates")
        print("     off                 - Deaktiviert automatische DB-Updates")
        print("     now                 - Führt sofort ein DB-Update durch")
        print("     status              - Zeigt den aktuellen Status der DB-Updates")
        print("  \\psql                - PostgreSQL Befehle:")
        print("     list                - Listet verfügbare Datenbanken")
        print("     list dbs            - Listet ebenfalls alle verfügbaren Datenbanken")
        print("     list {DB}           - Listet alle Tabellen in der angegebenen Datenbank")
        print("     login {DB}          - Verbindet zu einer angegebenen Datenbank")
        print("     switch {DB}         - Wechselt zu einer anderen Datenbank")
        print("     logout              - Beendet die Datenbankverbindung")
        print("  \\search {Begriff}    - PostgreSQL Befehle:")

    @classmethod
    def info(cls, device, name, memory):
        """
        Zeigt allgemeine Informationen über die Anwendung und ihre Konfiguration an.
        Liest die Einstellungen aus der settings.json-Datei.
        """
        settings = json.load(open(terminal_path + "settings/settings.json"))
        chroma_settings = settings.get("chroma_settings", {})
        ollama_settings = settings.get("ollama_settings", {})
        guard_settings = settings.get("guard_settings", {})

        print("\nAllgemeine Details:")
        print("  terminAl - Eine AI-Agent-Anwendung für Linux-Systeme")
        print("  Version: 0.1 (Proof of Concept)")

        print("\nDevice Details:")
        print(f"  Verfügbares Update Device:    {device}")
        print(f"  Device Name:                  {name}")
        print(f"  VRAM verfügbar:               {memory}GB")

        if settings:
            print("\nModelldetails:")
            print(f"  Ollama Model: {ollama_settings.get('ollama_model', 'Nicht gesetzt')}")
            print(f"  Embedding Model: {chroma_settings.get('embedding_model', 'Nicht gesetzt')}")
            print(f"  Guard Model: {guard_settings.get('guard_model', 'Nicht gesetzt')}")

        else:
            print("Einstellungen wurden nicht geladen.")

    @classmethod
    async def cmd(cls, command):
        """
        Führt einen Shell-Befehl aus.

        Args:
            command: Liste von Befehlsargumenten oder ein Shell-Befehl

        Returns:
            bool: True bei erfolgreicher Ausführung, False bei Fehlern
        """
        try:
            # Prüfe, ob ein Befehl angegeben wurde
            if not command:
                ic()
                ic("Kein Befehl vorhanden.")
                return False

            # Behandlung des 'change directory'-Befehls (wechselt das Verzeichnis)
            if command[0] == "cd":
                if len(command) < 2:
                    ic()
                    ic("Kein Zielpfad verfügbar.")
                    return False

                path = command[1]

                # Sonderfall: cd terminAl (Wechsel zurück zum terminAl-Ordner)
                if path.lower() == "terminal":
                    project_root = os.path.dirname(os.path.abspath(__file__))  # Zeigt auf /functions
                    project_root = os.path.abspath(os.path.join(project_root, ".."))  # Eine Ebene hoch zum Projektroot
                    os.chdir(project_root)
                    print(f"Wechsel zum terminAl-Ordner: {os.getcwd()}")
                    return True

                # Normales cd-Verhalten
                try:
                    os.chdir(path)
                    print(f"Wechsel zum Ordner:{os.getcwd()}")
                    return True
                except FileNotFoundError:
                    ic()
                    ic(f"Ordner existiert nicht: {path}")
                    return False
                except Exception as e:
                    ic()
                    ic(f"Fehler beim Wechseln zum Ordner: {str(e)}")
                    return False

            # Prüfe, ob Shell-Operatoren verwendet werden
            use_shell = any(x in command for x in ["|", ">", "&&", ";"])
            if use_shell:
                popen_input = " ".join(command)  # String für die Shell
            else:
                popen_input = command  # Liste für direkte Ausführung

            # Starte den Prozess
            process = subprocess.Popen(
                popen_input,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Lese stdout live (Zeile für Zeile)
            while True:
                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    print(line.strip())

            return_code = process.wait()

            # Fehlerbehandlung
            if return_code != 0:
                stderr = process.stderr.read()
                if stderr:
                    ic()
                    ic(f"Fehler: {stderr.strip()}")
                else:
                    ic()
                    ic(f"Fehler: Exitcode: {return_code}")

            return return_code == 0

        except Exception as e:
            ic()
            ic(f"Ausnahme eingetreten: {str(e)}")
            return False

    @classmethod
    async def psql(cls, user_input=None):
        """
        Verwaltet PostgreSQL-Datenbankzugriffe.

        Args:
            user_input: Liste mit Unterbefehl und Parametern

        Returns:
            None oder Liste mit Befehl für weitere Verarbeitung
        """
        settings = json.load(open(terminal_path + "settings/settings.json"))
        tool_settings = settings.get("tools", {})

        if not settings:
            ic()
            ic("Einstellungen wurden nicht geladen.")

        try:
            # PostgreSQL-Benutzer und Datenbankliste aus den Einstellungen holen
            username = tool_settings.get('postgres').get('username')
            databases = tool_settings.get('postgres').get('databases')

            # Befehl "list" - zeigt entweder Datenbanken oder Tabellen in einer DB an
            if user_input[0] == "list":
                # Wenn nur "list" oder "list dbs" --> zeige Datenbanken
                if len(user_input) == 1 or (len(user_input) == 2 and user_input[1].lower() == "dbs"):
                    print("Verfügbare Datenbanken:")
                    for db in databases:
                        print(f"  - {db}")
                # Wenn "list <dbname>" --> Liste Tabellen in dieser DB auf
                elif len(user_input) == 2 and user_input[1] in databases:
                    db_name = user_input[1]

                    # Führe psql mit \dt+ Befehl aus, um Tabellen anzuzeigen
                    command = ["sudo", "-u", username, "psql", "-d", db_name, "-c", r"\dt+"]
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    stdout, stderr = process.communicate()

                    if process.returncode == 0:
                        print(stdout)
                        return True
                    else:
                        ic()
                        ic(f"Fehler beim Abfragen der Tabellen:\n{stderr}")
                        return False
                else:
                    ic()
                    ic("Ungültige Eingabe für 'list'. Entweder nur 'list', 'list dbs' oder 'list <DB-Name>' angeben.")
                    return False

            # Befehl "login" - Verbindung zu einer Datenbank herstellen
            elif user_input[0] == "login" and user_input[1] in databases:
                print(f"Starte psql als Benutzer '{username}' auf Datenbank '{user_input[1]}'...")
                return ["sudo", "-u", username, "psql", "-d", user_input[1], "-c"]
            # Befehl "switch" - Wechsel zu einer anderen Datenbank
            elif user_input[0] == "switch" and user_input[1] in databases:
                print(f"Starte psql als Benutzer '{username}' auf Datenbank '{user_input[1]}'...")
                return ["sudo", "-u", username, "psql", "-d", user_input[1], "-c"]
            # Befehl "logout" - Datenbankverbindung beenden
            elif user_input[0] == "logout":
                print("Beendet")
                return None
            else:
                ic()
                ic("Ungültige Eingabe. Bitte 'list', 'list dbs', 'list <DB-Name>' oder eine gültige Datenbank angeben.")
                return False

        except Exception as e:
            ic()
            ic(f"Fehler beim Starten des psql Logins: {str(e)}")
            return False

    @classmethod
    async def clear(cls, option):
        """
        Leert den Bildschirm/Terminal und zeigt optional das Logo an.

        Args:
            option: Wenn "logo", wird das terminAl ASCII-Art Logo angezeigt
        """
        # Führe den clear-Befehl aus, um den Bildschirm zu leeren
        subprocess.run(
            ["clear"],
            capture_output=False,
            text=True
        )
        # Wenn die Option "logo" angegeben wurde, zeige das ASCII-Art Logo
        if option == "logo":
            print(terminAl_ascii)
