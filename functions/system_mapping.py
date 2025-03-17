import json
import subprocess

from icecream import ic

from functions.chromadb_client import ChromaDB


class SystemMapping:
    settings = json.load(open("./settings/settings.json"))

    @classmethod
    def import_os_to_vdb(cls):
        tree_data = cls.process_system_mapping()
        documents = []
        ids = []

        if tree_data:
            empty_dirs = 0
            for path, directory in tree_data.items():
                if not directory:
                    empty_dirs += 1
                if directory:
                    documents.append(str(directory))
                    ids.append(path)

        else:
            #TODO Else Statement
            pass

        ChromaDB.replace_data(collection=cls.settings.get("chromadb_tree_collection", "tree_collection"),
                              documents=documents,
                              ids=ids)
        return True

    @classmethod
    def process_system_mapping(cls):
        confirmation = cls.map_system()
        if not confirmation:
            return False
        with open(cls.settings.get("tree_file_path", "./database/system_tree.json"), 'r') as file:
            json_output = json.load(file)

        base_tree, report = json_output
        root_dirs = base_tree.get('contents', None)

        if not root_dirs:
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

        return directory_dict

    @classmethod
    def map_system(cls):
        tree_command = cls.settings.get("tree_command", None)
        tree_file_path = cls.settings.get("tree_file_path", "./database/system_tree.json")
        delete_tree_command = cls.settings.get("delete_tree_command", None)

        if any(var is None for var in [tree_command, tree_file_path, delete_tree_command]):
            return False

        tree_command.append(tree_file_path)
        delete_tree_command.append(tree_file_path)

        if tree_command:
            try:
                subprocess.run(
                    delete_tree_command,
                    capture_output=True,
                    text=True,
                    check=True
                )

                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    return True

                except subprocess.CalledProcessError as e:
                    return False
                except Exception as e:
                    return False

            except subprocess.CalledProcessError as e:

                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    return True

                except subprocess.CalledProcessError as e:
                    return False
                except Exception as e:
                    return False

            except Exception as e:

                try:
                    subprocess.run(
                        tree_command,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    return True

                except Exception as e:
                    return False

        else:
            return None