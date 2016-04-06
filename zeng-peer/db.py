
from TrackedFile import TrackedFile

import time

class FilesDb(object):
    def __init__(self):
        self.files = {}

        self.saveAll([
            TrackedFile(filename='zeng-peer/files.py', changed=time.time() - 50)
            , TrackedFile(filename='zeng-peer/cli.py', changed=1459000000.0)
            , TrackedFile(filename='zeng-peer/unexistent.py', changed=1459000000.0)
        ]);

    def list(self):
        return [x for x in self.files.values()]

    def listByName(self):
        return self.files.copy()

    def save(self, file):
        self.files[file.filename] = file.clone()

    def saveAll(self, files):
        for f in files:
            self.save(f)
