import sys
import time
import logging

import watchdog
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

class FileObserver(object):
    def __init__(self, filesDb):
        self.filesDb = filesDb
        self.observer = None

    def check_changes(self, base_dir):
        comparator = FileChangeComparator(self.filesDb, base_dir)
        return comparator.check_changes()

    def saveChange(self, trackedFile):
        if not trackedFile:
            return

        if trackedFile.status != FileStatus.Removed:
            trackedFile = trackedFile.clone()
            trackedFile.status = FileStatus.Synced

        self.filesDb.save(trackedFile)

    def saveAllChanges(self, trackedFiles):
        for f in trackedFiles:
            self.saveChange(f)

    def monitor_changes(self, base_dir, listener):
        #if is monitoring files, stop
        self.stop()

        event_handler = FileObserver.ObserverAdapter(listener, self, base_dir)

        self.observer = Observer()
        self.observer.schedule(event_handler, base_dir, recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()

    def join(self):
        if self.observer:
            self.observer.join()

    def hasFileChanged(self, trackedFile):
        dbFile = self.filesDb.get(filename=trackedFile.filename)
        return (not dbFile) or (dbFile.changed < trackedFile.changed)

    class ObserverAdapter(watchdog.events.FileSystemEventHandler):
        def __init__(self, listener, filesObserver, base_dir):
            self.listener = listener
            self.filesObserver = filesObserver
            self.base_dir = base_dir

        def on_created(self, event):
            self.notify_event(event.src_path, FileStatus.Unsynced, 'onNewFile')

        def on_deleted(self, event):
            self.notify_event(event.src_path, FileStatus.Removed, 'onFileRemoved')

        def on_modified(self, event):
            #Ignora mudanças em diretório, pois elas devem estar associadas a um
            # arquivo (adicionado ou removido)
            if not event.is_directory:
                self.notify_event(event.src_path, FileStatus.Unsynced, 'onFileChange')

        def on_moved(self, event):
            self.notify_event(event.src_path, FileStatus.Removed, 'onFileRemoved')
            self.notify_event(event.dest_path, FileStatus.Unsynced, 'onNewFile')

        def notify_event(self, path, fileStatus, method_name):
            now = datetime.fromtimestamp(time.time())
            file = TrackedFile(path
                    , status = fileStatus
                    , base_dir = self.base_dir
                    # Se arquivo é removido, utiliza 'agora' como timestamp,
                    # caso contrário, obtém timestamp do arquivo
                    , changed = now if fileStatus == FileStatus.Removed else None)

            if file.isHidden() or not self.filesObserver.hasFileChanged(file):
                return

            self.filesObserver.saveChange(file)

            if self.listener:
                getattr(self.listener, method_name)(file)

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

                #ignore hidden files or directories
                if f.isHidden():
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

class ChangeFileListener(object):
    def onNewFile(self, file):
        print ("new file: ", file)

    def onFileChange(self, file):
        print ("changed file: ", file)

    def onFileRemoved(self, file):
        print ("file removed: ", file)


def main():
    filesDb = FilesDb()
    filesDb.create()

    observer = FileObserver(filesDb)
    base_dir = os.getcwd()

    changes = observer.check_changes(base_dir)
    printChanges(changes)
    observer.saveAllChanges(changes)
    printChanges(observer.check_changes(base_dir))

    #monitorar mudanças
    listener = ChangeFileListener()
    observer.monitor_changes(base_dir, listener)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

    printChanges(filesDb.list())


if __name__ == "__main__":
    main()
