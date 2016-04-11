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
from daemon import *

class Event(object):
    def __init__(self, event_type, content=None):
        self.type = event_type
        self.content = content

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

    def startAsGuest(self):
        hostname, port = self.get_configured_port()
        client_socket = network.client.create_client_socket(hostname, port)
        # self.event_queue.put(RequestListFilesEvent())
        self.fire_event('sync')
        self.run(client_socket, None)

    def get_configured_port(self):
        parts = self.host.split(':')
        hostname = parts[0]
        port = int(parts[1]) if len(parts) > 1 else defs.ZENG_DEFAULT_PORT

        print("Connected to ", hostname, " at port ", port)

        return (hostname, port)

    def startAsHost(self):
        server_socket = None
        try:
            server_socket = server.tcp_server_socket('',
                                                     defs.ZENG_DEFAULT_PORT)

            client_socket, client_address = server_socket.accept()
            self.run(client_socket, client_address)

        finally:
            print("closing server socket")
            if server_socket:
                server_socket.close()

    def run(self, client_socket, client_address):
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

    def fire_event(self, event_type, content=None):
        self.event_queue.put(Event(event_type, content))

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
        print("process_messages")

        zeng_daemon = ZengDaemon(self.dir, peer_socket, self.filesDb)
        zeng_daemon_client = ZengClientDaemon(self.dir,
                                              peer_socket,
                                              self.filesDb,
                                              self.fileObserver)


        while self.running:
            ready_sockets = []

            # Bloqueia até tempo de timeout
            # ou detectar que há conteúdo a ser lido em peer_socket
            ready_sockets, _, _ = select.select([peer_socket],
                                                [], [], defs.POLL_TIME)

            # Se lista não está vazia, então há uma requisição
            if len(ready_sockets) > 0:
                zeng_daemon.handle_request()
            else:
                # Caso contrário (timeout), tenta processar fila de eventos
                self._process_queue(zeng_daemon_client)

    def _process_queue(self, zeng_client):
        try:
            # Loop infinito -
            # será interrompido quando lista estiver vazia (exceção é lançada)
            while True:
                item = self.event_queue.get_nowait()

                self._handle_queue_item(item, zeng_client)

                self.event_queue.task_done()
        except queue.Empty:
            pass

    def _handle_queue_item(self, item, zeng_client):
        if isinstance(item, TrackedFile): #TODO: use
            self._notify_file_changes([item], zeng_client.peer_socket)
        elif isinstance(item, Event):
            zeng_client.handle_event(item)

    def _notify_file_changes(self, files, peer_socket):
        # TODO: notificar outro socket
        # TODO: esperar resposta do outro (OK)
        print("changed files(%d): " % len(files), files)
        if not files:
            return

    def printChanges(self, changes):
        print("\t" + "\n\t".join([repr(x) for x in changes]))


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
