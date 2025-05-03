import ast, json, os
from enum import nonmember

import torch
import chromadb
import nltk
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from icecream import ic
from typing import List, Union
from dotenv import load_dotenv

try:
    from nltk.corpus import stopwords
    stopwords.words("german")  # Try to access it
except LookupError:
    import nltk
    nltk.download('stopwords')
    from nltk.corpus import stopwords  # Re-import after download
    stopwords.words("german")  # Now this should work


load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class AsyncChromaDBRetriever:
    def __init__(self):
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
        self.chroma_settings = self.settings.get("chroma_settings", {})

        # Set up device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Set up embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="intfloat/multilingual-e5-small",
            cache_folder=self.settings["model_cache_directory"],
            device=self.device,
        )

        # ChromaDB Client Set up moved functions, to get current Client!

    async def retrieve(self, user_input: str, top_k=2, threshold=0.3):

        # Set up ChromaDB client (not in def __init__() because updating changes the client!
        client = chromadb.PersistentClient(
            path=self.chroma_settings["chromadb_path"],
            settings=Settings(anonymized_telemetry=False)
        )

        # Connect to the Main_Collection
        collection_name = "Main_Collection"
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            collection = None

        if not collection:
            return "Keine Verbindung zur Datenbank."

        try:
            # Query the collection
            results = collection.query(
                query_texts=[user_input],
                n_results=top_k,
                include=["documents", "metadatas"],
            )

            ic()
            ic(results)

            if not results or not results.get("documents") or not any(results["documents"]):
                return "Keine relevanten Informationen gefunden."

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

    async def fulltext_search(self, keywords: Union[str, List[str]], top_k: int = 5, query=False):

        # Set up ChromaDB client (not in def __init__() because updating changes the client!
        client = chromadb.PersistentClient(
            path=self.chroma_settings["chromadb_path"],
            settings=Settings(anonymized_telemetry=False)
        )

        # Connect to the Main_Collection
        collection_name = "Main_Collection"
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            collection = None

        if not collection:
            return "Keine Verbindung zur Datenbank."

        if isinstance(keywords, str):
            keywords = [keywords]

        keywords = [kw.lower() for kw in keywords if kw.strip()]  # Leere Strings entfernen
        # Filter Natural Language Query only
        if query:
            keywords = [kw for kw in keywords if kw not in stopwords.words("german")]

        if not keywords:
            return "Bitte gib mindestens ein Suchwort an."

        ic()
        ic(keywords)

        try:
            # Je nach Anzahl der Keywords unterschiedlich bauen
            if len(keywords) == 1:
                where_document = {"$contains": keywords[0]}
            elif len(keywords) > 1 and query:
                where_document = {"$or": [{"$contains": kw} for kw in keywords]}
            elif len(keywords) > 1 and not query:
                where_document = {"$and": [{"$contains": kw} for kw in keywords]}

            ic()
            ic(where_document)

            results = collection.query(
                query_texts="",
                where_document=where_document,
                n_results=top_k,
                include=["documents", "metadatas"]
            )

            # 1. Format to string
            formatted_text = self._format_context(results)

            if query:
                return formatted_text
            else:
                # 2. Parse and print nicely
                _format_search_results(formatted_text)
                return None
            return None

        except Exception as e:
            return f"Fehler bei der Volltextsuche: {str(e)}"

    def _format_context(self, results):
        context_text = ""
        if results and results.get("documents"):
            for doc_list, id_list in zip(results["documents"], results["ids"]):
                for doc, id_ in zip(doc_list, id_list):
                    context_text += f"ID: {id_}\nInhalt: {doc}\n\n"

        return context_text if context_text else "Keine relevanten Informationen gefunden."

def _format_search_results(results_text: str):
    """
    Parses the search results text from ChromaDB and prints each list item individually,
    or prints the content directly if it's not a list.
    """
    for block in results_text.strip().split("\n\n"):
        lines = block.splitlines()
        id_line = None
        content_line = None

        for line in lines:
            if line.startswith("ID: "):
                id_line = line
            elif line.startswith("Inhalt: "):
                content_line = line.replace("Inhalt: ", "").strip()

        if id_line and content_line:
            print(id_line)

            # Try to parse content
            try:
                parsed_content = ast.literal_eval(content_line)
                if isinstance(parsed_content, list):
                    for item in parsed_content:
                        print(f" - {item}")
                else:
                    print(parsed_content)
            except Exception:
                # If parsing fails, just print raw
                print(content_line)

            print()  # Add a newline for separation
