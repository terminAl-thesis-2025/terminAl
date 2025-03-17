import asyncio
import json
import os
import time
import threading
from datetime import datetime

import chromadb
from tqdm import tqdm as tqdm_func
import torch
from chromadb.utils import embedding_functions
from icecream import ic

from functions.system_mapping import SystemMapping
from functions.chromadb_client import ChromaDB


class AsyncChromaDBUpdater:
    """
    Verwaltet asynchrone Updates für ChromaDB in einem Linux-Agent-System,
    das regelmäßige Aktualisierungen der Verzeichnisstruktur erfordert.
    Koordiniert mit den bestehenden SystemMapping und ChromaDB Klassen.
    """

    def __init__(self, settings_path="./settings/settings.json"):
        self.settings = json.load(open(settings_path))
        self.update_interval = self.settings.get("chroma_update_interval", 600)  # Standard: 10 Minuten
        self.auto_update = self.settings.get("chroma_auto_update", False)  # Standard: Automatisches Update aktiviert
        self.is_updating = False
        self.update_lock = threading.Lock()

        # ChromaDB-Einstellungen initialisieren
        self.chroma_collection = self.settings.get("chromadb_tree_collection", "tree_collection")

        # Temp-Verzeichnis für temporäre Collections
        os.makedirs(os.path.join(self.settings["chromadb_path"], "temp"), exist_ok=True)

    async def start_update_cycle(self):
        """
        Startet den periodischen Update-Zyklus als Hintergrundaufgabe
        """
        while True:
            # Nur updaten, wenn auto_update aktiviert ist
            if self.auto_update:
                await self.update_system_mapping()
            else:
                #TODO
                pass

            # Auf den nächsten Update-Zyklus warten
            await asyncio.sleep(self.update_interval)

    async def update_system_mapping(self):
        """
        Aktualisiert das System-Mapping in ChromaDB ohne Blockierung von Abfrage-Operationen
        """
        if self.is_updating:
            return {"success": False, "message": "Ein Update-Prozess läuft bereits."}

        with self.update_lock:
            self.is_updating = True

            try:
                # Generate a unique timestamp-based name for the new collection
                new_collection_name = f"temp_{int(time.time())}"

                # Get the current collection name from settings
                current_collection_name = self.settings.get("current_collection_name", self.chroma_collection)

                # System-Mapping in einem separaten Thread ausführen
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, self._execute_system_mapping, new_collection_name)

                if not success:
                    self.is_updating = False
                    return {"success": False, "message": "System-Mapping konnte nicht aktualisiert werden."}

                print("system-mapping-success")

                # Update collection pointer in metadata collection
                pointer_updated = self.update_collection_pointer(self.chroma_collection, new_collection_name)
                if not pointer_updated:
                    self.is_updating = False
                    # Clean up the just-created collection that won't be used
                    try:
                        await loop.run_in_executor(None,
                                                   lambda: ChromaDB.client.delete_collection(name=new_collection_name))
                    except:
                        pass
                    return {"success": False, "message": "Collection-Zeiger konnte nicht aktualisiert werden."}

                print("update-collection-success")

                # Update settings with new collection name
                self.settings["current_collection_name"] = new_collection_name

                # Remove old collection if different from the new one
                # Remove old collection if different from the new one
                if current_collection_name and current_collection_name != new_collection_name:
                    try:
                        await loop.run_in_executor(
                            None,
                            lambda: ChromaDB.client.delete_collection(name=current_collection_name)
                        )
                        print(f"Alte Collection '{current_collection_name}' wurde entfernt.")
                    except Exception as e:
                        print(f"Warnung: Konnte alte Collection nicht entfernen: {str(e)}")
                # Update timestamp
                current_time = int(time.time())
                formatted_time = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S")
                self.settings["chroma_latest_update"] = formatted_time
                print("chroma-latest-update")

                # Settings speichern
                with open("./settings/settings.json", 'w') as file:
                    json.dump(self.settings, file, indent=2)
                print("chroma-latest-update-success als json")

                return {"success": True, "message": f"Update abgeschlossen um {formatted_time}"}

            except Exception as e:
                return {"success": False, "message": f"Fehler: {str(e)}"}
            finally:
                self.is_updating = False

    def _execute_system_mapping(self, temp_collection_name):
        """
        Führt das System-Mapping mit bestehenden Klassen aus
        """
        try:
            # SystemMapping verwenden, um Daten zu erhalten
            # Anstatt direkt in die Standard-Collection zu schreiben,
            # leiten wir die Daten in die temporäre Collection um

            # Prozess simulieren - dies würde durch Ihre existierende Logik ersetzt
            # Verwenden Sie ggf. SystemMapping.process_system_mapping für Daten
            tree_data = SystemMapping.process_system_mapping()

            if not tree_data:
                return False

            # Daten für die Collection vorbereiten
            documents = []
            ids = []

            for path, directory in tree_data.items():
                documents.append(str(directory))
                ids.append(path)

            # Eigene Collection-Erstellung anstelle von replace_data
            # verwenden, um die bestehenden Collections nicht zu beeinträchtigen
            device = "cuda" if torch.cuda.is_available() else "cpu"
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="intfloat/multilingual-e5-large",
                cache_folder=self.settings["model_cache_directory"],
                device=device,
            )

            client = chromadb.PersistentClient(path=self.settings["chromadb_path"])

            # Sicherstellen, dass die temporäre Collection nicht existiert
            try:
                client.delete_collection(name=temp_collection_name)
            except:
                pass

            # Collection erstellen und Daten hinzufügen
            temp_collection = client.create_collection(
                name=temp_collection_name,
                embedding_function=embedding_function
            )

            # Dokumente in Batches hinzufügen
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                temp_collection.add(
                    documents=documents[i:end_idx],
                    ids=ids[i:end_idx]
                )

            return True

        except Exception as e:
            # TODO add logging
            return False

    def update_collection_pointer(self, base_collection_name, current_collection_name):
        """
        Aktualisiert den Zeiger auf die aktuell aktive Collection
        """
        try:
            # Use the ChromaDB client
            client = ChromaDB.client

            # EXPLICITLY create the embedding function to ensure the correct model
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="intfloat/multilingual-e5-large",  # Explicitly use the correct model
                cache_folder=self.settings["model_cache_directory"],
                device="cuda" if torch.cuda.is_available() else "cpu",
            )

            # Always delete the metadata collection first to ensure correct embedding function
            try:
                client.delete_collection(name="collection_metadata")
            except:
                pass

            # Create a fresh metadata collection with the correct embedding function
            metadata_collection = client.create_collection(
                name="collection_metadata",
                embedding_function=embedding_function
            )

            # Update the pointer
            metadata_collection.upsert(
                ids=[base_collection_name],
                documents=[current_collection_name],
                metadatas=[{"updated_at": int(time.time())}]
            )

            print(f"Collection-Zeiger aktualisiert: {base_collection_name} -> {current_collection_name}")
            return True

        except Exception as e:
            print(f"Fehler bei der Aktualisierung des Collection-Zeigers: {str(e)}")
            return False

    async def retrieve(self, query, n_results=5, filter_condition=None):
        """
        Thread-sichere Abfrage, die die aktuell aktive Collection verwendet
        """
        try:
            # Get the current collection name from settings
            current_collection_name = self.settings.get("current_collection_name", self.chroma_collection)

            # Run database operations in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: ChromaDB.retrieve(current_collection_name, query, n_results, filter_condition)
            )
            return results
        except Exception as e:
            # Fallback to base collection if there's an error
            try:
                loop = asyncio.get_event_loop()
                fallback_results = await loop.run_in_executor(
                    None,
                    lambda: ChromaDB.retrieve(self.chroma_collection, query, n_results, filter_condition)
                )
                return fallback_results
            except:
                return {"documents": [], "distances": [], "ids": []}

    def _sync_retrieve(self, base_collection_name, query, n_results, filter_condition):
        # Aktuellen Collection-Namen aus den Metadaten abrufen
        base_collection_name = self.chroma_collection

        try:
            # Aktuellen Collection-Zeiger abrufen
            device = "cuda" if torch.cuda.is_available() else "cpu"
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="intfloat/multilingual-e5-large",
                cache_folder=self.settings["model_cache_directory"],
                device=device,
            )

            client = chromadb.PersistentClient(path=self.settings["chromadb_path"])

            try:
                metadata_collection = client.get_collection(
                    name="collection_metadata",
                    embedding_function=embedding_function
                )

                results = metadata_collection.get(ids=[base_collection_name])

                if results and results["documents"]:
                    current_collection_name = results["documents"][0]
                else:
                    current_collection_name = base_collection_name
            except:
                current_collection_name = base_collection_name

            # Bestehende ChromaDB-Klasse für die Abfrage verwenden
            return ChromaDB.retrieve(current_collection_name, query, n_results, filter_condition)

        except Exception as e:
            # Fallback zur Basis-Collection
            try:
                return ChromaDB.retrieve(base_collection_name, query, n_results, filter_condition)
            except Exception as e2:
                # TODO add logging
                return {"documents": [], "distances": [], "ids": []}

    async def auto_update_on(self):
        self.auto_update = True
        self.settings["chroma_auto_update"] = True
        # Save settings
        with open("./settings/settings.json", 'w') as file:
            json.dump(self.settings, file, indent=2)

    async def auto_update_off(self):
        self.auto_update = False
        self.settings["chroma_auto_update"] = False
        # Save settings
        with open("./settings/settings.json", 'w') as file:
            json.dump(self.settings, file, indent=2)
