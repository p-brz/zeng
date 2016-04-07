

def receive_file(socket, filename):
    f = open(filename, 'wb')
    loading = True
    while (loading):
        line = socket.recv(1024)
        while (line):
            f.write(line)
            line = socket.recv(1024)
            if not line:
                loading = False
    f.close()
