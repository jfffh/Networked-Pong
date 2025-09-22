import time
import socket
import threading
from binary_messaging import binary_message, binary_message_handler
from networked_player import player
from server_network_config import HOST, PORT
import global_time

def init():
    global run 
    run = True

    global thread_count
    thread_count = 0

    global message_handler
    message_handler = binary_message_handler([
        binary_message("p", "iii"),
        binary_message("l", "d")
    ])

    global players 
    players = []

def start_threads():
    threading.Thread(target=listen_for_connections).start()

def main():
    global run
    
    try:
        while run:
            time.sleep(0.05)
    except KeyboardInterrupt:
        run = False

def listen_for_connections():
    global thread_count, run, players

    thread_count += 1

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        server_socket.bind((HOST, PORT))

        print("listening at: " + HOST + ":" + str(PORT))
        while run:
            server_socket.settimeout(1)
            server_socket.listen()
            try:
                connection, address = server_socket.accept()
                print("new connection at: ", address[0] + ":" + str(address[1]))
                new_player = player(connection, address)
                players.append(new_player)
                threading.Thread(target=handle_connection, args=[new_player]).start()
            except socket.timeout:
                continue
            time.sleep(0.01)

        server_socket.close()

    thread_count -= 1
    return

def handle_connection(target_player:player):
    global thread_count, run, players

    thread_count += 1

    target_player.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    target_player.socket.settimeout(1)

    buffer = b""

    time_since_last_message = 0

    start_ntp_time = global_time.time()
    start_time = time.time()

    with target_player.socket:
        while run:
            try:
                buffer = b"".join([target_player.socket.recv(4096)])
                decrypted_messages, decrypted_data, decrypted_data_length = message_handler.decrypt_message(buffer)
                if len(decrypted_messages) > 0:
                    buffer = buffer[decrypted_data_length:]
                    time_since_last_message = 0
                    for message, data in zip(decrypted_messages, decrypted_data):
                        if message == "p":
                            target_player.id, target_player.x, target_player.y = data
            except socket.timeout:
                pass
            except (ConnectionAbortedError, ConnectionResetError):
                pass

            try:
                messages = []
                for player in players:
                    if player.id != None and player.id != target_player.id:
                        messages.append(("p", (player.id, player.x, player.y)))
                messages.append(("l", (start_ntp_time + (time.time() - start_time),)))
                if len(messages) > 0:
                    target_player.socket.send(message_handler.encrypt_message(messages))
            except socket.timeout:
                pass
            except OSError:
                pass
            time.sleep(0.001)
            time_since_last_message += 0.001
    
            if time_since_last_message > 10:
                break
                
        target_player.socket.shutdown(0)
        print("connection with " + player.address[0] + ":" + str(player.address[1]) + " terminated")
        if player in players:
            players.remove(player)
    
    thread_count -= 1

def await_threads():
    global thread_count
    while thread_count > 0:
        time.sleep(0.001)

init()
start_threads()
main()
await_threads()
print("server killed")
