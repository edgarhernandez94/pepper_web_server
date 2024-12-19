# audio_server.py
import socket
import subprocess
import threading

HOST = '0.0.0.0'  # Escuchar en todas las interfaces
PORT = 6000       # Puerto exclusivo para audio

def handle_client(conn):
    """Transmite audio al cliente."""
    print("Cliente conectado para transmisin de audio.")
    audio_process = subprocess.Popen(["arecord", "-f", "cd", "-t", "raw"], stdout=subprocess.PIPE)

    try:
        while True:
            audio_data = audio_process.stdout.read(4096)
            if not audio_data:
                break
            conn.sendall(audio_data)
    except Exception as e:
        print("Error streaming audio: {}".format(e))
    finally:
        print("Cliente desconectado.")
        audio_process.terminate()
        conn.close()

def start_audio_server():
    """Inicia el servidor de audio."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(conn,)).start()

if __name__ == "__main__":
    start_audio_server()
