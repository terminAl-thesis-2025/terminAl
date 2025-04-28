import json, os, subprocess, sys
from divers.ascii_art import terminAl_ascii
from dotenv import load_dotenv
from icecream import ic

load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class UserFunctions:
    """
    Class containing utility functions for the Terminal app.
    """

    @classmethod
    async def exit(cls):
        print("OK, bye...")
        sys.exit(0)

    @classmethod
    async def help(cls):
        print("Verfügbare Befehle:")
        print("  \\exit           - Beendet die Anwendung")
        print("  \\help           - Zeigt diese Hilfe an")
        print("  \\info           - Zeigt Informationen zur Anwendung")
        print("  \\cmd <Befehl>   - Führt einen Shell-Befehl direkt aus")
        print("     cd terminAl  - Zurück zur Applikation")
        print("  \\clear          - Leert den Bildschirm/Terminal")
        print("  \\update         - DB-Update Befehle:")
        print("     on           - Aktiviert automatische DB-Updates")
        print("     off          - Deaktiviert automatische DB-Updates")
        print("     now          - Führt sofort ein DB-Update durch")
        print("     status       - Zeigt den aktuellen Status der DB-Updates")
        print("  \\psql           - PostgreSQL Befehle:")
        print("     list         - Listet verfügbare Datenbanken")
        print("     login <DB>   - Verbindet zu einer angegebenen Datenbank")
        print("     switch <DB>  - Wechselt zu einer anderen Datenbank")
        print("     logout       - Beendet die Datenbankverbindung")

    @classmethod
    def info(cls):
        settings = json.load(open(terminal_path + "settings/settings.json"))
        chroma_settings = settings.get("chroma_settings", {})
        ollama_settings = settings.get("ollama_settings", {})

        print("\nAllgemeine Details:")
        print("  terminAl - Eine AI-Agent-Anwendung für Linux-Systeme")
        print("  Version: 0.1 (Proof of Concept)")

        if settings:
            print("\nModelldetails:")
            print(f"  Ollama Model: {ollama_settings.get('ollama_model', 'Nicht gesetzt')}")
            print(f"  Embedding Model: {chroma_settings.get('embedding_model', 'Nicht gesetzt')}")
        else:
            print("Einstellungen wurden nicht geladen.")

    @classmethod
    async def cmd(cls, command):
        try:
            if not command:
                print("No command provided.")
                return False

            # Handle 'cd' manually
            if command[0] == "cd":
                if len(command) < 2:
                    print("No path provided for cd.")
                    return False

                path = command[1]

                # Special case: cd terminAl
                if path.lower() == "terminal":
                    project_root = os.path.dirname(os.path.abspath(__file__))  # This points to /functions
                    project_root = os.path.abspath(os.path.join(project_root, ".."))  # Go one level up to project root
                    os.chdir(project_root)
                    print(f"Changed directory to project root: {os.getcwd()}")
                    return True

                # Regular cd behavior
                try:
                    os.chdir(path)
                    print(f"Changed directory to {os.getcwd()}")
                    return True
                except FileNotFoundError:
                    print(f"No such directory: {path}")
                    return False
                except Exception as e:
                    print(f"Failed to change directory: {str(e)}")
                    return False

            ic()
            ic(command)

            use_shell = any(x in command for x in ["|", ">", "&&", ";"])  # Detect shell operators
            if use_shell:
                popen_input = " ".join(command)  # string for shell
            else:
                popen_input = command  # list for direct execution

            process = subprocess.Popen(
                popen_input,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            process = subprocess.Popen(
                popen_input,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Read stdout live
            while True:
                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    print(line.strip())

            return_code = process.wait()

            if return_code != 0:
                stderr = process.stderr.read()
                if stderr:
                    print(f"Error: {stderr.strip()}")
                else:
                    print(f"Error: Command exited with code {return_code}")

            return return_code == 0

        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return False

    @classmethod
    async def psql(cls, user_input=None):
        settings = json.load(open(terminal_path + "settings/settings.json"))
        tool_settings = settings.get("tools", {})

        if not settings:
            print("Einstellungen wurden nicht geladen.")
            return None

        try:
            username = tool_settings.get('postgres').get('username')
            databases = tool_settings.get('postgres').get('databases')

            if user_input[0] == "list":
                print("Verfügbare Datenbanken:")
                for db in databases:
                    print(f"  - {db}")
                    return None
            elif user_input[0] == "login" and user_input[1] in databases:
                print(f"Starte psql als Benutzer '{username}' auf Datenbank '{user_input[1]}'...")
                return ["sudo", "-u", username, "psql", "-d", user_input[1], "-c"]
            elif user_input[0] == "switch" and user_input[1] in databases:
                print(f"Starte psql als Benutzer '{username}' auf Datenbank '{user_input[1]}'...")
                return ["sudo", "-u", username, "psql", "-d", user_input[1], "-c"]
            elif user_input[0] == "logout":
                print("Beendet")
                return None
            else:
                print("Ungültige Eingabe. Bitte 'list' aufrufen oder eine gültige Datenbank angeben.")
                return None

        except Exception as e:
            print(f"Fehler beim Starten des psql Logins: {str(e)}")
            return None

    @classmethod
    async def clear(cls, option):
        subprocess.run(
            ["clear"],
            capture_output=False,
            text=True
        )
        if option == "logo":
            print(terminAl_ascii)



