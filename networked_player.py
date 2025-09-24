import socket

class player:
    def __init__(self, address:tuple = (None, None), id:int|None = None):
        self.x = 0
        self.y = 0
        self.address = address
        self.id = id
        self.last_message = None