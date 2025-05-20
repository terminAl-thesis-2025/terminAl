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
    A wrapper around your DeBERTa classifier that checks
    the model’s own risk_level prediction against the one
    returned by Ollama, and prints a warning if they differ.
    """

    def __init__(self):
        # load a sync text-classification pipeline
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
        Classify `command`, compare to Ollama’s reported risk (“low”/“medium”/“high”),
        and print a warning if they don’t match.
        """
        loop = asyncio.get_event_loop()

        def _classify():
            out = self.classifier(command)[0]
            # assumes your model’s label mapping yields exactly "low"/"medium"/"high"
            return out["label"].lower()

        # run the blocking pipeline in the default executor
        predicted = await loop.run_in_executor(None, _classify)

        if predicted != reported_risk.lower():
            print(
                f"⚠️ Warnung: Guard prognostiziert “{predicted}”, "
                f"Modell meldet aber “{reported_risk}”."
            )
        return predicted
