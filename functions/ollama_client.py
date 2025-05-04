# Standardbibliotheken
import json
import os

# Externe Bibliotheken
from dotenv import load_dotenv
from icecream import ic
from ollama import AsyncClient

# Interne Module
from settings.system_prompts import system_prompt

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class OllamaClient:
    """
    Eine Klasse zur Verwaltung der Interaktionen mit der Ollama-API.
    Diese bietet eine Schnittstelle für Anfragen an das LLM und die Verarbeitung von Antworten.
    """

    def __init__(self):
        """
        Initialisiere den Ollama-Client mit Konfiguration
        """
        # Lade Einstellungen aus der Konfigurationsdatei
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
        # Extrahiere Ollama-spezifische Einstellungen
        self.ollama_settings = self.settings.get("ollama_settings", {})
        # Setze Host-URL mit Fallback auf localhost
        self.host = self.ollama_settings.get("ollama_url", "http://localhost:11434")
        # Setze Modellname mit Fallback auf Standardmodell
        self.model = self.ollama_settings.get("ollama_model", "llama3.2:3b-instruct-q4_K_M")
        # Erstelle einen asynchronen Client für die Kommunikation mit Ollama
        self.client = AsyncClient(host=self.host)
        # Setze den System-Prompt für Kontext
        self.system_prompt = system_prompt

    async def query(self, prompt, system_context=None, temperature=0.1):
        """
        Sende eine Anfrage an das Ollama-Modell und erhalte eine Antwort.

        Args:
            prompt (str): Die Anfrage des Benutzers
            system_context (str, optional): Systemanweisungen für das Modell
            temperature (float, optional): Kreativitätsparameter (0.0-1.0)

        Returns:
            str: Die Antwort des Modells
        """
        try:
            # Bereite die Nachrichtenstruktur vor
            messages = [{"role": "system", "content": self.system_prompt}]

            # Füge Systemnachricht hinzu, falls vorhanden
            if system_context:
                messages.append({"role": "system", "content": f"{system_context}"})

            # Füge Benutzernachricht hinzu
            messages.append({"role": "user", "content": prompt})

            # Erhalte Antwort vom Modell
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options={"temperature": temperature}
            )

            # Extrahiere die Nachricht des Modells
            if response and "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            else:
                return "Keine verwertbare Antwort erhalten."

        except Exception as e:
            # Gib Fehlermeldung zurück, falls ein Problem auftritt
            ic()
            ic(e)
            return f"Fehler bei der Kommunikation mit Ollama: {str(e)}"
