import time
import socket
import threading
import random
from binary_messaging import binary_message, binary_message_handler
import networked_player
import global_time
from network_config import SERVER_IP, SERVER_TCP_PORT, SERVER_UDP_PORT
from networked_ball import ball
import pygame
import math

pygame.init()

class player(networked_player.player):
    def __init__(self, address:tuple = (None, None), id:int|None = None, team:int = 0):
        super().__init__(address, id, team)
        self.buffer = b""

class ball(ball):
    def __init__(self):
        super().__init__()
        self.reset()
        self.time = time.time()

    def update(self, players:dict[tuple:player], dt:float):
        global yellow_team_score, blue_team_score

        if time.time() - self.time > 5:
            self.x += self.speed_x * dt; self.y += self.speed_y * dt

            if self.y > 360:
                self.y = 360
                self.speed_y *= -1
            elif self.y < 0:
                self.y = 0
                self.speed_y *= -1

            if self.x > 640:
                blue_team_score += 1
                self.reset()
            elif self.x < 0:
                yellow_team_score += 1
                self.reset()

            player_rect = pygame.Rect(0, 0, 8, 32)

            for player in players.copy().values():
                player_rect.center = (player.x, player.y)
                if player_rect.collidepoint((self.x, self.y)):
                    if self.speed_x < 0:
                        self.x = player_rect.right + 1
                        self.speed_x *= -1
                        self.speed_y = -((player.y - self.y) / 0.053)
                    elif self.speed_x > 0:
                        self.x = player_rect.left - 1
                        self.speed_x *= -1
                        self.speed_y = -((player.y - self.y) / 0.053)
        else:
            pass
    
    def reset(self):
        self.x, self.y = 320, 180
        if random.randint(0, 1) == 0:
            self.speed_x = 150
        else:
            self.speed_x = -150
        self.speed_y = 0
        self.time = time.time()

def init():
    global run 
    run = True

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "iBii"),
        binary_message("h", "ii"),
        binary_message("l", "d"),
        binary_message("H", "B"),
        binary_message("g", "IIii"),
    ])

    global players
    players = {}

    global server_UDP_socket 
    server_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_UDP_socket.bind((SERVER_IP, SERVER_UDP_PORT))
    server_UDP_socket.setblocking(False)

    global networked_ball 
    networked_ball = ball()

    global blue_team_score
    blue_team_score = 0

    global yellow_team_score
    yellow_team_score = 0

def start_threads():
    global thread_count
    thread_count = 0

    threading.Thread(target=listen_to_clients).start()
    threading.Thread(target=communicate_with_clients).start()
    threading.Thread(target=listen_for_TCP_handshakes).start()
    threading.Thread(target=check_for_timed_out_players).start()

def main():
    global run, networked_ball, players

    try:
        clock = pygame.Clock()
        while run:
            dt = clock.tick(60) / 1000
            if len(players) >= 2:
                networked_ball.update(players, dt)
            else:
                networked_ball.reset()
    except KeyboardInterrupt:
        run = False

def listen_to_clients():
    global thread_count, run, players, server_UDP_socket

    thread_count += 1

    print("listening at " + SERVER_IP + ":" + str(SERVER_UDP_PORT))

    while run:
        try:
            data, address = server_UDP_socket.recvfrom(4096)
        except BlockingIOError:
            continue
        except socket.timeout:
            continue
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            continue
        
        if address == (SERVER_IP, SERVER_UDP_PORT):
            continue

        if address in players:
            pass
        else:
            print("connection from " + address[0] + ":" + str(address[1]) + " was attempted prior to handshake")
            continue

        networked_player:player = players[address]
        networked_player.last_message = time.time()
        networked_player.buffer = b"".join([networked_player.buffer, data])

        decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(networked_player.buffer)
        if len(decrypted_messages) > 0:
            for message, data in zip(decrypted_messages, decrypted_data):
                if message == "p":
                    networked_player.id, networked_player.team, networked_player.x, networked_player.y = data
                        
        networked_player.buffer = networked_player.buffer[decrypted_data_length:]

    print("stopped listening at " + SERVER_IP + ":" + str(SERVER_UDP_PORT))

    thread_count -= 1
    return

