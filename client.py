import pygame
import socket
import time
import threading
import secrets
import sys
from networking import *
from networking.binary_messaging import binary_message, binary_message_handler
import networked_player
from network_config import SERVER_IP, SERVER_TCP_PORT, SERVER_UDP_PORT
import assets
from networked_ball import ball

class player(networked_player.player):
    def __init__(self, address:tuple = (None, None), id:int|None = None, team:int = 0):
        super().__init__(address, id, team)
        self.old_position_message = None
        self.new_position_message = None
        self.lerp_time = 0

    def received_new_position_message(self, position_message:tuple):
        if self.old_position_message == None and self.new_position_message == None:
            self.old_position_message = position_message
            self.new_position_message = position_message
            self.lerp_time = 0
        else:
            if position_message[2] < self.new_position_message[2]:
                return
            self.old_position_message = self.new_position_message
            self.new_position_message = position_message
            self.lerp_time = 0

    def update(self, dt:float):
        if self.old_position_message != None and self.new_position_message != None:
            time_difference = (self.new_position_message[2] - self.old_position_message[2]) * 1000
            self.lerp_time += 1000 * dt
            self.lerp_time = min(self.lerp_time, time_difference)
            if time_difference == 0:
                self.x, self.y = self.new_position_message[0], self.new_position_message[1]
            else:
                self.x = pygame.math.lerp(self.old_position_message[0], self.new_position_message[0], self.lerp_time / time_difference)
                self.y = pygame.math.lerp(self.old_position_message[1], self.new_position_message[1], self.lerp_time / time_difference)

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
            self.y -= 120 * dt
        if keys_held.get(pygame.K_DOWN, False) or keys_held.get(pygame.K_s, False):
            self.y += 120 * dt
        if keys_held.get(pygame.K_LEFT, False) or keys_held.get(pygame.K_a, False):
            self.x -= 120 * dt
        if keys_held.get(pygame.K_RIGHT, False) or keys_held.get(pygame.K_d, False):
            self.x += 120 * dt
        
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

        self.old_position_message = None
        self.new_position_message = None
        self.lerp_time = 0

    def received_new_position_message(self, position_message:tuple):
        if self.old_position_message == None and self.new_position_message == None:
            self.old_position_message = position_message
            self.new_position_message = position_message
            self.lerp_time = 0
        else:
            if position_message[2] < self.new_position_message[2]:
                return
            self.old_position_message = self.new_position_message
            self.new_position_message = position_message
            self.lerp_time = 0

    def update(self, dt:float):
        if self.old_position_message != None and self.new_position_message != None:
            time_difference = (self.new_position_message[2] - self.old_position_message[2]) * 1000
            self.lerp_time += 1000 * dt
            self.lerp_time = min(self.lerp_time, time_difference)
            if time_difference == 0:
                self.x, self.y = self.new_position_message[0], self.new_position_message[1]
            else:
                self.x = pygame.math.lerp(self.old_position_message[0], self.new_position_message[0], self.lerp_time / time_difference)
                self.y = pygame.math.lerp(self.old_position_message[1], self.new_position_message[1], self.lerp_time / time_difference)

pygame.init()

screen = pygame.display.set_mode((640, 360))
clock = pygame.time.Clock()

MY_IP = networking.get_ip()
AVAILABLE_PORTS = [port for port in range(62743, 65535)]

def init():
    global my_player
    my_player = controllable_player(int.from_bytes(secrets.token_bytes(3), byteorder=sys.byteorder))

    global run
    run = True

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "iBiid"),
        binary_message("h", "ii"),
        binary_message("l", "d"),
        binary_message("H", "B"),
        binary_message("g", "IIiid")
    ])

    global players 
    players = {}

    global keys_held
    keys_held = {}

    global client_UDP_socket
    client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    global MY_UDP_PORT
    MY_UDP_PORT = networking.bind_socket_to_available_port(client_UDP_socket, MY_IP)
    client_UDP_socket.setblocking(False)

    global connected 
    connected = False

    global latency
    latency = 0

    global networked_ball
    networked_ball = ball()

    global blue_team_score
    blue_team_score = 0

    global yellow_team_score
    yellow_team_score = 0

def show_loading_screen():
    global screen

    screen.fill((0, 0, 0))
    screen.blit(assets.loading_screen, assets.loading_screen.get_rect(center = (320, 180)))

    pygame.display.update()

def start_threads():
    global thread_count
    thread_count = 0

    utils.thread(listen_to_server)
    utils.thread(communicate_with_server)
    utils.thread(check_for_timed_out_players)

