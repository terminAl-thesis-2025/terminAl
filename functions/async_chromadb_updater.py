import asyncio, datetime, json, os, shutil, time
import sqlite3

import chromadb
from tqdm import tqdm as tqdm_func
import torch
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from icecream import ic

from functions.system_mapping import SystemMapping
# from functions.chromadb_client import ChromaDB
from dotenv import load_dotenv

load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class AsyncChromaDBUpdater:
    """
    Verwaltet asynchrone Updates für ChromaDB in einem Linux-Agent-System,
    das regelmäßige Aktualisierungen der Verzeichnisstruktur erfordert.
    Koordiniert mit den bestehenden SystemMapping und ChromaDB Klassen.
    """

    def __init__(self):
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
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
            batch_size = 5000 # Small batch size to prevent RAM and VRAM overload
            psql_result_len = len(psql_results)

            # Track UUIDs to keep
            uuids_to_keep = set()

            # Create temporary collection and track its UUID
            temp_collection = self.client.create_collection(temp_coll_name)
            uuids_to_keep.add(str(temp_collection.id))

            # Add collection_metadata UUID to keep list
            try:
                metadata_collection = self.client.get_collection("collection_metadata")
                uuids_to_keep.add(str(metadata_collection.id))
            except Exception:
                # collection_metadata might not exist yet
                pass

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

            ic()
            ic(f"Temp Collection before Deleting Main Collection: {temp_collection.name, temp_collection.id}")
            ic(f"UUIDs to keep: {uuids_to_keep}")

            # Delete Main_Collection if it exists
            try:
                main_collection = self.client.get_collection("Main_Collection")
                ic(f"Main Collection before Deleting Main Collection: {main_collection.name, main_collection.id}")
                self.client.delete_collection("Main_Collection")
            except Exception as e:
                ic()
                ic(e)

            try:
                check_main_coll2 = self.client.get_collection("Main_Collection")
            except Exception as e:
                ic()
                ic(e)
            try:
                check_temp_coll2 = self.client.get_collection(temp_coll_name)
            except Exception as e:
                ic()
                ic(e)

            ic()
            try:
                ic(f"Main Collection after Deleting Main Collection: {check_main_coll2.name, check_main_coll2.id}")
            except Exception as e:
                ic()
                ic(e)

            try:
                ic(f"Temp Collection after Deleting Main Collection: {check_temp_coll2.name, check_temp_coll2.id}")
            except Exception as e:
                ic()
                ic(e)

            # Rename temp collection to Main_Collection
            temp_collection_to_update = self.client.get_collection(temp_coll_name)
            temp_collection_to_update.modify(name="Main_Collection")

            try:
                check_main_coll1 = self.client.get_collection("Main_Collection")
            except Exception as e:
                ic()
                ic(e)
            try:
                check_temp_coll1 = self.client.get_collection(temp_coll_name)
            except Exception as e:
                ic()
                ic(e)

            ic()
            try:
                ic(f"Temp Collection after renaming Temp Collection: {check_temp_coll1.name, check_temp_coll1.id}")
            except Exception as e:
                ic()
                ic(e)

            try:
                ic(f"Main Collection after renaming Temp Collection: {check_main_coll1.name, check_main_coll1.id}")
            except Exception as e:
                ic()
                ic(e)

            # TODO Remove
            # Add collection_metadata UUID to keep list
            try:
                metadata_collection = self.client.get_collection("collection_metadata")
                uuids_to_keep.add(str(metadata_collection.id))
            except Exception:
                # collection_metadata might not exist yet
                pass

            # Do cleanup with our uuids_to_keep list
            self._clean_up(uuids_to_keep)

            self._update_update_time()
            self.is_updating = False

            end_time = time.time()
            time_elapsed = end_time - start_time
            print(f"Time taken for updating ChromaDB: {time_elapsed/60} minutes")

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
        now = datetime.datetime.now()
        formatted_now = now.strftime("%d.%m.%Y %H:%M:%S")
        self.chroma_latest_update = formatted_now
        self.settings["chroma_settings"]["chroma_latest_update"] = self.chroma_latest_update
        # Save the updated settings file
        with open("./settings/settings.json", "w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    def _chunked(self, iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    def list_collections(self):
        # List collections using ChromaDB client
        print("\n=== Collections via ChromaDB Client ===")
        collections = self.client.list_collections()
        for collection in collections:
            retrieved_coll = self.client.get_collection(collection)
            print(f"Collection: {retrieved_coll.name} --> {retrieved_coll.id}")

        # Now also directly read from the database
        db_path = os.path.join(self.chromadb_path, "chroma.sqlite3")

        if not os.path.exists(db_path):
            print("\nSQLite database not found.")
            return

        print("\n=== Collections via SQLite Database ===")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, uuid FROM collections;")
            rows = cursor.fetchall()

            for row in rows:
                name, uuid = row
                print(f"DB Collection: {name} --> {uuid}")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error reading database: {e}")

    def _clean_up(self, uuids_to_keep=None):
        """
        Bereinigt den ChromaDB-Speicher:
        - Behalte maximal die 15 neuesten Ordner (basierend auf Änderungszeit).
        - Löscht alle älteren Ordner.
        - Führt VACUUM auf der chroma.sqlite3-Datenbank durch.
        """
        if not os.path.exists(self.chromadb_path):
            print(f"Pfad {self.chromadb_path} existiert nicht. Cleanup übersprungen.")
            return

        all_entries = os.listdir(self.chromadb_path)
        print(f"All entries: {all_entries}")

        # Nur echte Ordner (keine Dateien) auflisten
        all_folders = [
            entry for entry in all_entries
            if os.path.isdir(os.path.join(self.chromadb_path, entry))
        ]
        print(f"Detected folders: {all_folders}")

        folder_paths = [os.path.join(self.chromadb_path, folder) for folder in all_folders]

        # Änderungszeit für alle Ordner holen
        folder_paths_with_mtime = [
            (path, os.path.getmtime(path)) for path in folder_paths
        ]

        # Sortieren nach Änderungszeit (neueste zuerst)
        folder_paths_with_mtime.sort(key=lambda x: x[1], reverse=True)

        # Ordner aufteilen: neueste 15 behalten, Rest löschen
        folders_to_keep = folder_paths_with_mtime[:15]
        folders_to_delete = folder_paths_with_mtime[15:]

        # Löschen der alten Ordner
        for path, mtime in folders_to_delete:
            try:
                shutil.rmtree(path)
                print(f"Gelöscht (älter als Top-15): {path} (Letzte Änderung: {time.ctime(mtime)})")
            except Exception as e:
                print(f"Fehler beim Löschen von {path}: {e}")

        if not folders_to_delete:
            print("Weniger als 15 Ordner vorhanden oder keine alten Ordner zum Löschen.")

        # VACUUM auf der SQLite-Datenbank
        db_path = os.path.join(self.chromadb_path, "chroma.sqlite3")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM;")
                conn.close()
                print("VACUUM auf chroma.sqlite3 erfolgreich abgeschlossen.")
            except Exception as e:
                print(f"Fehler beim VACUUM der Datenbank: {e}")
