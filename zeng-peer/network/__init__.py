import socket
import threading


def tcp_server_socket(bind_ip, bind_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((bind_ip, bind_port))
    server.listen(5)

    return server


def tcp_thread_target(tcp_socket, target_handler):
    # Pode ser importante aplicar uma global aqui
    while True:
        client, addr = tcp_socket.accept()
        log_debug("[TCP] Accepted connection from %s:%d" % (addr[0], addr[1]),
                  prefix='tcp')
        client_handler = threading.Thread(target=target_handler,
                                          args=(client, addr,))
        client_handler.start()

    log_debug('[TCP] Shutting down TCP Server', prefix='tcp')
    tcp_socket.close()


def start_tcp_server(bind_ip, bind_port, target_handler):
    server_socket = tcp_server_socket(bind_ip, bind_port)
    tcp_thread_target(server_socket, target_handler)
