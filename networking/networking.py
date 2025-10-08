import socket

AVAILABLE_PORTS = [port for port in range(62743, 65535)]

def bind_socket_to_available_port(socket:socket.socket, ip:str):
    for port in AVAILABLE_PORTS:
        try:
            socket.bind((ip, port))
            return port
        except:
            pass

def get_ip(allow_localhost:bool = False):
    for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
        if allow_localhost:
            return ip
        else:
            if ip != "127.0.0.1":
                return ip
            
def configure_TCP_socket(tcp_socket:socket.socket, timeout:int = 1):
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
    tcp_socket.settimeout(timeout)