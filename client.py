import pygame
import socket
import time
import threading
import secrets
import sys
from binary_messaging import binary_message, binary_message_handler
import networked_player
from network_config import HOST, PORT

class player(networked_player.player):
    def render(self, screen:pygame.Surface, color:tuple):
        surface = pygame.Surface((32, 32))
        surface.fill(color)
        screen.blit(surface, surface.get_rect(center = (self.x, self.y)))

class controllable_player(player):
    def __init__(self, socket:socket.socket|None, id:int):
        super().__init__(socket=socket, id=id)

    def update(self, keys_held:dict, dt:float):
        if keys_held.get(pygame.K_UP, False) or keys_held.get(pygame.K_w, False):
            self.y -= 100 * dt
        if keys_held.get(pygame.K_DOWN, False) or keys_held.get(pygame.K_s, False):
            self.y += 100 * dt
        if keys_held.get(pygame.K_LEFT, False) or keys_held.get(pygame.K_a, False):
            self.x -= 100 * dt
        if keys_held.get(pygame.K_RIGHT, False) or keys_held.get(pygame.K_d, False):
            self.x += 100 * dt

        self.x = max(min(self.x, 720), 0)
        self.y = max(min(self.y, 360), 0)

    def render(self, screen:pygame.Surface):
        return super().render(screen, (255, 0, 0))
    
    def update_server(self):
        global message_handler
        try:
            self.socket.sendall(message_handler.encrypt_message([
                ("p", (self.id, round(self.x), round(self.y)))
            ]))
        except:
            pass

pygame.init()

screen = pygame.display.set_mode((640, 360))
clock = pygame.time.Clock()

def init():
    global my_player
    my_player = controllable_player(None, int.from_bytes(secrets.token_bytes(4), byteorder=sys.byteorder))

    global run 
    run = True

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "iii"),
        binary_message("l", "d")
    ])

    global players 
    players = {}

    global has_succesfully_connected_with_server
    has_succesfully_connected_with_server = False

    global trying_to_connect_to_server
    trying_to_connect_to_server = False

    global keys_held
    keys_held = {}

    global ping 
    ping = None

    global average_pings
    average_pings = []

def start_threads():
    global thread_count
    thread_count = 0

    threading.Thread(target=listen_to_server).start()

def main():
    global screen, clock, my_player, run, keys_held, ping, average_pings

    dt = 0

    while run:
        dt = clock.tick() / 1000

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                keys_held[event.key] = True
            elif event.type == pygame.KEYUP:
                keys_held[event.key] = False
        
        if keys_held.get(pygame.K_LCTRL, False) and keys_held.get(pygame.K_r, False) and has_succesfully_connected_with_server == False and trying_to_connect_to_server == False:
            threading.Thread(target=listen_to_server).start()

        screen.fill((0, 0, 0))
        
        my_player.update(keys_held, dt)
        my_player.update_server()
        my_player.render(screen)
            
        for player in players.values():
            player.render(screen, (0, 255, 0))

        pygame.display.update()

        if len(average_pings) > 0:
            ping = sum(average_pings) / len(average_pings) * 1000
        
        pygame.display.set_caption("ping: " + str(ping) + "ms")

def listen_to_server():
    global run, thread_count, my_player, players, has_succesfully_connected_with_server, trying_to_connect_to_server, ping

    thread_count += 1

    trying_to_connect_to_server = True

    my_player.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    with my_player.socket:
        my_player.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        my_player.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        my_player.socket.settimeout(1)
        print("awaiting connection...")
        try:
            my_player.socket.connect((HOST, PORT))
            print("connected to " + HOST + ":" + str(PORT))
            has_succesfully_connected_with_server = True
            trying_to_connect_to_server = False
        except:
            print("unable to connect to " + HOST + ":" + str(PORT))
            trying_to_connect_to_server = False
            thread_count -= 1
            return
                
        time_since_last_message = 0

        buffer = b""
        
        while run:
            try:
                buffer = b"".join([my_player.socket.recv(4096)])
                decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer)
                if len(decrypted_messages) > 0:
                    for message, data in zip(decrypted_messages, decrypted_data):
                        if message == "p":
                            player_id = data[0]
                            if player_id in players:
                                players[player_id].x, players[player_id].y = data[1], data[2]
                            else:
                                players[player_id] = player(id=player_id)
                                players[player_id].x, players[player_id].y = data[1], data[2]
                        if message == "l":
                            average_pings.append(time.time() - data)
                            if len(average_pings) > 50:
                                average_pings.pop(0)
                    time_since_last_message = 0
            except socket.timeout:
                pass
            except (ConnectionAbortedError, ConnectionResetError):
                pass
            time.sleep(0.001)
            time_since_last_message += 0.001
    
            if time_since_last_message > 10:
                break
            
        my_player.socket.shutdown(0)
        print("connection with " + HOST + ":" + str(PORT) + " terminated")
        has_succesfully_connected_with_server = False
    
    thread_count -= 1
    return

def await_threads():
    global thread_count
    while thread_count > 0:
        time.sleep(0.001)

init()
start_threads()
main()
await_threads()
print("program killed")