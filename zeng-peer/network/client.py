import socket


def create_client_socket(target_host, target_port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((target_host, target_port))

    return client

# client = create_client_socket('127.0.0.1', 8090)
#
#
# msg = raw_input('Enter message to send : ')
# client.send(msg)
# response = client.recv(4096)
#
# print response
#
# client.close()
