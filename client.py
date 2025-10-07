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
import assets
from networked_ball import ball

class player(networked_player.player):
    def render(self, screen:pygame.Surface):
        if self.team == 0:
            screen.blit(assets.blue_paddle, assets.blue_paddle.get_rect(center = (self.x, self.y)))
        elif self.team == 1:
            screen.blit(assets.yellow_paddle, assets.yellow_paddle.get_rect(center = (self.x, self.y)))

class controllable_player(player):
    def __init__(self, id:int):
        super().__init__(id=id)

    def update(self, keys_held:dict, dt:float):
        if keys_held.get(pygame.K_UP, False) or keys_held.get(pygame.K_w, False):
            self.y -= 180 * dt
        if keys_held.get(pygame.K_DOWN, False) or keys_held.get(pygame.K_s, False):
            self.y += 180 * dt
        if keys_held.get(pygame.K_LEFT, False) or keys_held.get(pygame.K_a, False):
            self.x -= 180 * dt
        if keys_held.get(pygame.K_RIGHT, False) or keys_held.get(pygame.K_d, False):
            self.x += 180 * dt
        
        if self.team == 0:
            self.x = max(min(self.x, 320), 0)
            self.y = max(min(self.y, 360), 0)
        elif self.team == 1:
            self.x = max(min(self.x, 640), 320)
            self.y = max(min(self.y, 360), 0)

class ball(ball):
    def __init__(self):
        super().__init__()
        self.has_updated = False

pygame.init()

screen = pygame.display.set_mode((640, 360))
clock = pygame.time.Clock()

for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
    if ip != "127.0.0.1":
        MY_IP = ip
MY_IP = "127.0.0.1"
AVAILABLE_PORTS = [port for port in range(62743, 65535)]

def init():
    global my_player
    my_player = controllable_player(int.from_bytes(secrets.token_bytes(3), byteorder=sys.byteorder))

    global run
    run = True

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "iBii"),
        binary_message("h", "ii"),
        binary_message("l", "d"),
        binary_message("H", "B"),
        binary_message("b", "ii")
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
    # client_UDP_socket.settimeout(1)
    client_UDP_socket.setblocking(False)

    global connected 
    connected = False

    global latency
    latency = 0

    global networked_ball
    networked_ball = ball()

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

        pygame.draw.line(screen, (255, 255, 255), (320, 0), (320, 360), 2)
        
        my_player.update(keys_held, dt)
        my_player.render(screen)
            
        for player in players.values():
            player.render(screen)

        if networked_ball.has_updated:
            screen.blit(assets.ball, assets.ball.get_rect(center = (networked_ball.x, networked_ball.y)))

        pygame.display.update()
        
        fps = clock.get_fps()
        if fps == float("inf"):
            fps = None
        else:
            fps = round(fps)

        pygame.display.set_caption("latency: " + str(round(latency, 4)) + " ms | fps: " + str(fps))
        
def listen_to_server():
    global run, thread_count, my_player, players, client_UDP_socket, latency, ball

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
        except BlockingIOError:
            continue
        except socket.timeout:
            continue
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            continue
            
        decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer)
        if len(decrypted_messages) > 0:
            for message, data in zip(decrypted_messages, decrypted_data):
                if message == "p":
                    if data[0] != my_player.id:
                        if data[0] in players:
                            pass
                        else:
                            players[data[0]] = player(None, data[0], data[1])
                        players[data[0]].team, players[data[0]].x, players[data[0]].y = data[1], data[2], data[3]
                        players[data[0]].last_message = time.time()
                elif message == "l":
                    latency = abs(((start_ntp_time + (time.time() - start_time)) - data[0]) * 1000)
                elif message == "b":
                    networked_ball.x, networked_ball.y = data[0], data[1]
                    networked_ball.has_updated = True
            
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
                message_handler.encrypt_message([("p", (my_player.id, my_player.team, round(my_player.x), round(my_player.y)))]),
                (SERVER_IP, SERVER_UDP_PORT)
            )
        except BlockingIOError:
            continue
        except socket.timeout:
            continue
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
        print("attempting tcp handshake...")
        try:
            client_TCP_socket.connect((SERVER_IP, SERVER_TCP_PORT))
            connected = True
        except:
            print("unable to establish TCP handshake with " + SERVER_IP + ":" + str(SERVER_UDP_PORT))
            return
        
        client_TCP_socket.sendall(
            message_handler.encrypt_message([("h", (my_player.id, MY_UDP_PORT))])
        )

        handshake_completed = False

        buffer = b""

        while run and handshake_completed == False:

            try:
                buffer = b"".join([client_TCP_socket.recv(4096)])
                decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer)
                if len(decrypted_messages) > 0:
                    buffer = buffer[decrypted_data_length:]
                    for message, data in zip(decrypted_messages, decrypted_data):

                        if message == "H":
                            my_player.team = data[0]
                            if data[0] == 0:
                                my_player.x = 160
                            elif data[0] == 1:
                                my_player.x = 480
                            my_player.y = 180
                            handshake_completed = True

                    buffer = buffer[decrypted_data_length:]
            except socket.timeout:
                pass
            except (ConnectionAbortedError, ConnectionResetError):
                pass
        print("handshake with " + SERVER_IP + ":" + str(SERVER_TCP_PORT) + " completed")
        
    return
        
init()
attempt_tcp_handshake()
start_threads()
main()
await_threads()
print("program killed")