def communicate_with_clients():
    global thread_count, run, players, server_UDP_socket, networked_ball, blue_team_score, yellow_team_score

    thread_count += 1

    print("sending data though " + SERVER_IP + ":" + str(SERVER_UDP_PORT))

    start_ntp_time = global_time.time()
    start_time = time.time()

    while run:
        messages = [("l", (start_ntp_time + (time.time() - start_time),))]
        for networked_player in players.copy().values():
            if networked_player.id != None:
                messages.append(("p", (networked_player.id, networked_player.team, networked_player.x, networked_player.y)))
        messages.append(("g", (blue_team_score, yellow_team_score, round(networked_ball.x), round(networked_ball.y))))
        data = message_handler.encrypt_message(messages)
        for player_address in players.copy().keys():
            try:
                server_UDP_socket.sendto(data, player_address)
            except BlockingIOError:
                continue
            except socket.timeout:
                continue
            except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
                continue

    print("stopped sending data though " + SERVER_IP + ":" + str(SERVER_UDP_PORT))

    thread_count -= 1
    return

def listen_for_TCP_handshakes():
    global thread_count, run, players

    thread_count += 1

    print("listening for handshakes at " + SERVER_IP + ":" + str(SERVER_TCP_PORT))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_TCP_socket:
        server_TCP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        server_TCP_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        server_TCP_socket.settimeout(1)
        server_TCP_socket.bind((SERVER_IP, SERVER_TCP_PORT))
        while run:
            server_TCP_socket.listen()
            try:
                connection, address = server_TCP_socket.accept()
                threading.Thread(target=handle_TCP_handshake, args=[connection, address]).start()
            except socket.timeout:
                continue

    print("stopped listening for handshakes at " + SERVER_IP + ":" + str(SERVER_TCP_PORT))

    thread_count -= 1
    return

def handle_TCP_handshake(handshake_socket:socket.socket, address:tuple):
    global thread_count, run, players

    thread_count += 1

    handshake_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    handshake_socket.settimeout(1)

    handshake_completed = False

    buffer = b""


    print("handling handshake with: ", address[0] + ":" + str(address[1]))

    while run and handshake_completed == False:
        try:
            buffer = b"".join([handshake_socket.recv(4096)])
            decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer)
            if len(decrypted_messages) > 0:
                buffer = buffer[decrypted_data_length:]
                for message, data in zip(decrypted_messages, decrypted_data):
                    if message == "h":
                        blue_team = 0
                        yellow_team = 0
                        for networked_player in players.values():
                            if networked_player.team == 0:
                                blue_team += 1
                            elif networked_player.team == 1:
                                yellow_team += 1

                        if blue_team > yellow_team:
                            team = 1
                        elif blue_team < yellow_team:
                            team = 0
                        else:
                            team = random.randint(0, 1)
                        
                        if team == 0:
                            print("the new player has been assigned to the blue team")
                        else:
                            print("the new player has been assigned to the yellow team")

                        players[(address[0], data[1])] = player(address, data[0], team)
                        handshake_socket.sendall(
                            message_handler.encrypt_message([
                                ("H", (team,))
                            ])
                        )
                        handshake_completed = True
                buffer = buffer[decrypted_data_length:]
        except socket.timeout:
            pass
        except (ConnectionAbortedError, ConnectionResetError):
            pass

    handshake_socket.close()

    print("handshake with " + address[0] + ":" + str(address[1]) + " completed")
    
    thread_count -= 1

def check_for_timed_out_players():
    global thread_count, run, players

    thread_count += 1

    while run:
        for player_address, player in players.copy().items():
            if player.last_message != None:
                if time.time() - player.last_message > 10:
                    print("player at " + player_address[0] + ":" + str(player_address[1]) + " timed out")
                    del players[player_address]
        time.sleep(1)

    thread_count -= 1
    return

def await_threads():
    global thread_count
    while thread_count > 0:
        time.sleep(0.001)

    global server_UDP_socket
    try:
        server_UDP_socket.shutdown(0)
    except:
        server_UDP_socket.close()
    finally:
        pass

init()
start_threads()
main()
await_threads()
print("server killed")