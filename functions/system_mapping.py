# Standardbibliotheken
import json
import os
import subprocess

# Externe Bibliotheken
from dotenv import load_dotenv
from icecream import ic

# Lade Umgebungsvariablen aus .env Datei
load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class SystemMapping:
    # Lade Einstellungen aus der settings.json Datei
    settings = json.load(open(terminal_path + "settings/settings.json"))

    @classmethod
    def map_all(cls):
        """
        Abbildung von Postgres-Datenbanken als auch Betriebssystem.

        Returns:
            tuple: Ergebnisse der OS-Abbildung und Postgres-Abbildung
        """
        psql_results = cls.map_postgres()
        os_results = cls.map_os()

        return os_results, psql_results

    @classmethod
    def map_postgres(cls, active_database=None):
        """
        Abbildung von Postgres-Datenbanken und ihren Tabellen.

        Args:
            active_database (str, optional): Name der aktiven Datenbank.
                Wenn angegeben, wird nur diese Datenbank abgebildet.

        Returns:
            list: Liste von Tabellen mit Datenbanknamen und Tabellendaten
        """
        postgres_settings = cls.settings.get("tools", "").get("postgres", "")
        username = postgres_settings.get("username", "")
        databases = postgres_settings.get("databases", [])  # Liste der Datenbanken
        mapping_tables_command = postgres_settings.get("mapping_tables_command", [])  # Liste der Befehlsteile

        table_results = []

        mapping_tables_command[2] = username

        # Wenn keine aktive Datenbank angegeben ist, bilde alle Datenbanken ab
        if databases and mapping_tables_command and username and not active_database:
            for database in databases:
                mapping_tables_command[5] = database

                try:
                    # Speichere das Ergebnis von subprocess.run()
                    result = subprocess.run(
                        mapping_tables_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )

                    # Füge sowohl Datenbankname als auch Befehlsausgabe zu table_results hinzu
                    table_results.append({
                        "database": database,
                        "tables_table": result.stdout
                    })

                except subprocess.CalledProcessError as e:
                    ic()
                    ic(f"stdout: {e.stdout}")
                    ic(f"stderr: {e.stderr}")
                    return []
                except Exception as e:
                    ic()
                    ic(e)
                    return []

        # Wenn eine aktive Datenbank angegeben ist, bilde nur diese ab
        elif mapping_tables_command and username and active_database:
            mapping_tables_command[5] = active_database

            try:
                # Speichere das Ergebnis von subprocess.run()
                result = subprocess.run(
                    mapping_tables_command,
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Füge sowohl Datenbankname als auch Befehlsausgabe zu table_results hinzu
                table_results.append({
                    "database": active_database,
                    "tables_table": result.stdout
                })

            except subprocess.CalledProcessError as e:
                ic()
                ic(f"stdout: {e.stdout}")
                ic(f"stderr: {e.stderr}")
                return []
            except Exception as e:
                ic()
                ic(e)
                return []

        return table_results

    @classmethod
    def map_os(cls):
        """
        Abbildung vom Dateisystem mit Hilfe des tree commands und speichert die Ausgabe in einer JSON-Datei.

        Returns:
            dict: Verarbeitete Dateisystemabbildung
        """
        os_mapping_vars = cls.settings.get("os_mapping")
        tree_command = os_mapping_vars.get("tree_command", None)
        tree_file_path = os_mapping_vars.get("tree_file_path", "./database/system_tree.json")
        delete_tree_command = os_mapping_vars.get("delete_tree_command", None)

        if any(var is None for var in [tree_command, tree_file_path, delete_tree_command]):
            return {}

        tree_command.append(tree_file_path)
        delete_tree_command.append(tree_file_path)

        if tree_command:
            try:
                # Versuche, die bestehende Abbildung zu löschen
                subprocess.run(
                    delete_tree_command,
                    capture_output=True,
                    text=True,
                    check=True
                )

                try:
                    # Erzeuge neue Abbildung
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Verarbeite die erzeugte Abbildung
                    return cls.process_os_mapping(tree_file_path)

                except subprocess.CalledProcessError as e:
                    ic()
                    ic(f"stdout: {e.stdout}")
                    ic(f"stderr: {e.stderr}")
                    return {}
                except Exception as e:
                    ic()
                    ic(f"error: {e}")
                    return {}

            except subprocess.CalledProcessError as e:
                # Wenn das Löschen fehlschlägt, versuche trotzdem Abbildung zu generieren
                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Verarbeite die erzeugte Abbildung
                    return cls.process_os_mapping(tree_file_path)

                except subprocess.CalledProcessError as e:
                    ic()
                    ic(f"stdout: {e.stdout}")
                    ic(f"stderr: {e.stderr}")
                    return {}
                except Exception as e:
                    ic()
                    ic(f"error: {e}")
                    return {}

            except Exception as e:
                # Wenn während des Löschens eine andere Ausnahme auftritt, versuche trotzdem zu generieren
                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Verarbeite die erzeugte Abbildung
                    return cls.process_os_mapping(tree_file_path)

                except Exception as e:
                    ic()
                    ic(f"error: {e}")
                    return {}

        else:
            return {}

    @classmethod
    def process_os_mapping(cls, tree_file_path=None):
        """
        Verarbeitet die JSON-Ausgabe des tree commands und erstellt ein Verzeichnis-Wörterbuch.

        Args:
            tree_file_path (str, optional): Pfad zur JSON-Datei mit Baumstruktur.
                Wenn nicht angegeben, wird der Pfad aus den Einstellungen verwendet.

        Returns:
            dict: Wörterbuch mit Dateipfaden und zugehörigen Informationen
        """
        if tree_file_path is None:
            tree_file_path = cls.settings.get("tree_file_path", "./database/system_tree.json")

        try:
            with open(tree_file_path, 'r') as file:
                json_output = json.load(file)

            base_tree, report = json_output
            root_dirs = base_tree.get('contents', None)

            if not root_dirs:
                ic()
                ic(f"Fehler beim Laden des system_tree.json")
                return {}

            directory_dict = {}
            empty_directories = 0
            directories = []

            # Iteriere durch die root directories und extrahiere Details
            for directory in root_dirs:
                if type(directory) == dict:
                    if directory["type"] == "directory":
                        directories.append(directory["name"])
                    if directory["type"] == "directory" and directory.get("contents", False):
                        for item in directory["contents"]:
                            if item["type"] == "file":
                                item_name = item["name"].split("/")[-1]
                                directory_dict[item["name"]] = {"filetype": item["type"], "item": item_name}
                            elif item["type"] == "directory":
                                root_dirs.append(item)


                elif directory["type"] == "directory" and not directory.get("contents", False):
                    item_name = directory["name"].split("/")[-1]
                    directory_dict[directory["name"]] = {"filetype": directory["type"], "item": item_name}
                    empty_directories += 1

            # Entferne große Elemente
            for path, content in directory_dict.items():
                if len(content) > 2000:
                    del directory_dict[path]

            return directory_dict

        except Exception as e:
            ic()
            ic(e)
            return {}
