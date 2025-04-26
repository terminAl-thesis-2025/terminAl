import json
import os
import asyncio
import sys

from dotenv import load_dotenv

from functions.ollama_client import OllamaClient
from functions.userfunctions import UserFunctions
from functions.async_chromadb_updater import AsyncChromaDBUpdater
from functions.async_chromadb_retriever import AsyncChromaDBRetriever
from functions.async_environment_retriever import environment_retriever
from settings.ascii_art import terminAl_ascii

load_dotenv("./settings/.env")


class TerminAl:
    def __init__(self):
        self.settings = json.load(open("./settings/settings.json"))
        self.env = os.getenv("ollama_key")
        self.chroma_updater = AsyncChromaDBUpdater()
        self.ollama_client = OllamaClient()
        self.chroma_retriever = AsyncChromaDBRetriever()

    async def check(self):
        print(self.settings)
        print(self.env)

    async def run(self):
        await UserFunctions.clear()

        print(terminAl_ascii)
        print("Willkommen bei terminAl!\nZeige Benutzerhandbuch mit: \\help")

        # Start the ChromaDB update cycle as a background task
        update_task = asyncio.create_task(self.chroma_updater.start_update_cycle())

        # Track manual update tasks
        manual_update_task = None

        # Run the main input loop
        try:
            while True:
                user_input = await self.get_user_input()

                # Verwenden der bestehenden UserFunctions-Klasse für die Standardbefehle
                if user_input.startswith(r"\update on"):
                    await self.chroma_updater.auto_update_on()
                    print("Automatisches Update wurde aktiviert.")
                elif user_input.startswith(r"\update off"):
                    await self.chroma_updater.auto_update_off()
                    print("Automatisches Update wurde deaktiviert.")
                elif user_input.startswith(r"\update now"):
                    print("Update startet. Bitte warten.")
                    if not manual_update_task or manual_update_task.done():
                        print("Bitte warten bis das Update beendet ist.")
                        manual_update_task = asyncio.create_task(self.chroma_updater.update_system_mapping())
                        await manual_update_task
                        print("Update abgeschlossen.")
                elif user_input.startswith(r"\update status"):
                    update_status = self.chroma_updater.chroma_settings.get("chroma_auto_update", "Status nicht verfügbar")
                    latest_update = self.chroma_updater.chroma_settings.get("chroma_latest_update",
                                                                     "Keine Information verfügbar")
                    print(f"Auto Update Status:         {update_status}")
                    print(f"Letztes Update:             {latest_update}")
                elif user_input.startswith(r"\cmd"):
                    await UserFunctions.cmd(user_input)
                elif user_input.startswith(r"\exit"):
                    await UserFunctions.exit()
                elif user_input.startswith(r"\help"):
                    await UserFunctions.help()
                elif user_input.startswith(r"\info"):
                    await UserFunctions.info()
                elif user_input.startswith(r"\search"):
                    user_input = user_input.split(" ")
                    seach_results = await self.chroma_retriever.fulltext_search(user_input[1:], top_k=2)
                    print(seach_results)
                elif user_input.startswith(r"\clear"):
                    await UserFunctions.clear()
                elif user_input.startswith(r"\chromadb_collections"):
                    self.chroma_updater.list_collections()
                elif user_input.startswith("\\"):
                    print("Unbekannter Befehl. Zeige alle Befehle mit \\help")
                else:
                    vector_context, environment_context = await asyncio.gather(
                        self.chroma_retriever.retrieve(user_input, top_k=2),
                        environment_retriever()
                    )

                    # Starte mit wichtigem Kontext (Umgebungskontext)
                    combined_context = (
                        "### BEGINN AKTUELLE UMGEBUNGSINFORMATIONEN\n"
                        f"{json.dumps(environment_context, indent=2, ensure_ascii=False)}\n"
                        "### ENDE AKTUELLE UMGEBUNGSINFORMATIONEN\n\n"
                        "### BEGINN SYSTEM-WISSENSDATENBANK (aus lokaler ChromaDB abgerufen)\n"
                        f"{vector_context}\n"
                        "### ENDE SYSTEM-WISSENSDATENBANK\n"
                    )

                    print(combined_context)
                    result = await self.ollama_client.query(prompt=user_input, system_context=combined_context)
                    print(result)
                    #TODO Geordnete Anzeige: zeige Command und Beschreibung

        except KeyboardInterrupt:
            print("\nBeenden der Anwendung...")
        finally:
            # Cancel all running tasks when exiting
            update_task.cancel()

            # Also cancel manual update task if it exists and is running
            if manual_update_task and not manual_update_task.done():
                manual_update_task.cancel()

            # Wait for all tasks to be properly cancelled
            try:
                await update_task
                if manual_update_task:
                    await manual_update_task
            except asyncio.CancelledError:
                pass

    async def get_user_input(self):
        """
        Non-blocking user input that doesn't block the event loop
        """
        try:
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(None, lambda: input("terminAl --> : "))
            return user_input
        except (EOFError, KeyboardInterrupt):
            return r"\exit"


async def main():
    """Main entry point for the application."""
    app = TerminAl()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
        sys.exit(0)