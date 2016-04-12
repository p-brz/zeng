import fnmatch
import logging
import os
import sys
import time
import errno
from os import path
from stat import *

import defs
import watchdog
from db import FilesDb
from TrackedFile import *
from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

from utils import log_debug

from IgnorerParser import IgnorerParser

def mkdirs(newdir):
    """Cria um diretório e seus 'pais' caso não existam"""
    try:
        os.makedirs(newdir)
    except OSError as err:
        # Reraise the error unless it's about an already existing directory
        if err.errno != errno.EEXIST or not os.path.isdir(newdir):
            raise

class FileObserver(object):

    def __init__(self, base_dir, filesDb):
        self.filesDb = filesDb
        self.base_dir = base_dir
        self.observer = None
        self.ignorer = IgnorerParser()

        ignore_file = path.join(base_dir, defs.IGNORE_FILE)
        if path.exists(ignore_file):
            self.ignorer.start(ignore_file)

        log_debug("ignore patterns: ", self.ignorer.ignore_patterns)
        log_debug("include patterns: ", self.ignorer.include_patterns)

    def check_changes(self):
        comparator = FileChangeComparator(self.filesDb, self.base_dir)
        changed_files =  comparator.check_changes()

        return [f for f in changed_files if not self.ignorer.ignore(f.filename)]

    def compare_files(self, other_files):
        comparator = FileChangeComparator(self.filesDb, self.base_dir)
        return comparator.compare_files(other_files)

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

    def monitor_changes(self, listener):
        # if is monitoring files, stop
        self.stop()

        event_handler = FileObserver.ObserverAdapter(listener,
                                                     self, self.base_dir)

        self.observer = Observer()
        self.observer.schedule(event_handler, self.base_dir, recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()

    def join(self):
        if self.observer:
            self.observer.join()

    def hasFileChanged(self, trackedFile):
        dbFile = self.filesDb.get(filename=trackedFile.filename)

        if not dbFile:
            return True
        elif dbFile.changed is None or trackedFile.changed is None:
            return False
        else:
            return (dbFile.changed < trackedFile.changed)

    class ObserverAdapter(watchdog.events.FileSystemEventHandler):

        def __init__(self, listener, filesObserver, base_dir):
            self.listener = listener
            self.filesObserver = filesObserver
            self.base_dir = base_dir

        def on_created(self, event):
            self.notify_event(event.src_path, FileStatus.Unsynced,
                              'onNewFile', event.is_directory)

        def on_deleted(self, event):
            self.notify_event(event.src_path, FileStatus.Removed,
                              'onFileRemoved', event.is_directory)

        def on_modified(self, event):
            # Ignora mudanças em diretório, pois elas
            # devem estar associadas a um arquivo (adicionado ou removido)
            if not event.is_directory:
                self.notify_event(event.src_path, FileStatus.Unsynced,
                                  'onFileChange', event.is_directory)

        def on_moved(self, event):
            is_dir = event.is_directory
            self.notify_event(event.src_path, FileStatus.Removed,
                              'onFileRemoved', is_dir)
            self.notify_event(event.dest_path, FileStatus.Unsynced,
                              'onNewFile', is_dir)

        def notify_event(self, path, fileStatus, method_name, is_dir):
            # Não suporta diretórios, atualmente
            if is_dir:
                return

            now = datetime.fromtimestamp(time.time())
            # Se arquivo é removido, utiliza 'agora' como timestamp,
            # caso contrário, obtém timestamp do arquivo
            changed_value = now if fileStatus == FileStatus.Removed else None
            file = TrackedFile(path,
                               status=fileStatus,
                               base_dir=self.base_dir,
                               changed=changed_value)


            if file.isHidden() or self.is_ignored(file.filename) or not self.filesObserver.hasFileChanged(file):
                return

            self.filesObserver.saveChange(file)

            if self.listener:
                getattr(self.listener, method_name)(file.clone())

        def is_ignored(self, path):
            return self.filesObserver.ignorer.ignore(path)

class FilesDiff(object):
    '''
        Auxiliar para encapsular arquivos que devem ser enviados
        para outro host (export_changes) e arquivos a
        serem obtidos do outro (import_changes)
    '''

    def __init__(self, **kwargs):
        self.export_changes = kwargs.get('export_changes', [])
        self.import_changes = kwargs.get('import_changes', [])


class FileChangeComparator(object):

    def __init__(self, filesDb, base_dir):
        self.filesDb = filesDb
        self.base_dir = base_dir

    def check_changes(self):
        filesMap = self.filesDb.listByName()

        changes = []

        for dirName, subdirList, fileList in os.walk(self.base_dir):
            for filename in fileList:
                f = TrackedFile(path.join(dirName, filename),
                                base_dir=self.base_dir,
                                status=FileStatus.Unsynced)

                # ignore hidden files or directories
                if f.isHidden():
                    continue

                self._checkChanged(f, filesMap, changes)

        self._checkRemoved(filesMap, changes)
        return changes

    def compare_files(self, other_files):
        filesDiff = FilesDiff()

        local_files = self.filesDb.listByName()

        for otherF in other_files:
            filename = otherF.filename

            localF = local_files.get(filename, None)
            if localF is None:
                filesDiff.import_changes.append(otherF)
                continue

            # Remove para evitar processar arquivo duas vezes
            local_files.pop(filename)

            if localF.changed < otherF.changed:  # local é mais antigo
                filesDiff.import_changes.append(otherF)
            elif localF.changed > otherF.changed:  # remoto é mais antigo
                filesDiff.export_changes.append(localF)

        # Arquivos locais que não existem no remoto
        for f in local_files.values():
            filesDiff.export_changes.append(f)

        return filesDiff

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
