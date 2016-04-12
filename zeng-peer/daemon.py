import datetime
import pickle
import os
import files
import time


from defs import REQUEST_SEPARATOR_TOKEN
from utils import log_debug
from network.server import send_data
from network.client import receive_data
from network import client
from files import *


class ZengDaemon(object):

    def __init__(self, zeng_dir, peer_socket, files_db, fileObserver):
        self.dir = zeng_dir
        self.peer_socket = peer_socket
        self.files_db = files_db
        self.fileObserver = fileObserver

        self.fileSyncer = FileSyncer(zeng_dir, peer_socket, files_db)

    def handle_request(self):
        data = self.peer_socket.recv(1024)
        zeng_request = pickle.loads(data)
        request_id = zeng_request['task']

        log_debug("Received message " + str(zeng_request))

        if request_id == 'update':
            self.on_get_file_update(zeng_request)
        elif request_id == 'list':
            self.on_get_file_ls()
        elif request_id == 'dw':
            self.on_get_file_download(zeng_request)

    # GET -> Lida com as respostas do par
    def on_get_file_update(self, request):
        self.send_response({"status": "OK"})

        diff = self.fileObserver.compare_files(request.get('files', []))

        if diff and len(diff.import_changes) > 0:
            self.fileSyncer.sync_all(diff.import_changes)


    def on_get_file_ls(self):
        files = self.files_db.list()
        self.send_response(files)

    def on_get_file_download(self, zeng_request):
        local_filename = zeng_request['file']
        file = os.path.join(self.dir, local_filename)
        data = open(file, 'rb').read()

        self.send_response(data)

    def send_response(self, data):
        send_data(self.peer_socket, data)



class ZengClientDaemon(object):

    def __init__(self, shared_dir, peer_socket, files_db, fileObserver):
        self.dir = shared_dir
        self.peer_socket = peer_socket
        # self.files_db = files_db
        self.fileObserver = fileObserver

        self.fileSyncer = FileSyncer(shared_dir, peer_socket, files_db)

    def handle_event(self, event):
        log_debug("handle_event: ", event)
        evtype = event.type
        if evtype == 'sync':
            self.sync_changes()
        elif evtype == 'file_change':
            self.on_file_change(event.content)

    def sync_changes(self):
        changes = self.get_file_changes()

        self.fileSyncer.sync_all(changes.import_changes)
        self.post_file_changes(changes.export_changes)

    def on_file_change(self, file_evt):
        changed_file = file_evt.file

        log_debug("on_file_change: ", changed_file)
        self.post_file_changes([changed_file])

    def get_file_changes(self):

        trackedFiles = self.do_request('list')
        diff = self.fileObserver.compare_files(trackedFiles)

        return diff

    def post_file_changes(self, files):
        if files and len(files) > 0:
            self.do_request('update', files=files)

    def do_request(self, req_type, **data_members):
        return client.do_request(self.peer_socket, req_type, **data_members)


class FileSyncer(object):

    def __init__(self, zeng_dir, peer_socket, files_db):
        self.dir = zeng_dir
        self.peer_socket = peer_socket
        self.files_db = files_db

    def sync_all(self, files):
        for f in files:
            self.sync_file(f)

    def sync_file(self, file):
        if not self.file_has_changed(file):
            return
        elif file.status == FileStatus.Removed:
            self.remove_file(file)
        elif not file.is_dir:
            self.download_file(file)

    def download_file(self, file):
        print("downloading: ", file, " ...", end="")

        data = client.do_request(self.peer_socket, 'dw', file=file.filename)

        self.save_file(data, file)

        print(" Ok")


    def remove_file(self, file):
        print("removing: ", file.filename, " ...", end="")

        try:
            filename = self.get_full_filename(file)
            os.remove(filename)
        except OSError:
            pass

        removed_file = TrackedFile(filename= file.filename,
                                   status  = FileStatus.Removed,
                                   changed = datetime.fromtimestamp(time.time()))
        self.files_db.save(removed_file)

        print(" Ok")

    def file_has_changed(self, file):
        db_file = self.files_db.get(filename=file.filename)

        if db_file:
            return file.changed > db_file.changed
        elif os.path.exists(file.filename):
            local_file = TrackedFile(file.filename)

            # precisa baixar se arquivo atual é menos recente ou se foi removido
            return file.status == FileStatus.Removed or local_file.changed < file.changed
        else:
            #se arquivo não existe localmente (ou no banco), deve baixo-lo
            #se ele não tiver sido removido no par
            return file.status != FileStatus.Removed

    def save_file(self, data, file):
        self.files_db.save(file)

        full_filename = self.get_full_filename(file)
        dirs = os.path.dirname(full_filename)

        files.mkdirs(dirs)
        with open(full_filename, 'wb') as output:
            output.write(data)

        #Define o tempo de modificação (e acesso) do arquivo para o timestamp
        # definido em file (ou para o tempo atual)

        times = None
        if file.changed:
            epoch_time = time.mktime(file.changed.timetuple())
            times = (epoch_time, epoch_time)

        os.utime(full_filename, times)

    def get_full_filename(self, file):
        return os.path.join(self.dir, file.filename)
