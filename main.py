import json
import os

from dotenv import load_dotenv

from functions.system_mapping import SystemMapping
from functions.userfunctions import UserFunctions
from settings.ascii_art import terminAl_ascii

load_dotenv("./settings/.env")

class TerminAl:
    def __init__(self):
        self.settings = json.load(open("./settings/settings.json"))
        self.env = os.getenv("ollama_key")
        self.system_mapping = SystemMapping.import_os_to_vdb()

    def check(self):
        print(self.settings)
        print(self.env)

    def run(self):
        print(terminAl_ascii)
        print("Willkommen bei terminAl!\nBeende die Anwendung mit \\exit")
        while True:
            user_input = input("terminAl --> : ")
            UserFunctions.check_user_input(user_input)


def main():
    """Main entry point for the application."""
    app = TerminAl()
    app.run()

if __name__ == "__main__":
    main()