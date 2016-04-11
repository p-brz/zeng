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
        peer_socket = network.client.create_client_socket(hostname, port)
        self.fire_event('sync')
        self.run(peer_socket)

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

            peer_socket, peer_address = server_socket.accept()
            self.run(peer_socket)

        finally:
            print("closing server socket")
            if server_socket:
                server_socket.close()

    def run(self, peer_socket):
        if peer_socket is None:
            return

        try:
            self.running = True
            self.startFileObserver()
            self._process_messages(peer_socket)
        except:
            raise  # relança exceção
        finally:
            # ensure that connection is closed
            peer_socket.close()

    def startFileObserver(self):
        self.verify_local_file_changes()

        # begin monitor file changes
        self.fileObserver.monitor_changes(ChangeFilesListener(self))

    def verify_local_file_changes(self):
        "Verify and save local changes"

        changes = self.fileObserver.check_changes()
        self.fileObserver.saveAllChanges(changes)

    def stop(self):
        print("stop!")
        self.fileObserver.stop()
        self.clear_queue()
        self.running = False

    def fire_event(self, event_type, content=None):
        self.event_queue.put(Event(event_type, content))

    def clear_queue(self):
        self.process_queue(None)

    def join(self):
        print("join!")
        self.fileObserver.join()
        self.event_queue.join()
        print("finish join")

    def _process_messages(self, peer_socket):
        zeng_daemon = ZengDaemon(self.dir, peer_socket, self.filesDb)
        zeng_daemon_client = ZengClientDaemon(self.dir,
                                              peer_socket,
                                              self.filesDb,
                                              self.fileObserver)


        while self.running:
            if self.wait_to_read_socket(peer_socket, defs.POLL_TIME):
                zeng_daemon.handle_request()
            else:
                # Timeout: tenta processar fila de eventos
                self.process_queue(zeng_daemon_client)

    def wait_to_read_socket(self, socket, timeout):
        '''Espera por um tempo de até "timeout" segundos para "socket" estar
            pronto para leitura.
            Caso timeout ocorra retorna None, se não retorna o socket
        '''

        # Bloqueia até tempo de timeout
        # ou detectar que há conteúdo a ser lido em socket
        ready_sockets, _, _ = select.select([socket],
                                            [], [], timeout)

        if not ready_sockets or len(ready_sockets) == 0:
            return None
        else:
            return ready_sockets[0]

    def process_queue(self, event_handler):
        try:
            # Loop infinito -
            # será interrompido quando lista estiver vazia (exceção é lançada)
            while True:
                item = self.event_queue.get_nowait()

                if event_handler:
                    event_handler.handle_event(item)

                self.event_queue.task_done()
        except queue.Empty:
            pass

class ChangeFilesListener(object):
    class FileEvent(object):
        def __init__(self, file, type):
            self.file = file
            self.type = type

    def __init__(self, peer):
        self.peer = peer

    def onNewFile(self, file):
        self.notify_event(file, 'created')

    def onFileChange(self, file):
        self.notify_event(file, 'changed')

    def onFileRemoved(self, file):
        self.notify_event(file, 'removed')

    def notify_event(self, file, type):
        log_debug("file '", file.filename,"' event: ", type)

        self.peer.fire_event('file_change', self.FileEvent(file, type))
