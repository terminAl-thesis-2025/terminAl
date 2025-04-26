import json
import torch
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from icecream import ic
from typing import List, Union



class AsyncChromaDBRetriever:
    def __init__(self):
        self.settings = json.load(open("./settings/settings.json"))
        self.chroma_settings = self.settings.get("chroma_settings", {})

        # Set up device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Set up embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="intfloat/multilingual-e5-small",
            cache_folder=self.settings["model_cache_directory"],
            device=self.device,
        )

        # Set up ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.chroma_settings["chromadb_path"],
            settings=Settings(anonymized_telemetry=False)
        )

        # Connect to the Main_Collection
        self.collection_name = "Main_Collection"
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            self.collection = None

    async def retrieve(self, user_input: str, top_k):
        if not self.collection:
            return "Keine Verbindung zur Datenbank."

        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[user_input],
                n_results=top_k  # Adjust as needed
            )

            # Format results into a text block
            formatted_context = self._format_context(results)

            return formatted_context

        except Exception as e:
            return f"Fehler bei der Abfrage der ChromaDB: {str(e)}"

    async def fulltext_search(self, keywords: Union[str, List[str]], top_k: int = 5):
        if not self.collection:
            return "Keine Verbindung zur Datenbank."

        if isinstance(keywords, str):
            keywords = [keywords]

        keywords = [kw.lower() for kw in keywords if kw.strip()]  # Leere Strings entfernen

        if not keywords:
            return "Bitte gib mindestens ein Suchwort an."

        try:
            # Je nach Anzahl der Keywords unterschiedlich bauen
            if len(keywords) == 1:
                where_document = {"$contains": keywords[0]}
            else:
                where_document = {"$and": [{"$contains": kw} for kw in keywords]}

            results = self.collection.query(
                query_texts=[""],
                n_results=top_k,
                where_document=where_document,
                include=["documents", "metadatas"]
            )

            return self._format_context(results)

        except Exception as e:
            return f"Fehler bei der Volltextsuche: {str(e)}"

    def _format_context(self, results):
        context_text = ""
        if results and results.get("documents"):
            for doc_list, id_list in zip(results["documents"], results["ids"]):
                for doc, id_ in zip(doc_list, id_list):
                    context_text += f"ID: {id_}\nInhalt: {doc}\n\n"

        return context_text if context_text else "Keine relevanten Informationen gefunden."
