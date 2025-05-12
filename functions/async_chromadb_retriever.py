# Standardbibliotheken
import ast
import json
import os
from typing import List, Union

# Externe Bibliotheken
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from icecream import ic
import torch

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv("./.env")
terminal_path = os.getenv("TERMINAL_PATH")


class AsyncChromaDBRetriever:
    """
    Eine Klasse zur asynchronen Abfrage einer ChromaDB-Datenbank mit semantischen Embeddings.
    Ermöglicht semantische Suche und Volltextsuche in gespeicherten Dokumenten.
    """

    def __init__(self):
        """
        Initialisiert den Retriever mit Einstellungen aus der Konfigurationsdatei.
        Richtet die Embedding-Funktion mit einem multilingualen Modell ein.
        """
        # Lade Einstellungen aus der Konfigurationsdatei
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
        self.chroma_settings = self.settings.get("chroma_settings", {})

        # Stelle das Gerät ein (CUDA wenn verfügbar, sonst CPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Erstelle die Embedding-Funktion mit einem multilingualen Modell
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.chroma_settings.get("model_name", "intfloat/multilingual-e5-small"),
            cache_folder=terminal_path + self.settings["model_cache_directory"],
            device=self.device,
        )

        # Hinweis: ChromaDB-Client wird in den Methoden erstellt, nicht hier in __init__,
        # um immer den aktuellen Client zu erhalten

    async def retrieve(self, user_input: str, top_k=2, threshold=0.3):
        """
        Führt eine semantische Suche in der Datenbank durch, basierend auf der Benutzereingabe.

        Args:
            user_input: Der Eingabetext des Benutzers
            top_k: Anzahl der zurückzugebenden Ergebnisse
            threshold: Schwellenwert für die Relevanz (aktuell nicht verwendet)

        Returns:
            Formatierter Text mit den gefundenen Dokumenten oder eine Fehlermeldung

        ! Wichtig: Diese Funktion wird im aktuellen Proof of Concept aufgrund der unzureichenden Qualität
        des Retrievals des Embedding-Modells nicht verwendet. Größere Embedding-Modelle bringen für diesen
        Use Case etwas bessere Qualität, rechtfertigen aber die Systembelastung (VRAM) nicht. Es sollte ein
        Embedding-Modell für diesen Use Case finetuned werden, damit ausreichende Qualität mit vertretbarer
        Systembelastung erreicht wird.
        """
        # Erstelle den ChromaDB-Client (nicht in __init__, da bei Updates der Client aktualisiert wird)
        client = chromadb.PersistentClient(
            path=terminal_path + self.chroma_settings["chromadb_path"],
            settings=Settings(anonymized_telemetry=False)
        )

        # Verbinde mit Main Collection
        collection_name = "Main_Collection"
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            ic()
            ic(e)
            collection = None

        if not collection:
            return "Keine Verbindung zur Datenbank."

        try:
            # Abfrage der Sammlung mit dem semantischen Embedding des Benutzertexts
            results = collection.query(
                query_texts=[user_input],
                n_results=top_k,
                include=["documents", "metadatas"],
            )

            # Überprüfe, ob Ergebnisse vorhanden sind
            if not results or not results.get("documents") or not any(results["documents"]):
                return "Keine relevanten Informationen gefunden."

            # Formatiere die Ergebnisse, wenn vorhanden
            if results.get("documents") and results.get("ids"):
                formatted_context = ""
                for doc_list, id_list in zip(results["documents"], results["ids"]):
                    for doc, id_ in zip(doc_list, id_list):
                        formatted_context += f"ID: {id_}\nInhalt: {doc}\n\n"
                return formatted_context if formatted_context else "Keine relevanten Informationen gefunden."
            else:
                return "Keine relevanten Informationen gefunden."

        except Exception as e:
            return f"Fehler bei der Abfrage der ChromaDB: {str(e)}"

    async def fulltext_search(self, keywords: Union[str, List[str]], top_k: int = 5):
        """
        Führt eine Volltextsuche in der Datenbank durch, basierend auf Schlüsselwörtern.

        Args:
            keywords: Ein Schlüsselwort oder eine Liste von Schlüsselwörtern
            top_k: Anzahl der zurückzugebenden Ergebnisse

        Returns:
            Formatierter Text mit den gefundenen Dokumenten
        """
        # Erstelle den ChromaDB-Client (nicht in __init__, da bei Updates der Client aktualisiert wird)
        client = chromadb.PersistentClient(
            path=terminal_path + self.chroma_settings["chromadb_path"],
            settings=Settings(anonymized_telemetry=False)
        )

        # Verbinde mit der Hauptsammlung
        collection_name = "Main_Collection"
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            ic()
            ic(e)
            collection = None

        if not collection:
            return "Keine Verbindung zur Datenbank."

        # Konvertiere einzelnes Schlüsselwort zu Liste, wenn nötig
        if isinstance(keywords, str):
            keywords = [keywords]

        # Bereinige die Schlüsselwörter: zu Kleinbuchstaben konvertieren und leere entfernen
        keywords = [kw.lower() for kw in keywords if kw.strip()]

        if not keywords:
            return "Bitte gib mindestens ein Suchwort an."

        try:
            # Je nach Anzahl der Keywords und Abfrageart unterschiedliche Bedingungen bauen
            if len(keywords) == 1:
                # Bei einem Schlüsselwort: einfacher Textvergleich
                where_document = {"$contains": keywords[0]}
            elif len(keywords) > 1:
                # Bei mehreren Schlüsselwörtern: OR-Verknüpfung
                where_document = {"$or": [{"$contains": kw} for kw in keywords]}

            # Abfrage der Sammlung mit Metadatensuche
            results = collection.query(
                query_texts="",
                where_document=where_document,
                where={"item": {"$in": keywords}},
                n_results=top_k,
                include=["documents", "metadatas"]
            )

            if not results:
                print("Results query (without filters)")

                # Abfrage der Sammlung ohne Metadatensuche, falls mit Metadatensuche keine Resultate gefunden wurden
                results = collection.query(
                    query_texts="",
                    where_document=where_document,
                    n_results=top_k,
                    include=["documents", "metadatas"]
                )

            # Formatiere die Ergebnisse als Text
            formatted_text = self._format_context(results)

            # Zeige formatierte Ergebnisse direkt an
            self._format_search_results(formatted_text)

            # Für die Verwendung durch das LLM (wenn Funktionsabruf über die Query-Funktion)
            return formatted_text

        except Exception as e:
            ic()
            ic(e)
            return f"Fehler bei der Volltextsuche: {str(e)}"

    def _format_context(self, results):
        """
        Hilfsmethode zum Formatieren der Abfrageergebnisse.

        Args:
            results: Die Abfrageergebnisse von ChromaDB

        Returns:
            Formatierter Text mit den gefundenen Dokumenten
        """
        context_text = ""
        if results and results.get("documents"):
            for doc_list, id_list in zip(results["documents"], results["ids"]):
                for doc, id_ in zip(doc_list, id_list):
                    context_text += f"ID: {id_}\nInhalt: {doc}\n\n"

        return context_text if context_text else "Keine relevanten Informationen gefunden."


    def _format_search_results(self, results_text: str):
        """
        Verarbeitet und zeigt die Suchergebnisse aus ChromaDB an,
        ohne die IDs anzuzeigen. Bei Listen werden die einzelnen Elemente separat angezeigt.

        Args:
            results_text: Formatierter Text aus ChromaDB
        """
        ic()
        ic(results_text)

        for block in results_text.strip().split("\n\n"):
            lines = block.splitlines()
            content_line = None

            # Extrahiere nur den Inhalt aus dem Block (ID wird ignoriert)
            for line in lines:
                if line.startswith("Inhalt: "):
                    content_line = line.replace("Inhalt: ", "").strip()

            if content_line:
                # Versuche, den Inhalt zu parsen (für Listen)
                try:
                    parsed_content = ast.literal_eval(content_line)
                    if isinstance(parsed_content, list):
                        # Zeige Listenelemente einzeln an
                        for item in parsed_content:
                            print(f" - {item}")
                    else:
                        # Normaler Inhalt
                        print(parsed_content)
                except Exception:
                    # Wenn Parsing fehlschlägt, zeige Rohtext an
                    print(content_line)

                print()  # Füge eine Leerzeile zur Trennung hinzu