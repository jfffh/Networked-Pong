import socket

class player:
    def __init__(self, socket:socket.socket|None = None, address:tuple|None = (None, None), id:int|None = None):
        self.x = 0
        self.y = 0
        self.socket = socket
        self.address = address
        self.id = id