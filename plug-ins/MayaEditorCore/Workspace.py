import json


class Workspace:
    def __init__(self):
        self.workspace_name: str = ""
        self.files: list = []
        self.is_saved = False

    def add_file(self, file):
        self.files.append(file)

    def save(self, filename):
        workspace = {}
        workspace["name"] = self.workspace_name
        workspace["files"] = self.files
        with open(filename, "w") as workspace_file:
            json.dump(workspace, indent=4, fp=workspace_file)

    def load(self, filename):
        self.files.clear()

        with open(filename, "r") as workspace_file:
            workspace = json.load(workspace_file)
            self.name = workspace["name"]
            self.files = workspace["files"]
        print(f"{self.name} {self.files}")
