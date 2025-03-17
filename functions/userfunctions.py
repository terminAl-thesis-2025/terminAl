import json
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
        print("  \\update on      - Aktiviert automatische DB-Updates")
        print("  \\update off     - Deaktiviert automatische DB-Updates")
        print("  \\update now     - Führt sofort ein DB-Update durch")

    @classmethod
    async def info(cls):
        print("  terminAl - Eine AI-Agent-Anwendung für Linux-Systeme")
        print("  Version: 0.1 (Proof of Concept)")
        #TODO Modeltypes
        #TODO Last DB Update
        #TODO Grösse der DB


