import asyncio, json, os, sys

from dotenv import load_dotenv
from icecream import ic

from functions.ollama_client import OllamaClient
from functions.userfunctions import UserFunctions
from functions.async_chromadb_updater import AsyncChromaDBUpdater
from functions.async_chromadb_retriever import AsyncChromaDBRetriever
from functions.async_environment_retriever import environment_retriever
from divers.ascii_art import terminAl_ascii
from divers.example_responses import example_dict

load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class TerminAl:
    def __init__(self):
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
        self.env = os.getenv("ollama_key")
        self.chroma_updater = AsyncChromaDBUpdater()
        self.ollama_client = OllamaClient()
        self.chroma_retriever = AsyncChromaDBRetriever()
        self.current_user_database = None

    async def check(self):
        print(self.settings)
        print(self.env)

    async def run(self):
        await UserFunctions.clear(option=False)

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
                if user_input.startswith(r"\update"):
                    action = user_input.split(" ")[1]
                    match action:
                        case "on":
                            await self.chroma_updater.auto_update_on()
                            print("Automatisches Update wurde aktiviert.")
                        case "off":
                            await self.chroma_updater.auto_update_off()
                            print("Automatisches Update wurde deaktiviert.")
                        case "now":
                            print("Update startet. Bitte warten.")
                            if not manual_update_task or manual_update_task.done():
                                print("Bitte warten bis das Update beendet ist.")
                                manual_update_task = asyncio.create_task(self.chroma_updater.update_system_mapping())
                                await manual_update_task
                                print("Update abgeschlossen.")
                        case "status":
                            update_status = self.chroma_updater.chroma_settings.get("chroma_auto_update",
                                                                                    "Status nicht verfügbar")
                            latest_update = self.chroma_updater.chroma_settings.get("chroma_latest_update",
                                                                                    "Keine Information verfügbar")
                            print(f"Auto Update Status:         {update_status}")
                            print(f"Letztes Update:             {latest_update}")
                        case _:
                            print(f"Unbekannter Befehl: {action}")

                elif user_input.startswith(r"\cmd"):
                    command = user_input.split()[1:]
                    await UserFunctions.cmd(command)

                elif user_input.startswith(r"\exit"):
                    await UserFunctions.exit()

                elif user_input.startswith(r"\help"):
                    await UserFunctions.help()

                elif user_input.startswith(r"\info"):
                    UserFunctions.info()

                elif user_input.startswith(r"\search"):
                    user_input = user_input.split(" ")
                    seach_results = await self.chroma_retriever.fulltext_search(user_input[1:], top_k=2)
                    print(seach_results)

                elif user_input.startswith(r"\clear"):
                    option = user_input.split(" ")
                    if len(option) > 1:
                        option = option[1]
                    else:
                        option = None
                    await UserFunctions.clear(option)

                elif user_input.startswith(r"\psql"):
                    parts = user_input.split(" ")
                    if len(parts) >= 2:
                        self.current_user_database = await UserFunctions.psql(parts[1:])
                    else:
                        print("❗ Bitte gib entweder 'list' oder einen Datenbanknamen an.")

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
                    #result = await self.ollama_client.query(prompt=user_input, system_context=combined_context)
                    examples = json.dumps(example_dict, ensure_ascii=False)

                    examples = json.loads(examples)
                    result = examples.get(user_input, {})
                    command = result.get("command", None)

                    print(command)
                    if command:
                        decision = input("Befehl genehmigen oder ablehnen (J/N): ").lower()
                    else:
                        print("Kein Befehl erhalten.")
                        continue
                    if decision == "j":
                        if result["tool"] == "sql" and self.current_user_database:
                            command_list = self.current_user_database + [command]
                            await UserFunctions.cmd(command_list)
                        elif result["tool"] == "sql" and not self.current_user_database:
                            print("Bitte zuerst \\psql login <Datenbankname> ausführen.")
                        elif result["tool"] == "bash" and self.current_user_database:
                            print("Bitte von Datenbank abmelden oder reinen SQL-Befehl eingeben.")
                        elif result["tool"] == "bash" and not self.current_user_database:
                            command_list = command.split(" ")
                            await UserFunctions.cmd(command_list)
                    elif decision == "n":
                        print("Befehl wurde abgelehnt!")
                    else:
                        print("abbruch aufgrund ungültiger Eingabe!")




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
            # Build the prompt based on whether we have a current database
            if self.current_user_database:
                prompt = f"terminAl (psql) --> : "
            else:
                prompt = "terminAl --> : "

            loop = asyncio.get_event_loop()
            # You can pass `input` and its argument directly to run_in_executor
            user_input = await loop.run_in_executor(None, input, prompt)
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