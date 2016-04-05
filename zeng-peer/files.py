import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

import fnmatch
import os
from os import path
import time
from stat import *

from db import FilesDb

from TrackedFile import *

def monitor_changes():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = LoggingEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

class FileObserver(object):
    def __init__(self, filesDb):
        self.filesDb = filesDb

    def check_changes(self, base_dir):
        comparator = FileChangeComparator(self.filesDb, base_dir)
        return comparator.check_changes()

class FileChangeComparator(object):
    def __init__(self, filesDb, base_dir):
        self.filesDb = filesDb
        self.base_dir = base_dir

    def check_changes(self):
        filesMap = self.filesDb.listByName()

        changes = []

        for dirName, subdirList, fileList in os.walk(self.base_dir):
            for filename in fileList:
                f = TrackedFile(path.join(dirName, filename)
                    , base_dir= self.base_dir
                    , status  = FileStatus.Unsynced)

                #ignore hidden files
                if f.filename.startswith("."):
                    continue

                self._checkChanged(f, filesMap, changes)

        self._checkRemoved(filesMap, changes)


        return changes

    def _checkChanged(self, f, filesMap, changes):
        dbFile = filesMap.get(f.filename)
        if dbFile is None or self.hasFileChanged(dbFile, f):
            changes.append(f)
        else:
            f.status = FileStatus.Synced

        if dbFile:
            filesMap.pop(f.filename)

    def _checkRemoved(self, filesMap, changes):
        # Files not found on dirs, but stored on db
        for f in filesMap.values():
            if f.status != FileStatus.Removed:
                f.status = FileStatus.Removed
                changes.append(f)

    def hasFileChanged(self, dbFile, trackedFile):
        return dbFile.changed < trackedFile.changed

def printChanges(changes):
    print("changes: \n\t", "\n\t".join([repr(x) for x in changes]))

def main():
    filesDb = FilesDb()
    observer = FileObserver(filesDb)

    changes = observer.check_changes(os.getcwd())

    printChanges(changes)

    filesDb.saveAll(changes)
    changes = observer.check_changes(os.getcwd())

    printChanges(changes)


if __name__ == "__main__":
    main()
