
import errno
import os
import pickle
import select
import socket
import sys
import threading
from io import StringIO

import defs
import network
import queue
from db import FilesDb
from files import FileObserver
from network import client, server
from queue import Queue
from TrackedFile import *


class RequestListFilesEvent(object):
    pass


class Peer(object):

    def __init__(self, **kwargs):
        self.dir = kwargs.get('dir')
        self.alias = kwargs.get('alias')
        self.host = kwargs.get('host')

        self.event_queue = Queue()

        self.filesDb = FilesDb()
        self.fileObserver = FileObserver(self.dir, self.filesDb)

        self.filesDb.create()

        self.running = False

    def start(self):
        if self.host is None:
            self.startAsHost()
        else:
            self.startAsGuest()

    # def startAsHost(self):
    #    conn, addr = self._wait_guest_connect()
    #    self.run(conn, addr)

    def startAsGuest(self):
        parts = self.host.split(':')
        hostname = parts[0]
        port = int(parts[1]) if len(parts) > 1 else defs.ZENG_DEFAULT_PORT

        print("host: ", hostname, " port: ", port)

        client_socket = network.client.create_client_socket(hostname, port)

        self.event_queue.put(RequestListFilesEvent())

        self.received_connection_handler(client_socket, None)

    def startAsHost(self):
        server_socket = None
        try:
            server_socket = server.tcp_server_socket('',
                                                     defs.ZENG_DEFAULT_PORT)
            # tcp_thread_target(server_socket,
            #                   self.received_connection_handler)
            client_socket, client_address = server_socket.accept()
            self.received_connection_handler(client_socket, client_address)

        finally:
            print("closing server socket")
            if server_socket:
                server_socket.close()

    def received_connection_handler(self, client_socket, client_address):
        self.running = True

        if client_socket is None:
            return

        self.startFileObserver()

        try:
            self._process_messages(client_socket)
        except:
            raise  # relança exceção
        finally:
            # ensure that connection is closed
            client_socket.close()

    def stop(self):
        print("stop!")
        self.fileObserver.stop()
        self._clear_queue()
        self.running = False

    def _clear_queue(self):
        try:
            while True:  # read until get exception (queue empty)
                self.event_queue.get_nowait()
                self.event_queue.task_done()
        except queue.Empty:
            pass

    def join(self):
        print("join!")
        self.fileObserver.join()
        self.event_queue.join()
        print("finish join")

    def startFileObserver(self):
        print("startFileObserver")

        # Verify and save local changes
        changes = self.fileObserver.check_changes()
        self.fileObserver.saveAllChanges(changes)

        # begin monitor file changes
        self.fileObserver.monitor_changes(self)

    def onNewFile(self, file):
        print("new file")
        self.event_queue.put(file)

    def onFileChange(self, file):
        print("file change")

        self.event_queue.put(file)

    def onFileRemoved(self, file):
        print("file removed")

        self.event_queue.put(file)

    def _process_messages(self, peer_socket):
        while self.running:
            ready_sockets = []

            # Bloqueia até tempo de timeout
            # ou detectar que há conteúdo a ser lido em peer_socket
            ready_sockets, _, _ = select.select([peer_socket],
                                                [], [], defs.POLL_TIME)

            # Se lista não está vazia, então há uma requisição
            if len(ready_sockets) > 0:
                self._handle_request(peer_socket)
            else:
                # Caso contrário (timeout), tenta processar fila de eventos
                self._process_queue(peer_socket)

        print("finish processing messages")

    def _handle_request(self, conn):
        data = conn.recv(1024)
        zeng_request = pickle.loads(data)

        print("receive requeset: ", zeng_request)

        if zeng_request['task'] == 'dw':
            self._handle_download_request(conn, zeng_request)
        elif zeng_request['task'] == 'list':
            self._handle_list_files(conn, zeng_request)

        if zeng_request['task'] == 'ls':
            self._handle_list_request(conn, zeng_request)

        # #Create bytearray to send response
        # reply = bytearray('OK...', 'utf-8')
        # reply.extend(data)
        #
        # print("reply: ", reply)
        #
        # if not data:
        #     return
        #
        # conn.sendall(reply)

    def _handle_download_request(self, conn, zeng_request):
        print("handle download")

        local_filename = zeng_request['file']
        file = os.path.join(self.dir, local_filename)
        data = self.read_into_buffer(file)

        self.send_len(len(data), conn)
        conn.sendall(data)

    def read_into_buffer(self, filename):
        buf = bytearray(os.path.getsize(filename))
        with open(filename, 'rb') as f:
            f.readinto(buf)
        return buf

    def _handle_list_files(self, conn, zeng_request):
        files = self.filesDb.list()
        filesStr = pickle.dumps(files)

        self.send_len(len(filesStr), conn)

        conn.sendall(filesStr)

    def send_len(self, length, socket):
        reply = bytearray("length:"+str(length)+"\n", 'utf-8')
        socket.sendall(reply)

    def _receive_file(self, filename, conn):
        f = open(filename, 'wb')
        data = socket.recv(1024)
        while data:
            f.write(data)
            data = socket.recv(1024)

        f.close()

    def _process_queue(self, peer_socket):
        try:
            # Loop infinito -
            # será interrompido quando lista estiver vazia (exceção é lançada)
            while True:
                item = self.event_queue.get_nowait()

                self._handle_queue_item(item, peer_socket)

                self.event_queue.task_done()
        except queue.Empty:
            pass

    def _handle_queue_item(self, item, peer_socket):
        print ("got item: ", item)
        if isinstance(item, TrackedFile):
            self._notify_file_changes([item], peer_socket)
        elif isinstance(item, RequestListFilesEvent):
            self._request_file_list(item, peer_socket)

    def _notify_file_changes(self, files, peer_socket):
        # TODO: notificar outro socket
        # TODO: esperar resposta do outro (OK)
        print("changed files(%d): " % len(files), files)
        if not files:
            return

    def printChanges(self, changes):
        print("\t" + "\n\t".join([repr(x) for x in changes]))

    def _request_file_list(self, item, peer_socket):
        print("request list of files")
        request = {}
        request['task'] = 'list'

        peer_socket.sendall(pickle.dumps(request))

        data = self.receive_data(peer_socket)

        trackedFiles = pickle.loads(data)
        print("data: ")
        self.printChanges(trackedFiles)

        diff = self.fileObserver.compare_files(trackedFiles)

        print("after diff")

        self.download_all(diff.import_changes, peer_socket)

    def receive_data(self, peer_socket):
        lenght = self.receive_len(peer_socket)

        print("receive ", lenght, "bytes")

        data = bytearray()

        print("len data: ", len(data))

        readed = 0
        while(readed < lenght):
            chunk = peer_socket.recv(lenght - readed)
            readed += len(chunk)
            print("received chunk with ", len(chunk), " bytes")

            data.extend(chunk)

        print("readed total of ", len(data), " bytes")

        return data

    def download_all(self, files, peer_socket):
        for f in files:
            self.download_file(f, peer_socket)
        # self.download_file(files[1], peer_socket)

    def download_file(self, file, peer_socket):
        print("download: ", file)

        # TODO: correct this
        if file.status == FileStatus.Removed or os.path.exists(file.filename):
            return

        request = {}
        request['task'] = 'dw'
        request['file'] = file.filename

        peer_socket.sendall(pickle.dumps(request))

        print("after send all download")

        data = self.receive_data(peer_socket)

        print("received: ", len(data), " bytes")

        self.filesDb.save(file)
        self.save_file(data, file.filename)

    def save_file(self, data, filename):
        full_filename = os.path.join(self.dir, filename)
        dirs = os.path.dirname(full_filename)

        self.mkdirs(dirs)
        f = open(full_filename, 'wb')
        # for chunk in data:
        #     print("type: ", type(chunk))
        #     f.write(chunk)
        f.write(data)
        f.close()

    def mkdirs(self, newdir):
        try:
            os.makedirs(newdir)
        except OSError as err:
            # Reraise the error unless it's about an already existing directory
            if err.errno != errno.EEXIST or not os.path.isdir(newdir):
                raise

    def receive_len(self, socket):
        line = ""
        # while "\n" not in line:
        #     line += socket.recv(1)

        buff = bytearray()  # Some decent size, to avoid mid-run expansion
        while True:
            data = socket.recv(1)  # Pull what it can
            buff.extend(data)  # Append that segment to the buffer
            if data.endswith(b'\n'):
                break
        line = buff.decode("utf-8")
        parts = line.split(":")

        return int(parts[1].strip())

    def _on_get_file_list(self, peer_socket, file_list):
        files_diff = self.fileObserver.compare_files(file_list)

        if not files_diff:
            return

        for f in files_diff.import_changes:
            self._get_file(f, peer_socket)

        self._notify_file_changes(files_diff.export_changes, peer_socket)

    def _get_file(self, file, peer_socket):
        print("request file: ", file)
