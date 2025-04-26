import asyncio
import json
import os
import time
import threading
import sqlite3
import shutil

import datetime

import chromadb
from tqdm import tqdm as tqdm_func
import torch
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from icecream import ic

from functions.system_mapping import SystemMapping
# from functions.chromadb_client import ChromaDB


class AsyncChromaDBUpdater:
    """
    Verwaltet asynchrone Updates für ChromaDB in einem Linux-Agent-System,
    das regelmäßige Aktualisierungen der Verzeichnisstruktur erfordert.
    Koordiniert mit den bestehenden SystemMapping und ChromaDB Klassen.
    """

    def __init__(self, settings_path="./settings/settings.json"):
        self.settings = json.load(open(settings_path))
        self.chroma_settings = self.settings.get("chroma_settings", {})
        self.update_interval = self.chroma_settings.get("chroma_update_interval", 600)  # Standard: 10 Minuten
        self.auto_update = self.chroma_settings.get("chroma_auto_update", False)  # Standard: Automatisches Update aktiviert
        self.chromadb_path = self.chroma_settings.get("chromadb_path", None)
        self.chroma_latest_update = self.chroma_settings.get("chroma_latest_update", None)
        self.is_updating = False
        self.update_lock = asyncio.Lock()

        # Set Up ChromaDB Client
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="intfloat/multilingual-e5-small",
            cache_folder=self.settings["model_cache_directory"],
            device=self.device,
        )
        self.client = chromadb.PersistentClient(path=self.chromadb_path,
                                           settings=Settings(anonymized_telemetry=False))

        # ChromaDB-Einstellungen initialisieren
        self.chroma_collection = self.chroma_settings.get("chromadb_tree_collection")

    async def start_update_cycle(self):
        """
        Startet den periodischen Update-Zyklus als Hintergrundaufgabe
        """
        while True:
            # Nur updaten, wenn auto_update aktiviert ist
            if self.auto_update:
                await self.update_system_mapping()

            # Auf den nächsten Update-Zyklus warten
            await asyncio.sleep(self.update_interval)

    async def update_system_mapping(self):
        async with self.update_lock:
            start_time = time.time()

            # Prevent duplicate updates
            self.is_updating = True

            os_results, psql_results = SystemMapping().map_all()
            temp_coll_name = f"temp_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
            uuids_to_remove = []
            batch_size = 5000 # Small batch size to prevent RAM and VRAM overload
            psql_result_len = len(psql_results)

            # Get current Main_Collection ID to Delete HNSW later on
            try:
                main_collection = self.client.get_collection("Main_Collection")
                uuids_to_remove.append(main_collection.id)
            except Exception as e:
                self.client.create_collection(temp_coll_name)
                main_collection = self.client.create_collection("Main_Collection")
                uuids_to_remove.append(main_collection.id)

            # TODO Remove
            self._clean_up(uuids_to_remove)

            temp_collection = self.client.create_collection(temp_coll_name)
    
            temp_collection.add(
                documents=[str(psql_result) for psql_result in psql_results],
                metadatas=[{"tool": "sql"} for i in range(len(psql_results))],
                ids=[str(i) for i in range(len(psql_results))],
            )
    
            documents = [
                str(directory_content) if directory_content else str(directory)
                for directory, directory_content in os_results.items()
            ]
            metadatas = [{"tool": "bash"} for _ in documents]
            # OFFSET the IDs by the number of psql_documents
            ids = [str(i + psql_result_len) for i in range(len(documents))]
    
            for doc_chunk, meta_chunk, id_chunk in zip(
                    self._chunked(documents, batch_size),
                    self._chunked(metadatas, batch_size),
                    self._chunked(ids, batch_size)
            ):
                temp_collection.add(
                    documents=doc_chunk,
                    metadatas=meta_chunk,
                    ids=id_chunk
                )
    
            self.client.delete_collection("Main_Collection")
            temp_collection.modify(name="Main_Collection")
            self._clean_up(uuids_to_remove)

            self._update_update_time()

            self.is_updating = False

            end_time = time.time()
            time_elapsed = end_time - start_time
            print(f"Time taken for updating ChromaDB: {time_elapsed} seconds")

    async def auto_update_on(self):
        self.auto_update = True
        self.settings["chroma_auto_update"] = True
        # Save settings
        with open("./settings/settings.json", 'w', encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    async def auto_update_off(self):
        self.auto_update = False
        self.settings["chroma_auto_update"] = False
        # Save settings
        with open("./settings/settings.json", 'w', encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    def _update_update_time(self):
        self.chroma_latest_update = datetime.datetime.now().isoformat()
        self.settings["chroma_settings"]["chroma_latest_update"] = self.chroma_latest_update
        # Save the updated settings file
        with open("./settings/settings.json", "w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    def _chunked(self, iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    def list_collections(self):
        collections = self.client.list_collections()
        for collection in collections:
            retrieved_coll = self.client.get_collection(collection)
            print(f"Collection: {retrieved_coll.name} --> {retrieved_coll.id}")

    def _clean_up(self, uuids_to_remove):
        collections = self.client.list_collections()

        for col in collections:
            if col.startswith("temp_"):
                # Get full metadata
                collection = self.client.get_collection(name=col)

                # Delete via API
                self.client.delete_collection(collection.name)

                # Delete via shutil
                uuids_to_remove.append(collection.id)

        for uuid in uuids_to_remove:
            # Delete HNSW index folder
            uuid_folder = os.path.join(self.chromadb_path, str(uuid))
            if os.path.exists(uuid_folder):
                shutil.rmtree(uuid_folder)

        # Vacuum the database
        conn = sqlite3.connect(os.path.join(self.chromadb_path, "chroma.sqlite3"))
        conn.execute("VACUUM;")
        conn.close()


