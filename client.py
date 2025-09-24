import pygame
import socket
import time
import threading
import secrets
import sys
from binary_messaging import binary_message, binary_message_handler
import networked_player
import global_time
from network_config import SERVER_IP, SERVER_TCP_PORT, SERVER_UDP_PORT

class player(networked_player.player):
    def render(self, screen:pygame.Surface, color:tuple):
        surface = pygame.Surface((32, 32))
        surface.fill(color)
        screen.blit(surface, surface.get_rect(center = (self.x, self.y)))

class controllable_player(player):
    def __init__(self, id:int):
        super().__init__(id=id)

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

pygame.init()

screen = pygame.display.set_mode((640, 360))
clock = pygame.time.Clock()

# MY_IP = "127.0.0.1"
MY_IP = socket.gethostbyname(socket.gethostname())
AVAILABLE_PORTS = [port for port in range(62743, 65535)]

def init():
    global my_player
    my_player = controllable_player(int.from_bytes(secrets.token_bytes(3), byteorder=sys.byteorder))

    global run 
    run = True

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "iii"),
        binary_message("h", "ii"),
        binary_message("l", "d")
    ])

    global players 
    players = {}

    global keys_held
    keys_held = {}

    global client_UDP_socket
    client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in AVAILABLE_PORTS:
        try:
            client_UDP_socket.bind((MY_IP, port))

            global MY_UDP_PORT
            MY_UDP_PORT = port
        except:
            pass
    client_UDP_socket.settimeout(1)

    global connected 
    connected = False

    global latency
    latency = 0

def start_threads():
    global thread_count
    thread_count = 0

    if connected:
        threading.Thread(target=listen_to_server).start()
        threading.Thread(target=communicate_with_server).start()
        threading.Thread(target=check_for_timed_out_players).start()

def main():
    global screen, clock, my_player, run, keys_held
    dt = 0

    while run:
        dt = clock.tick(60) / 1000

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                keys_held[event.key] = True
            elif event.type == pygame.KEYUP:
                keys_held[event.key] = False

        screen.fill((0, 0, 0))
        
        my_player.update(keys_held, dt)
        my_player.render(screen)
            
        for player in players.values():
            player.render(screen, (0, 255, 0))

        pygame.display.update()
        
        fps = clock.get_fps()
        if fps == float("inf"):
            fps = None
        else:
            fps = round(fps)

        pygame.display.set_caption("latency: " + str(round(latency, 4)) + " ms | fps: " + str(fps))
        
def listen_to_server():
    global run, thread_count, my_player, players, client_UDP_socket, latency

    thread_count += 1

    print("listening at " + MY_IP + ":" + str(MY_UDP_PORT))

    buffer = b""

    start_ntp_time = global_time.time()
    start_time = time.time()
        
    while run:
        try:
            data, address = client_UDP_socket.recvfrom(4096)
            if address != (MY_IP, MY_UDP_PORT):
                buffer = b"".join([buffer, data])
        except socket.timeout:
            continue
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            continue
            
        decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer)
        if len(decrypted_messages) > 0:
            for message, data in zip(decrypted_messages, decrypted_data):
                if message == "p":
                    if data[0] in players:
                        pass
                    else:
                        players[data[0]] = player(None, data[0])
                    players[data[0]].x, players[data[0]].y = data[1], data[2]
                    players[data[0]].last_message = time.time()
                elif message == "l":
                    latency = abs(((start_ntp_time + (time.time() - start_time)) - data[0]) * 1000)
            
            buffer = buffer[decrypted_data_length:]

    print("stopped listening at " + MY_IP + ":" + str(MY_UDP_PORT))
                    
    thread_count -= 1
    return

def communicate_with_server():
    global run, thread_count, my_player, players, client_UDP_socket

    thread_count += 1

    print("sending data though " + MY_IP + ":" + str(MY_UDP_PORT))

    while run:
        try:
            client_UDP_socket.sendto(
                message_handler.encrypt_message([("p", (my_player.id, round(my_player.x), round(my_player.y)))]),
                (SERVER_IP, SERVER_UDP_PORT)
            )
            time_since_last_message = 0
        except socket.timeout:
            pass
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            continue

    print("stopped sending data though " + MY_IP + ":" + str(MY_UDP_PORT))
                            
    thread_count -= 1
    return

def check_for_timed_out_players():
    global run, thread_count, players

    thread_count += 1

    while run:
        for player_id, player in players.copy().items():
            if time.time() - player.last_message > 10:
                del players[player_id]
        time.sleep(0.1)

    thread_count -= 1
    return

def await_threads():
    global thread_count
    while thread_count > 0:
        time.sleep(0.001)

    global client_UDP_socket
    try:
        client_UDP_socket.shutdown(0)
    except:
        client_UDP_socket.close()
    finally:
        pass

def attempt_tcp_handshake():
    global connected, my_player

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_TCP_socket:
        client_TCP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        client_TCP_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        client_TCP_socket.settimeout(1)
        print("awaiting tcp handshake...")
        try:
            client_TCP_socket.connect((SERVER_IP, SERVER_TCP_PORT))
            connected = True
        except:
            print("unable to establish TCP handshake with " + SERVER_IP + ":" + str(SERVER_UDP_PORT))
            return
        
        client_TCP_socket.sendall(
            message_handler.encrypt_message([("h", (my_player.id, MY_UDP_PORT))])
        )
        
        print("handshake with " + SERVER_IP + ":" + str(SERVER_TCP_PORT) + " completed")
    
    return
        
init()
attempt_tcp_handshake()
start_threads()
main()
await_threads()
print("program killed")