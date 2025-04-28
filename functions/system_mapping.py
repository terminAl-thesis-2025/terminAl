import json, os, subprocess
from icecream import ic
from collections import deque
from dotenv import load_dotenv

load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")

class SystemMapping:
    settings = json.load(open(terminal_path + "settings/settings.json"))

    @classmethod
    def map_all(cls):
        psql_results = cls.map_postgres()
        os_results = cls.map_os()

        return os_results, psql_results

    @classmethod
    def map_postgres(cls):
        postgres_settings = cls.settings.get("tools", "").get("postgres", "")
        username = postgres_settings.get("username", "")
        databases = postgres_settings.get("databases", [])  # list of Databses
        mapping_tables_command = postgres_settings.get("mapping_tables_command", [])  # list of command parts

        table_results = []

        mapping_tables_command[2] = username


        if databases and mapping_tables_command and username:
            for database in databases:
                mapping_tables_command[5] = database

                try:
                    # Store the result of subprocess.run()
                    result = subprocess.run(
                        mapping_tables_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )

                    # Append both database name and command output to psql_results
                    table_results.append({
                        "database": database,
                        "tables_table": result.stdout
                    })

                except subprocess.CalledProcessError as e:
                    ic(e)
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
        os_mapping_vars = cls.settings.get("os_mapping")
        tree_command = os_mapping_vars.get("tree_command", None)
        tree_file_path = os_mapping_vars.get("tree_file_path", "./database/system_tree.json")
        delete_tree_command = os_mapping_vars.get("delete_tree_command", None)

        if any(var is None for var in [tree_command, tree_file_path, delete_tree_command]):
            ic()
            ic("Fucking Issues!!!")
            return {}

        tree_command.append(tree_file_path)
        delete_tree_command.append(tree_file_path)

        if tree_command:
            try:
                # Try to delete existing tree file
                subprocess.run(
                    delete_tree_command,
                    capture_output=True,
                    text=True,
                    check=True
                )

                try:
                    # Generate new tree file
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Process the generated tree file
                    return cls.process_os_mapping(tree_file_path)

                except subprocess.CalledProcessError as e:
                    ic(e)
                    ic(f"stdout: {e.stdout}")
                    ic(f"stderr: {e.stderr}")
                    return {}
                except Exception as e:
                    ic(e)
                    ic(f"error: {e}")
                    return {}

            except subprocess.CalledProcessError as e:
                # If deletion fails, try to generate anyway
                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Process the generated tree file
                    return cls.process_os_mapping(tree_file_path)

                except subprocess.CalledProcessError as e:
                    ic(e)
                    ic(f"stdout: {e.stdout}")
                    ic(f"stderr: {e.stderr}")
                    return {}
                except Exception as e:
                    ic(e)
                    ic(f"error: {e}")
                    return {}

            except Exception as e:
                # If another exception occurs during deletion, try to generate anyway
                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Process the generated tree file
                    return cls.process_os_mapping(tree_file_path)

                except Exception as e:
                    ic(e)
                    ic(f"error: {e}")
                    return {}

        else:
            ic()
            ic("Fucking Else!#############################")
            return {}

    @classmethod
    def process_os_mapping(cls, tree_file_path=None):
        if tree_file_path is None:
            tree_file_path = cls.settings.get("tree_file_path", "./database/system_tree.json")

        try:
            with open(tree_file_path, 'r') as file:
                json_output = json.load(file)

            base_tree, report = json_output
            root_dirs = base_tree.get('contents', None)

            if not root_dirs:
                ic()
                ic(f"Empty root directory list: {root_dirs}")
                return {}

            directory_dict = {}
            empty_directories = 0
            directories = []

            for root_dir in root_dirs:
                if root_dir["type"] == "directory":
                    directories.append(root_dir["name"])
                if root_dir["type"] == "directory" and root_dir.get("contents", False):
                    directory_dict[root_dir["name"]] = [item["name"] for item in root_dir["contents"] if
                                                        item["type"] == "file"]
                    root_dirs.extend([item for item in root_dir["contents"] if item["type"] == "directory"])

                elif root_dir["type"] == "directory" and not root_dir.get("contents", False):
                    directory_dict[root_dir["name"]] = []
                    empty_directories += 1

            # Remove Big Items for now. Split up later on.
            for path, content in directory_dict.items():
                if len(content) > 2000:
                    del directory_dict[path]

            return directory_dict

        except Exception as e:
            ic(e)
            ic(f"error: {e}")
            return {}

    def fast_process_os_mapping(self, tree_file_path):
        data, _ = json.loads(open(tree_file_path, 'rb').read())
        queue = deque(data.get("contents", []))
        directory_dict = {}

        while queue:
            node = queue.popleft()
            if node["type"] != "directory":
                continue

            # collect file names in this directory
            files = [c["name"] for c in node.get("contents", [])
                     if c["type"] == "file"]
            directory_dict[node["name"]] = files

            # enqueue subdirectories
            for c in node.get("contents", []):
                if c["type"] == "directory":
                    queue.append(c)

        # Remove Big Items for now. Split up later on.
        for path, content in directory_dict.items():
            if len(content) > 2000:
                del directory_dict[path]

        return directory_dict
