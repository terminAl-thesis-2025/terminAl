import asyncio
import json
import os
import subprocess

from dotenv import load_dotenv
from icecream import ic

from functions import *
from functions.system_mapping import SystemMapping

load_dotenv("./settings/.env")

class TerminAl:
    def __init__(self):
        self.settings = json.load(open("./settings/settings.json"))
        self.env = os.getenv("ollama_key")
        self.system_mapping = SystemMapping.import_os_to_vdb()

    def check(self):
        print(self.settings)
        print(self.env)

def main():
    """Main entry point for the application."""
    app = TerminAl()
    app.check()

if __name__ == "__main__":
    main()