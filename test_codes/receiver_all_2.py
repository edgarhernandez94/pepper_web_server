# -*- coding: utf-8 -*-
import qi
import socket
import struct
import time
import cv2
import numpy as np
import json
import subprocess
import threading

# Configuracion de host y puertos
HOST = '192.168.10.101' ## IP de pepper
PORT = 12345  # Puerto para los comandos de movimiento, audio y voz
VIDEO_PORT = 5000  # Puerto para la transmision de video
SERVER_IP = '192.168.10.153'  # IP de tu computadora para recibir audio
SERVER_PORT = 5555  # Puerto de tu computadora para recibir audio

audio_process = None  # Variable global para el proceso de audio
audio_socket = None   # Variable global para el socket de audio

def enviar_imagen(conn, video_service):
    """Transmite imagenes de video a traves del socket"""
    resolution = 2  
    color_space = 11  
    fps = 15  
    name_id = video_service.subscribeCamera("python_client", 0, resolution, color_space, fps)
    
    try:
        while True:
            image = video_service.getImageRemote(name_id)
            if image is not None:
                width, height = image[0], image[1]
                image_data = np.frombuffer(image[6], dtype=np.uint8).reshape((height, width, 3))
                
                _, jpeg_data = cv2.imencode('.jpg', image_data, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                
                try:
                    conn.sendall(struct.pack(">I", len(jpeg_data)))
                    conn.sendall(jpeg_data)
                except socket.error:
                    print("El cliente cerro la conexion.")
                    break
            time.sleep(1.0 / fps)
    finally:
        video_service.unsubscribe(name_id)

def manejar_comando(command):
    """Procesa los comandos JSON y ejecuta la accion correspondiente"""
    global audio_process, audio_socket

    if command['action'] == 'move':
        movimiento_comando = "qicli call ALMotion.setAngles \"{}\" {} {}".format(
            command['joint'], command['angle'], command['speed']
        )
        print("Ejecutando movimiento: {}".format(movimiento_comando))
        thread = threading.Thread(target=ejecutar_comando, args=(movimiento_comando,))
        thread.start()
        
    elif command['action'] == 'speak':
        texto_comando = "qicli call ALTextToSpeech.say \"{}\"".format(command['text'])
        print("Ejecutando texto a voz: {}".format(texto_comando))
        thread = threading.Thread(target=ejecutar_comando, args=(texto_comando,))
        thread.start()
    
    elif command['action'] == 'start_audio':
        # Iniciar transmision de audio
        if audio_process is None:
            print("Iniciando transmision de audio...")
            audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            audio_socket.connect((SERVER_IP, SERVER_PORT))
            audio_process = subprocess.Popen(["arecord", "-f", "cd", "-t", "raw"], stdout=subprocess.PIPE)
            threading.Thread(target=transmitir_audio).start()

    elif command['action'] == 'stop_audio':
        # Detener transmision de audio
        if audio_process is not None:
            print("Deteniendo transmision de audio...")
            audio_process.terminate()
            audio_process = None
            if audio_socket:
                audio_socket.close()
                audio_socket = None

def ejecutar_comando(comando):
    """Ejecuta un comando en un hilo separado"""
    subprocess.call(comando, shell=True)

def transmitir_audio():
    """Envia el audio capturado a la computadora"""
    global audio_process, audio_socket
    try:
        while audio_process and audio_socket:
            audio_data = audio_process.stdout.read(128)  # Tamano de fragmento reducido
            if audio_data:
                audio_socket.sendall(audio_data)
    except Exception as e:
        print("Error en la transmision de audio: ", e)
    finally:
        if audio_socket:
            audio_socket.close()
            audio_socket = None

def iniciar_transmision_video():
    """Inicia la transmision de video en un hilo separado"""
    app = qi.Application()
    app.start()
    session = app.session
    video_service = session.service("ALVideoDevice")
    
    video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_socket.bind(('0.0.0.0', VIDEO_PORT))
    video_socket.listen(1)
    print("Esperando conexion de video...")

    try:
        conn, addr = video_socket.accept()
        print("Conexion de video establecida con {}".format(addr))
        enviar_imagen(conn, video_service)
    finally:
        conn.close()
        video_socket.close()
        app.stop()

def main():
    """Funcion principal que maneja la conexion de comandos y la transmision de video"""
    # Inicia la transmision de video en un hilo separado
    video_thread = threading.Thread(target=iniciar_transmision_video)
    video_thread.start()

    # Configuracion del socket para comandos
    command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    command_socket.bind((HOST, PORT))
    command_socket.listen(5)
    print("Esperando conexion para comandos...")

    try:
        conn, addr = command_socket.accept()
        print("Conexion de comandos establecida con {}".format(addr))
        
        buffer = ""
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            buffer += data
            
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                command = json.loads(line)
                manejar_comando(command)
    finally:
        conn.close()
        command_socket.close()
        if audio_process:
            audio_process.terminate()

if __name__ == "__main__":
    main()
