import pygame
import socket
import time
import threading
from binary_messaging import binary_message, binary_message_handler

class client_player_entity:
    def __init__(self):
        self.x, self.y = 0, 0
        self.keys_down = {}

    def update(self, events:list[pygame.Event], dt:float):
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.keys_down[event.key] = True
            elif event.type == pygame.KEYUP:
                self.keys_down[event.key] = False

        if self.keys_down.get(pygame.K_UP, False) or self.keys_down.get(pygame.K_w, False):
            self.y -= 100 * dt
        if self.keys_down.get(pygame.K_DOWN, False) or self.keys_down.get(pygame.K_s, False):
            self.y += 100 * dt
        if self.keys_down.get(pygame.K_LEFT, False) or self.keys_down.get(pygame.K_a, False):
            self.x -= 100 * dt
        if self.keys_down.get(pygame.K_RIGHT, False) or self.keys_down.get(pygame.K_d, False):
            self.x += 100 * dt

        self.x = max(min(self.x, 720), 0)
        self.y = max(min(self.y, 360), 0)

    def render(self, screen:pygame.Surface):
        surface = pygame.Surface((32, 32))
        surface.fill((255, 0, 0))
        screen.blit(surface, surface.get_rect(center = (self.x, self.y)))

pygame.init()

screen = pygame.display.set_mode((640, 360))
clock = pygame.time.Clock()

HOST = "127.0.0.1"
PORT = 62743

def init():
    global client_player
    client_player = client_player_entity()

    global run 
    run = True

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "ii")
    ])

def start_threads():
    global thread_count
    thread_count = 0

    threading.Thread(target=listen_to_server()).start()

def main():
    global screen, clock, client_player, run

    dt = 0

    while run:
        dt = clock.tick() / 1000

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                run = False

        screen.fill((0, 0, 0))

        client_player.update(events, dt)
        client_player.render(screen)

        pygame.display.update()

    return

def listen_to_server():
    global run, thread_count

    thread_count += 1

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        client_socket.settimeout(1)
        print("awaiting connection...")
        try:
            client_socket.connect((HOST, PORT))
            print("connected to " + HOST + ":" + str(PORT))
        except:
            print("unable to connect to " + HOST + ":" + str(PORT))
            thread_count -= 1
            return
        
        while run:
            time.sleep(0.001)
    
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