def main():
    global screen, clock, my_player, run, keys_held, blue_team_score, yellow_team_score
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

        networked_ball.update(dt)

        for player in players.values():
            player.update(dt)
            
        for player in players.values():
            player.render(screen)

        if networked_ball.has_updated:
            screen.blit(assets.ball, assets.ball.get_rect(center = (networked_ball.x, networked_ball.y)))

        surface = assets.font.render(str(blue_team_score), False, (0, 212, 255))
        surface.set_colorkey((0, 0, 0))
        screen.blit(surface, surface.get_rect(topleft=(16, 16)))

        surface = assets.font.render(str(yellow_team_score), False, (255, 244, 0))
        surface.set_colorkey((0, 0, 0))
        screen.blit(surface, surface.get_rect(topright=(624, 16)))

        pygame.display.update()
        
        fps = clock.get_fps()
        if fps == float("inf"):
            fps = None
        else:
            fps = round(fps)

        pygame.display.set_caption("latency: " + str(round(latency, 4)) + " ms | fps: " + str(fps))

def alternate_main():
    global run, screen

    while run:
        dt = clock.tick(60) / 1000

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                run = False
        
        screen.fill((0, 0, 0))

        surface = assets.font.render("can't connect to server", False, (255, 255, 255))
        surface.set_colorkey((0, 0, 0))
        screen.blit(surface, surface.get_rect(center=(320, 180)))

        pygame.display.update()
        
        fps = clock.get_fps()
        if fps == float("inf"):
            fps = None
        else:
            fps = round(fps)

        pygame.display.set_caption("fps: " + str(fps))
    
def listen_to_server():
    global run, thread_count, my_player, players, client_UDP_socket, latency, networked_ball, blue_team_score, yellow_team_score

    thread_count += 1

    print("listening at " + MY_IP + ":" + str(MY_UDP_PORT))

    buffer = utils.buffer()

    time_manager = utils.time_manager()
        
    while run:
        try:
            data, address = client_UDP_socket.recvfrom(4096)
            if address != (MY_IP, MY_UDP_PORT):
                buffer.add_bytes(data)
        except BlockingIOError:
            continue
        except socket.timeout:
            continue
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            continue
            
        decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer.bytearray)
        if len(decrypted_messages) > 0:
            for message, data in zip(decrypted_messages, decrypted_data):
                if message == "p":
                    if data[0] != my_player.id:
                        if data[0] in players:
                            pass
                        else:
                            players[data[0]] = player(None, data[0], data[1])
                        players[data[0]].received_new_position_message((data[2], data[3], data[4]))
                        players[data[0]].team = data[1]
                        players[data[0]].last_message = time.time()
                elif message == "l":
                    latency = abs((time_manager.time() - data[0]) * 1000)
                elif message == "g":
                    blue_team_score, yellow_team_score = data[0], data[1]
                    networked_ball.received_new_position_message((data[2], data[3], data[4]))
                    networked_ball.has_updated = True
            
            del buffer.bytearray[:decrypted_data_length]
        
    print("stopped listening at " + MY_IP + ":" + str(MY_UDP_PORT))
                    
    thread_count -= 1
    return

def communicate_with_server():
    global run, thread_count, my_player, players, client_UDP_socket

    thread_count += 1

    time_manager = utils.time_manager()

    print("sending data though " + MY_IP + ":" + str(MY_UDP_PORT))

    while run:
        try:
            client_UDP_socket.sendto(
                message_handler.encrypt_message([("p", (my_player.id, my_player.team, round(my_player.x), round(my_player.y), time_manager.time()))]),
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
        networking.configure_TCP_socket(client_TCP_socket)
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

        buffer = utils.buffer()

        while run and handshake_completed == False:
            try:
                buffer.add_bytes(client_TCP_socket.recv(4096))
                decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer.bytearray)
                del buffer.bytearray[:decrypted_data_length]
                if len(decrypted_messages) > 0:
                    for message, data in zip(decrypted_messages, decrypted_data):
                        if message == "H":
                            my_player.team = data[0]
                            if data[0] == 0:
                                my_player.x = 160
                            elif data[0] == 1:
                                my_player.x = 480
                            my_player.y = 180
                            handshake_completed = True
            except socket.timeout:
                pass
            except (ConnectionAbortedError, ConnectionResetError):
                pass
        print("handshake with " + SERVER_IP + ":" + str(SERVER_TCP_PORT) + " completed")
        
    return
        
init()
show_loading_screen()
attempt_tcp_handshake()
if connected:
    start_threads()
    main()
    await_threads()
else:
    alternate_main()
print("program killed")