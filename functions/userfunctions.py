import json
import subprocess
import sys

class UserFunctions:
    """

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
        print("  \\update on      - Aktiviert automatische DB-Updates")
        print("  \\update off     - Deaktiviert automatische DB-Updates")
        print("  \\update now     - Führt sofort ein DB-Update durch")
        print("  \\update status  - Zeigt den aktuellen Status der DB-Updates")

    @classmethod
    async def info(cls):
        print("  terminAl - Eine AI-Agent-Anwendung für Linux-Systeme")
        print("  Version: 0.1 (Proof of Concept)")
        #TODO Modeltypes
        #TODO Last DB Update
        #TODO Grösse der DB

    @classmethod
    async def cmd(cls, command):
        cleared_command = command.split()[1:]
        try:
            result = subprocess.run(
                cleared_command,
                capture_output=True,
                text=True,
                check=True
            )

            # Print stdout
            print(result.stdout)

            # If you also want stderr
            print(result.stderr)

            # Return the result for further processing if needed
            return result

        except subprocess.CalledProcessError as e:
            # Print error output
            print(f"Command failed with error: {e.stderr}")
            return False

        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return False

    @classmethod
    async def psql_login(cls):
        #TODO set up
        pass


