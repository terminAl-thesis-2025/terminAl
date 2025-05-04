# Standard Bibliotheken - alphabetisch sortiert
import asyncio
import datetime
import json
import os
import shutil
import sqlite3
import time

# Externe Bibliotheken
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from icecream import ic
import torch

# Interne Module
from functions.system_mapping import SystemMapping

# Umgebungsvariablen laden
load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class AsyncChromaDBUpdater:
    """
    Verwaltet asynchrone Updates für ChromaDB in einem Linux-Agent-System,
    das regelmäßige Aktualisierungen der Verzeichnisstruktur erfordert.
    Koordiniert mit den bestehenden SystemMapping und ChromaDB Klassen.
    """

    def __init__(self):
        """
        Initialisiert den AsyncChromaDBUpdater mit Konfigurationen, ChromaDB-Client
        und erforderlichen Einstellungen für das Embedding-Modell.
        """
        # Einstellungen aus JSON-Datei laden
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
        self.chroma_settings = self.settings.get("chroma_settings", {})

        # Standardkonfigurationen aus den Einstellungen extrahieren oder Standardwerte verwenden
        self.update_interval = self.chroma_settings.get("chroma_update_interval", 600)  # Standard: 10 Minuten
        self.auto_update = self.chroma_settings.get("chroma_auto_update",
                                                    False)  # Standard: Automatisches Update aktiviert
        self.chromadb_path = self.chroma_settings.get("chromadb_path", None)  # Pfad zur ChromaDB
        self.chroma_latest_update = self.chroma_settings.get("chroma_latest_update",
                                                             None)  # Zeitstempel der letzten Aktualisierung

        # Status-Variablen für den Update-Prozess
        self.is_updating = False  # Flag, ob gerade ein Update läuft
        self.update_lock = asyncio.Lock()  # Lock zur Vermeidung paralleler Updates

        # Hardware-Beschleunigung für Embeddings konfigurieren
        self.device = "cuda" if torch.cuda.is_available() else "cpu"  # GPU nutzen, falls verfügbar
        # Embedding-Funktion mit mehrsprachigem Modell initialisieren
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="intfloat/multilingual-e5-small",
            cache_folder=self.settings["model_cache_directory"],
            device=self.device,
        )

        # Name der ChromaDB-Collection aus den Einstellungen extrahieren
        self.chroma_collection = self.chroma_settings.get("chromadb_tree_collection")

    async def start_update_cycle(self):
        """
        Startet den periodischen Update-Zyklus als Hintergrundaufgabe.
        Führt Updates gemäß dem konfigurierten Intervall durch, wenn auto_update aktiviert ist.
        """
        while True:
            # Nur updaten, wenn auto_update aktiviert ist
            if self.auto_update:
                await self.update_system_mapping()  # Führt das eigentliche Update durch

            # Auf den nächsten Update-Zyklus warten (in Sekunden)
            await asyncio.sleep(self.update_interval)

    async def update_system_mapping(self):
        """
        Hauptfunktion zur Aktualisierung der Systemstruktur in ChromaDB.
        Verwendet ein Lock, um Parallelausführungen zu verhindern.
        Erstellt eine temporäre Sammlung, füllt sie mit Daten und benennt sie dann um.
        Somit sollen Zugriffskonflikte verhindert werden, wenn während dem Update ChromaDB abgefragt wird.
        """
        async with self.update_lock:  # Verhindert gleichzeitige Updates
            # TODO Remove Zeitmessung
            start_time = time.time()  # Startzeit für Zeitmessung

            # Erstelle den ChromaDB-Client (nicht in __init__, damit der aktuelle Client geladen wird)
            client = chromadb.PersistentClient(
                path=self.chromadb_path,
                settings=Settings(anonymized_telemetry=False)
            )

            # Status auf 'aktualisierend' setzen
            self.is_updating = True

            # Daten von SystemMapping holen (OS- und PostgreSQL-Informationen)
            os_results, psql_results = SystemMapping().map_all()

            # Temporäre Sammlung mit Zeitstempel erstellen
            temp_coll_name = f"temp_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
            batch_size = 5000  # Große Datenmengen in Batches verarbeiten
            psql_result_len = len(psql_results)  # Anzahl der PostgreSQL-Ergebnisse

            # Set zum Speichern von UUIDs, die beim Aufräumen erhalten bleiben sollen
            uuids_to_keep = set()

            # Temporäre Sammlung erstellen und ihre UUID speichern
            temp_collection = client.create_collection(
                temp_coll_name,
                embedding_function=self.embedding_function
            )
            uuids_to_keep.add(str(temp_collection.id))

            # Collection_metadata UUID der Liste zum Beibehalten hinzufügen
            try:
                metadata_collection = client.get_collection("collection_metadata")
                uuids_to_keep.add(str(metadata_collection.id))
            except Exception:
                # Collection_metadata existiert möglicherweise noch nicht - ignorieren
                pass

            # PostgreSQL-Ergebnisse zur temporären Sammlung hinzufügen
            temp_collection.add(
                documents=[str(psql_result) for psql_result in psql_results],  # Ergebnisse als Strings
                metadatas=[{"tool": "sql"} for _ in range(len(psql_results))],  # Metadaten für jeden Eintrag
                ids=[str(i) for i in range(len(psql_results))],  # Fortlaufende IDs
            )

            # OS-Ergebnisse vorbereiten
            documents = [f"*Dokument: {meta['item']} Pfad: {path}*" for path, meta in
                         os_results.items()]  # Formatierte Dokumente

            # Metadaten für OS-Ergebnisse erstellen
            metadatas = [
                {
                    "tool": "bash",
                    "filetype": meta["filetype"],
                    "item": meta["item"]
                }
                for meta in os_results.values()
            ]

            # IDs für OS-Ergebnisse fortlaufend nach den PostgreSQL-IDs nummerieren
            ids = [str(i + psql_result_len) for i in range(len(documents))]

            # OS-Ergebnisse in Batches zur temporären Sammlung hinzufügen
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

            # Hauptsammlung löschen, falls vorhanden
            try:
                client.delete_collection("Main_Collection")
            except Exception:
                # Hauptsammlung existiert möglicherweise noch nicht - ignorieren
                pass

            # Temporäre Sammlung in Hauptsammlung umbenennen
            temp_collection_to_update = client.get_collection(temp_coll_name)
            temp_collection_to_update.modify(name="Main_Collection")

            # Collection UUIDs erneut zur Liste hinzufügen (zur Sicherheit)
            try:
                metadata_collection = client.get_collection("collection_metadata")
                main_collection = client.get_collection("Main_Collection")
                uuids_to_keep.add(str(metadata_collection.id))
                uuids_to_keep.add(str(main_collection.id))
            except Exception:
                # Falls Collections nicht vorhanden: ignorieren
                pass

            # Alte Sammlungen aufräumen und nur die relevanten behalten
            self._clean_up()

            # Zeitstempel der letzten Aktualisierung speichern
            self._update_update_time()
            # Update-Status zurücksetzen
            self.is_updating = False

            # Zeitmessung abschließen und Dauer ausgeben
            end_time = time.time()
            time_elapsed = end_time - start_time
            # TODO remove Zeitmessung
            print(f"Zeit für die Aktualisierung von ChromaDB: {time_elapsed / 60} Minuten")

    async def auto_update_on(self):
        """
        Aktiviert die automatischen Updates und speichert die Einstellung.
        """
        self.auto_update = True
        self.settings["chroma_auto_update"] = True
        # Aktualisierte Einstellungen in die JSON-Datei schreiben
        with open("./settings/settings.json", 'w', encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    async def auto_update_off(self):
        """
        Deaktiviert die automatischen Updates und speichert die Einstellung.
        """
        self.auto_update = False
        self.settings["chroma_auto_update"] = False
        # Aktualisierte Einstellungen in die JSON-Datei schreiben
        with open("./settings/settings.json", 'w', encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    def _update_update_time(self):
        """
        Aktualisiert den Zeitstempel der letzten Aktualisierung in den Einstellungen.
        """
        now = datetime.datetime.now()  # Aktuelles Datum und Uhrzeit
        formatted_now = now.strftime("%d.%m.%Y %H:%M:%S")  # In lesbares Format formatieren
        self.chroma_latest_update = formatted_now
        self.settings["chroma_settings"]["chroma_latest_update"] = self.chroma_latest_update
        # Aktualisierte Einstellungen in die JSON-Datei schreiben
        with open("./settings/settings.json", "w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2)

    def _chunked(self, iterable, size):
        """
        Hilfsfunktion zum Aufteilen einer Liste in Teile der angegebenen Größe.
        Wird verwendet, um große Datenmengen in verarbeitbare Batches aufzuteilen.

        Args:
            iterable: Die aufzuteilende Liste
            size: Die Größe jedes Teils

        Returns:
            Generator, der Teile der angegebenen Größe zurückgibt
        """
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    def list_collections(self):
        """
        Listet alle Sammlungen in der ChromaDB auf, sowohl über den ChromaDB-Client als auch
        direkt aus der SQLite-Datenbank, um Konsistenz zu überprüfen.
        """
        # Erstelle den ChromaDB-Client (nicht in __init__, damit der aktuelle Client geladen wird)
        client = chromadb.PersistentClient(
            path=self.chromadb_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Sammlungen über ChromaDB-Client auflisten
        print("\n=== Sammlungen über ChromaDB-Client ===")
        collections = client.list_collections()
        for collection in collections:
            retrieved_coll = client.get_collection(collection)
            print(f"Sammlung: {retrieved_coll.name} --> {retrieved_coll.id}")

        # Auch direkt aus der SQLite-Datenbank lesen (zur Überprüfung)
        db_path = os.path.join(self.chromadb_path, "chroma.sqlite3")  # Pfad zur SQLite-Datenbank

        if not os.path.exists(db_path):
            ic()
            ic("\nSQLite-Datenbank nicht gefunden.")
            return

        print("\n=== Sammlungen über SQLite-Datenbank ===")
        try:
            # SQLite-Verbindung herstellen
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Alle Sammlungen aus der Datenbank abfragen
            cursor.execute("SELECT name, uuid FROM collections;")
            rows = cursor.fetchall()

            # Sammlungen ausgeben
            for row in rows:
                name, uuid = row
                print(f"DB-Sammlung: {name} --> {uuid}")

            cursor.close()
            conn.close()
        except Exception as e:
            ic()
            ic(e)

    def _clean_up(self):
        """
        Bereinigt den ChromaDB-Speicher:
        - Behält maximal die 15 neuesten Ordner (basierend auf Änderungszeit).
        - Löscht alle älteren Ordner.
        - Führt VACUUM auf der chroma.sqlite3-Datenbank durch, um den Speicherplatz zu optimieren.
        """
        if not os.path.exists(self.chromadb_path):
            return

        # Alle Dateien und Ordner im ChromaDB-Verzeichnis auflisten
        all_entries = os.listdir(self.chromadb_path)

        # Nur echte Ordner (keine Dateien) auswählen
        all_folders = [
            entry for entry in all_entries
            if os.path.isdir(os.path.join(self.chromadb_path, entry))
        ]

        # Vollständige Pfade zu den Ordnern erstellen
        folder_paths = [os.path.join(self.chromadb_path, folder) for folder in all_folders]

        # Änderungszeit für alle Ordner erfassen
        folder_paths_with_mtime = [
            (path, os.path.getmtime(path)) for path in folder_paths
        ]

        # Sortieren nach Änderungszeit (neueste zuerst)
        folder_paths_with_mtime.sort(key=lambda x: x[1], reverse=True)

        # Die 15 neuesten Ordner behalten, den Rest löschen
        folders_to_delete = folder_paths_with_mtime[15:]  # Alle anderen

        # Alte Ordner löschen
        for path, mtime in folders_to_delete:
            try:
                shutil.rmtree(path)  # Rekursives Löschen des Ordners und seines Inhalts
            except Exception as e:
                ic()
                ic(f"Fehler beim Löschen von {path}: {e}")

        # SQLite-Datenbank optimieren (Speicherplatz freigeben)
        db_path = os.path.join(self.chromadb_path, "chroma.sqlite3")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM;")  # VACUUM-Befehl zur Optimierung
                conn.close()
                print("VACUUM auf chroma.sqlite3 erfolgreich abgeschlossen.")
            except Exception as e:
                ic()
                ic(f"Fehler beim VACUUM der Datenbank: {e}")
