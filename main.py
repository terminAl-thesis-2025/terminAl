import asyncio, json, os, re, shlex, sys

from dotenv import load_dotenv
from icecream import ic

from functions.ollama_client import OllamaClient
from functions.userfunctions import UserFunctions
from functions.async_chromadb_updater import AsyncChromaDBUpdater
from functions.async_chromadb_retriever import AsyncChromaDBRetriever
from functions.async_environment_retriever import environment_retriever
from functions.system_mapping import SystemMapping
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
                    seach_results = await self.chroma_retriever.fulltext_search(user_input[1:], top_k=10)
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
                    """
                    vector_context, environment_context = await asyncio.gather(
                        self.chroma_retriever.retrieve(user_input, top_k=5, threshold=10),
                        environment_retriever()
                    )
                    """

                    keywords = self.extract_keywords(user_input)

                    if not self.current_user_database:
                        vector_context, environment_context = await asyncio.gather(
                            self.chroma_retriever.fulltext_search(keywords, top_k=5, query=True),
                            environment_retriever()
                        )
                    elif self.current_user_database:
                        postgres_context = SystemMapping.map_postgres(active_database=self.current_user_database)
                        vector_context, environment_context = await asyncio.gather(
                            self.chroma_retriever.fulltext_search(keywords, top_k=5, query=True),
                            environment_retriever()
                        )
                    # Remove <>, otherwise the model gets confused
                    cleaned_user_input = self.clean_input(user_input)

                    # Starte mit wichtigem Kontext (Umgebungskontext)
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
                        "Nutze dazu die folgenden Pfade oder Datenbankdetails, wenn vorhanden:"
                        f"{postgres_context if self.current_user_database else vector_context}\n"
                        "# ENDE USERPROMPT\n"
                    )
                    ic()
                    ic(full_prompt)

                    result = await self.ollama_client.query(prompt=full_prompt)

                    def fix_json_escapes(s):
                        # Escape any stray backslashes not part of valid JSON escapes
                        # Replace: unescaped \ → \\ unless it's already \\ or part of \"
                        s = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', s)
                        return s

                    # Try fixing the result string before parsing
                    try:
                        safe_result = fix_json_escapes(result)
                        parsed = json.loads(safe_result)
                    except json.JSONDecodeError as e:
                        print("❗ JSON konnte nicht geparsed werden.")
                        print("Fehlermeldung:", e)
                        print("Antwort vom Modell:")
                        print(result)

                    examples = json.dumps(example_dict, ensure_ascii=False)

                    ic()
                    ic(type(parsed))
                    ic(parsed)



                    examples = json.loads(examples)
                    #result = examples.get(user_input, {})
                    command = parsed.get("command", None)

                    ic()
                    ic(type(command))
                    ic(command)

                    print(command)
                    if command:
                        decision = input("Befehl genehmigen oder ablehnen (J/N): ").lower()
                    else:
                        print("Kein Befehl erhalten.")
                        continue
                    if decision == "j":
                        if parsed["tool"] == "sql" and self.current_user_database:
                            command_list = self.current_user_database + [command]
                            await UserFunctions.cmd(command_list)
                        elif parsed["tool"] == "sql" and not self.current_user_database:
                            print("Bitte zuerst \\psql login <Datenbankname> ausführen.")
                        elif parsed["tool"] == "bash" and self.current_user_database:
                            print("Bitte von Datenbank abmelden oder reinen SQL-Befehl eingeben.")
                        elif parsed["tool"] == "bash" and not self.current_user_database:
                            command_list = shlex.split(command)
                            # Entferne "sudo" falls vorhanden (Prozess läuft schon als root)
                            command_list = [item for item in command_list if item.lower() != "sudo"]
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

    def extract_keywords(self, user_input: str) -> list[str]:
        """
        Extracts keywords wrapped in angle brackets: <keyword>
        """
        return re.findall(r"<([^<>]+)>", user_input)

    def clean_input(self, user_input: str) -> str:
        return re.sub(r"[<>]", "", user_input)


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