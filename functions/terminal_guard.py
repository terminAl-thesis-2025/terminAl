# Standard Bibliotheken
import asyncio
import os

# Externe Bibliotheken
from icecream import ic
from transformers import pipeline
from dotenv import load_dotenv

# Umgebungsvariablen aus .env Datei laden
load_dotenv()

class TerminAlGuard:
    """
    A wrapper around your DeBERTa classifier that checks
    the model’s own risk_level prediction against the one
    returned by Ollama, and prints a warning if they differ.
    """

    def __init__(
        self,
        model_name: str = "terminAl-thesis-2025/deberta-v3-base-terminAl-guard"
    ):
        token = os.getenv("HF_TOKEN")
        # load a sync text-classification pipeline

        from huggingface_hub import login
        token = os.getenv("HF_TOKEN")
        if token:
            login(token)

        self.classifier = pipeline(
            "text-classification",
            model=model_name,
            tokenizer=model_name,
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
