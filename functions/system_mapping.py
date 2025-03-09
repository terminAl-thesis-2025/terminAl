import json
import subprocess

from icecream import ic

class SystemMapping:
    settings = json.load(open("./settings/settings.json"))

    @classmethod
    def import_os_to_vdb(cls, tree_c):
        # TODO import the processed system mapping to the vector database
        pass

    @classmethod
    def process_system_mapping(cls, tree_output):
        tree = json.loads(tree_output)
        # TODO implement the Breadth-First algorithm from test_os_mapping.ipynb

    @classmethod
    def map_system(cls):
        tree_command = cls.settings["tree_command"]
        if tree_command:
            try:
                # Use subprocess.run with capture_output to get the result
                result = subprocess.run(
                    tree_command,
                    capture_output=True,
                    text=True,
                    check=True  # This will raise an exception if the command fails
                )

                # Get the JSON output
                tree_json = result.stdout

                # Save to file
                with open('system_tree.json', 'w') as f:
                    f.write(tree_json)

                # TODO return tree_output instead of saving as json
                print(f"Tree command completed successfully. Output saved to system_tree.json")
                return True

            except subprocess.CalledProcessError as e:
                print(f"Error running tree command: {e}")
                print(f"Error output: {e.stderr}")
                return False
            except Exception as e:
                print(f"Unexpected error: {e}")
                return False

        else:
            ic()
            ic('Es gab einen Fehler beim importieren des "tree_command" vom .env')
            return None
