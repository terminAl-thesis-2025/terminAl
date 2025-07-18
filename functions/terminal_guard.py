# Standard Bibliotheken
import asyncio
import json
import os

# Externe Bibliotheken
from icecream import ic
from transformers import pipeline
from dotenv import load_dotenv
from huggingface_hub import login
# Umgebungsvariablen aus .env Datei laden
load_dotenv()
# Hole den Pfad zur Terminal-Anwendung aus den Umgebungsvariablen
terminal_path = os.getenv("TERMINAL_PATH")

class TerminAlGuard:
    """
    Eine Wrapper-Klasse um den DeBERTa-Klassifizierer, die die eigene
    Risikoeinschätzung des Modells gegen die von Ollama zurückgegebene
    überprüft und eine Warnung ausgibt, falls diese voneinander abweichen.
    """

    def __init__(self):
        # Lade eine synchrone Text-Klassifizierungs-Pipeline
        token = os.getenv("HF_TOKEN")
        if token:
            login(token)

        self.settings = json.load(
            open(terminal_path + "settings/settings.json"))  # Lädt Einstellungen aus der JSON-Datei
        self.guard_settings = self.settings.get("guard_settings", None)

        self.classifier = pipeline(
            "text-classification",
            model=self.guard_settings.get("guard_model", "terminAl-thesis-2025/deberta-v3-base-terminAl-guard"),
            tokenizer=self.guard_settings.get("guard_model", "terminAl-thesis-2025/deberta-v3-base-terminAl-guard"),
            truncation=True,
            max_length=512,
            return_all_scores=False,
        )

    async def check(self, command: str, reported_risk: str):
        """
        Klassifiziert den `command`, vergleicht ihn mit Ollamas gemeldeter Risikoeinschätzung
        ("low"/"medium"/"high") und gibt eine Warnung aus, falls diese nicht übereinstimmen.
        """
        loop = asyncio.get_event_loop()

        def _classify():
            out = self.classifier(command)[0]
            # Nimmt an, dass das Modell-Label-Mapping exakt "low"/"medium"/"high" zurückgibt
            return out["label"].lower()

        # Führe die blockierende Pipeline im Standard-Executor aus
        predicted = await loop.run_in_executor(None, _classify)

        if predicted != reported_risk.lower():
            print(
                f"⚠️ Warnung: Guard prognostiziert “{predicted}”, "
                f"Modell meldet aber “{reported_risk}”."
            )
        return predicted
