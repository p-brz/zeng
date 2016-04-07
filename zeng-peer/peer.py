
import socket
import sys
import threading
import select

import queue
from queue import Queue

from db import FilesDb
from files import FileObserver

class Peer(object):
    HOST = ''   # Symbolic name, meaning all available interfaces
    PORT = 8888 # Arbitrary non-privileged port

    def __init__(self, **kwargs):
        self.dir = kwargs.get('dir')
        self.alias = kwargs.get('alias')
        self.host = kwargs.get('host')

        self.event_queue = Queue()

        self.filesDb = FilesDb()
        self.fileObserver = FileObserver(self.filesDb)

        self.running = False

    def start(self):
        if self.host is None:
            self.startAsHost()
        else:
            self.startAsGuest()

    def startAsHost(self):
        conn, addr = self._wait_guest_connect()
        self.run(conn, addr)

    def startAsGuest(self):
        pass

    def run(self, conn, addr):
        self.running = True

        if conn is None:
            return

        self.startFileObserver()

        try:
            conn.sendall(b'Welcome to the server. Type something and hit enter\n') #send only takes string
            self._process_messages(conn)
        except:
            raise
        finally:
            #ensure that connection is closed
            conn.close()

    def stop(self):
        print("stop!")
        self.fileObserver.stop()
        self._clear_queue()
        self.running = False

    def _clear_queue(self):
        try:
            while True: #read until get exception (queue empty)
                self.event_queue.get_nowait()
                self.event_queue.task_done()
        except queue.Empty:
            pass

    def join(self):
        print("join!")
        self.fileObserver.join()
        self.event_queue.join()


    def startFileObserver(self):
        #Verify and save local changes
        changes = self.fileObserver.check_changes(self.dir)
        self.fileObserver.saveAllChanges(changes)

        #begin monitor file changes
        self.fileObserver.monitor_changes(self.dir, self)

    def onNewFile(self, file):
        print ("new file: ", file)
        self.event_queue.put(file)

    def onFileChange(self, file):
        print ("changed file: ", file)
        self.event_queue.put(file)

    def onFileRemoved(self, file):
        print ("file removed: ", file)
        self.event_queue.put(file)

    def _process_messages(self, conn):
        while self.running:
            readReady = []

            while len(readReady) == 0 :
                if not self.running: #Parou de executar
                    print("stopped!")
                    return

                readReady,_,_ = select.select([conn], [], [], 1.0)

                if len(readReady) == 0:
                    self._process_queue()

            self._handle_request(readReady[0])

    def _handle_request(self, conn):
        #Receive data from client
        data = conn.recv(1024)

        #Create bytearray to send response
        reply = bytearray('OK...', 'utf-8')
        reply.extend(data)

        print("reply: ", reply)

        if not data:
            return

        conn.sendall(reply)

    def _process_queue(self):
        try:
            while True: #read until get exception (queue empty)
                item = self.event_queue.get_nowait()

                print("Got queue item: ", item)

                self.event_queue.task_done()
        except queue.Empty:
            pass

    def _wait_guest_connect(self):
        s = self._create_server_socket()

        conn = None
        addr = None
        try:
               #wait to accept a connection - blocking call
               conn, addr = s.accept()
               print('Connected with ' + addr[0] + ':' + str(addr[1]))
        finally:
            print("closing server socket")
            s.close()

        return (conn, addr)

    def _create_server_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print ('Socket created')

        #Bind socket to local host and port
        try:
           s.bind((self.HOST, self.PORT))
        except socket.error as msg:
        #    print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            print("error: ", msg)
            sys.exit()

        print('Socket bind complete')

        #Start listening on socket
        s.listen(10)
        print('Socket now listening')

        return s
