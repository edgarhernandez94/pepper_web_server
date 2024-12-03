import socket
import struct
import cv2
import numpy as np
from PyQt6.QtWidgets import QTextEdit, QSlider, QGridLayout, QApplication, QMainWindow, QPushButton, QWidget, QLabel
from PyQt6.QtGui import QPixmap, QFont, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import json
import pyaudio
import threading
import speech_recognition as sr

HOST = '192.168.10.101'  # IP de Pepper
PORT = 12345  # Puerto para comandos de movimiento, voz y audio
VIDEO_PORT = 5000  # Puerto para la transmisión de video

def adjust_gamma(image, gamma=1.2):
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(image, table)

# Clase para recibir imágenes en un hilo separado
class ImageReceiver(QThread):
    new_image = pyqtSignal(np.ndarray)  # Señal para enviar imágenes al hilo principal

    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.host, self.port))

        try:
            while self.running:
                image = self.recibir_imagen(client_socket)
                if image is not None:
                    # Aplicar corrección de gamma para mejorar los colores
                    image = adjust_gamma(image, gamma=1.2)
                    self.new_image.emit(image)
                else:
                    break
        except Exception as e:
            print("Error en el hilo receptor:", e)
        finally:
            client_socket.close()

    def stop(self):
        self.running = False

    def recibir_imagen(self, client_socket):
        try:
            data_size = client_socket.recv(4)
            if not data_size:
                return None
            size = struct.unpack(">I", data_size)[0]
            
            data = b""
            while len(data) < size:
                packet = client_socket.recv(size - len(data))
                if not packet:
                    return None
                data += packet
            
            image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            return image #cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            print("Error al recibir la imagen:", e)
            return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interacting with Pepper")
        self.setGeometry(0, 0, 700, 850)  # Tamaño de la ventana principal
        self.is_audio_active = False

        # Inicializar el socket de comandos para Pepper
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            print("Conectado a Pepper para comandos")
        except Exception as e:
            print(f"Error al conectar con Pepper: {e}")
            self.client_socket = None

        # Configuración del layout y los widgets
        grid_layout = QGridLayout()
        self.setStyleSheet("background-color: white;")  # Configurar el color de fondo de la ventana principal

        # Configuración para recibir video
        self.video_label = QLabel()
        grid_layout.addWidget(self.video_label, 4, 6, 2, 2)  # Posición del video en 4,6 ocupando 2x2

        # Inicia el receptor de imágenes
        self.receiver = ImageReceiver('192.168.10.178', 5000)
        self.receiver.new_image.connect(self.update_image)
        self.receiver.start()

        # Widget para la imagen del logo
        self.logo_label = QLabel(self)
        self.logo_pixmap = QPixmap('Data/mirai_logo.png')  # Homologar ruta
        self.logo_pixmap = self.logo_pixmap.scaledToWidth(150)
        self.logo_label.setPixmap(self.logo_pixmap)

        # Configuración del título principal de la aplicación
        self.title_label = QLabel("Robot Avatar System Using Pepper")
        font_title = QFont('Arial', 40)
        self.title_label.setStyleSheet("color: darkblue;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(font_title)


        # Crear el QSlider para seleccionar los grados de right elbow
        self.degrees_slider_elbowr = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_elbowr.setRange(-100, 100)
        self.degrees_slider_elbowr.setTickInterval(10)
        self.degrees_slider_elbowr.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_elbowr.sliderReleased.connect(self.move_elbowr)
        grid_layout.addWidget(self.degrees_slider_elbowr, 8, 0, 1, 1)
        
        # Crear el QSlider para seleccionar los grados de left elbow
        self.degrees_slider_elbowl = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_elbowl.setRange(-100, 100)
        self.degrees_slider_elbowl.setTickInterval(10)
        self.degrees_slider_elbowl.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_elbowl.sliderReleased.connect(self.move_elbowl)
        grid_layout.addWidget(self.degrees_slider_elbowl, 8, 3, 1, 1)
        
        # Crear el QSlider para seleccionar los grados de right shoulder pitch
        self.degrees_slider_shoulderr = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_shoulderr.setRange(-100, 100)
        self.degrees_slider_shoulderr.setTickInterval(10)
        self.degrees_slider_shoulderr.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_shoulderr.sliderReleased.connect(self.move_shoulderr)
        grid_layout.addWidget(self.degrees_slider_shoulderr, 6, 1, 1, 1)
        
        # Crear el QSlider para seleccionar los grados de left shoulder pitch
        self.degrees_slider_shoulderl = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_shoulderl.setRange(-100, 100)
        self.degrees_slider_shoulderl.setTickInterval(10)
        self.degrees_slider_shoulderl.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_shoulderl.sliderReleased.connect(self.move_shoulderl)
        grid_layout.addWidget(self.degrees_slider_shoulderl, 6, 2, 1, 1)
        
        # Crear el QSlider para seleccionar los grados de right shoulder roll
        self.degrees_slider_shoulderr_r = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_shoulderr_r.setRange(-100, 100)
        self.degrees_slider_shoulderr_r.setTickInterval(10)
        self.degrees_slider_shoulderr_r.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_shoulderr_r.sliderReleased.connect(self.move_shoulderr_r)
        grid_layout.addWidget(self.degrees_slider_shoulderr_r, 7, 1, 1, 1)
        
        # Crear el QSlider para seleccionar los grados de left shoulder roll
        self.degrees_slider_shoulderl_r = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_shoulderl_r.setRange(-100, 100)
        self.degrees_slider_shoulderl_r.setTickInterval(10)
        self.degrees_slider_shoulderl_r.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_shoulderl_r.sliderReleased.connect(self.move_shoulderl_r)
        grid_layout.addWidget(self.degrees_slider_shoulderl_r, 7, 2, 1, 1)
        
        # Crear el QSlider para seleccionar los movimientos de la muñeca derecha
        self.degrees_slider_wristr = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_wristr.setRange(-100, 100)
        self.degrees_slider_wristr.setTickInterval(10)
        self.degrees_slider_wristr.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_wristr.sliderReleased.connect(self.move_wristr)
        grid_layout.addWidget(self.degrees_slider_wristr, 6, 0, 1, 1)
        
        # Crear el QSlider para seleccionar los movimientos de la muñeca izquierda
        self.degrees_slider_wristl = QSlider(Qt.Orientation.Horizontal)
        self.degrees_slider_wristl.setRange(-100, 100)
        self.degrees_slider_wristl.setTickInterval(10)
        self.degrees_slider_wristl.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.degrees_slider_wristl.sliderReleased.connect(self.move_wristl)
        grid_layout.addWidget(self.degrees_slider_wristl, 6, 3, 1, 1)

        # Widgets para la interacción del usuario
        self.label = QLabel("Select your movement:")
        font_lable = QFont('Helvetica', 18)
        font_lable.setItalic(True)
        self.label.setFont(font_lable)
        #self.input_line = QLineEdit()

        """ Definición de Botones """
        self.button_head_up = QPushButton("Up")
        self.button_head_up.clicked.connect(self.move_head_up)
        grid_layout.addWidget(self.button_head_up, 2, 0, 1, 1)
        self.button_head_up.setFixedSize(150, 80)
        
        self.button_head_down = QPushButton("Down")
        self.button_head_down.clicked.connect(self.move_head_down)
        grid_layout.addWidget(self.button_head_down, 3, 0, 1, 1)
        self.button_head_down.setFixedSize(150, 80)
        
        self.button_head_left = QPushButton("Left")
        self.button_head_left.clicked.connect(self.move_head_left)
        grid_layout.addWidget(self.button_head_left, 2, 2, 1, 1)
        self.button_head_left.setFixedSize(150, 80)
        
        self.button_head_right = QPushButton("Right")
        self.button_head_right.clicked.connect(self.move_head_right)
        grid_layout.addWidget(self.button_head_right, 3, 2, 1, 1)
        self.button_head_right.setFixedSize(150, 80)
    

        ## Configuración de imagen de cabeza de Pepper
        self.head_image_logo = QLabel(self)
        self.head_image = QPixmap('Data/head_logo.png')  ## Homologar ruta
        #self.head_image = self.head_image.scaledToWidth(150)
        self.head_image_logo.setPixmap(self.head_image)
        grid_layout.addWidget(self.head_image_logo, 2, 1, 2, 1)

        ## Configuración de imagen de mano izquierda de Pepper
        self.arml_image_logo = QLabel(self)
        self.arml_image = QPixmap('Data/Arm_left.png')
        self.arml_image_logo.setPixmap(self.arml_image)

        ## Configuración de imagen de mano derecha de Pepper
        self.armr_image_logo = QLabel(self)
        self.armr_image = QPixmap('Data/Arm_right.png') 
        self.armr_image_logo.setPixmap(self.armr_image)

        ## Configuración de imagen de codo derecho de Pepper
        self.elbowr_image_logo = QLabel(self)
        self.elbowr_image = QPixmap('Data/Elbow_right.png') 
        self.elbowr_image_logo.setPixmap(self.elbowr_image)

        ## Configuración de imagen de codo izquierdo de Pepper
        self.elbowl_image_logo = QLabel(self)
        self.elbowl_image = QPixmap('Data/Elbow_left.png') 
        self.elbowl_image_logo.setPixmap(self.elbowl_image)

        ## Configuración de imagen de hombro izquierdo de Pepper
        self.shoulderr_image_logo = QLabel(self)
        self.shoulderr_image = QPixmap('Data/Shoulder_right.png') 
        self.shoulderr_image_logo.setPixmap(self.shoulderr_image)


        ## Configuración de imagen de hombro derecho de Pepper
        self.shoulderl_image_logo = QLabel(self)
        self.shoulderl_image = QPixmap('Data/Shoulder_left.png') 
        self.shoulderl_image_logo.setPixmap(self.shoulderl_image)

        ## Resultados del perfil del cliente 
        self.result_label = QLabel("The movement required will be shown here.")
        self.result_label.setFont(font_lable)
        self.result_label.setWordWrap(True)

        # Especificaciones para font de subtítulos
        font_subtitle = QFont('Helvetica', 18)  
        font_subtitle.setBold(True)  # Hacer el subtítulo en negrita


        # Conectar botón a la función de procesamiento
        #self.button_head.clicked.connect(self.move_head)


        # Agregar widgets al layout, incluyendo la imagen del logo
        
        grid_layout.addWidget(self.logo_label, 0, 0, 1, 2)  # El logo en la fila 0, columna 0, que se extiende 1 fila y 3 columnas
        grid_layout.addWidget(self.title_label, 0, 1, 1, 4) # Agregar y configurar posición para el título al layout principal 
        grid_layout.addWidget(self.arml_image_logo, 5, 0)#, 1, 2)
        grid_layout.addWidget(self.elbowl_image_logo, 7, 0)
        
        grid_layout.addWidget(self.armr_image_logo, 5, 3)#, 1, 2)
        grid_layout.addWidget(self.elbowr_image_logo, 7, 3)
        grid_layout.addWidget(self.shoulderr_image_logo, 5, 1)
        grid_layout.addWidget(self.shoulderl_image_logo, 5, 2)

        grid_layout.addWidget(self.label, 1, 0, 1, 2)  # El label "Select your movement" en la fila 1, columna 0
    
        #grid_layout.addWidget(self.button_head, 3, 1, 1, 3)  # El botón "Head" en la fila 5, columna 1 ## PENDIENTE


        # Quitar scroll area y añadir QLabel directamente
        grid_layout.addWidget(self.result_label, 1, 2, 1, 2)  

        # Configurar un widget central y aplicar el layout
        central_widget = QWidget()
        central_widget.setLayout(grid_layout)
        self.setCentralWidget(central_widget)
        
        # Botón para indicar con voz lo que dirá Pepper
        self.speak_button = QPushButton("Talk to Pepper Speak", self)
        self.speak_button.clicked.connect(self.speech_to_text)
        #self.speak_button.clicked.connect(self.send_speak_command)
        #self.speak_button.move(200, 250)
        grid_layout.addWidget(self.speak_button, 4, 4, 1, 1)
        
        # Botón para que Pepper hable a partir del texto
        self.speak_button_text = QPushButton("Make Pepper Speak with text", self)
        self.speak_button_text.clicked.connect(self.send_speak_command)
        grid_layout.addWidget(self.speak_button_text, 6, 4, 1, 1)
        
    
        # Campo de texto para ingresar la frase a decir
        self.speak_text_input = QTextEdit(self)
        self.speak_text_input.setPlaceholderText("Enter phrase for Pepper to speak")
        #self.speak_text_input.move(200, 300)
        grid_layout.addWidget(self.speak_text_input, 4, 4, 3, 3)
        self.speak_text_input.setFixedSize(150, 80)
        
        # Botón para activar/desactivar la transmisión de audio
        self.audio_toggle_button = QPushButton("Toggle Pepper Listening", self)
        self.audio_toggle_button.clicked.connect(self.toggle_audio_stream)
        grid_layout.addWidget(self.audio_toggle_button, 7, 4, 1, 1)

    def closeEvent(self, event):
        """Cerrar la conexión al salir de la aplicación"""
        self.receiver.stop()
        self.receiver.wait()
        event.accept()

    def update_image(self, image):
        """Actualiza la imagen en la etiqueta de video"""
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_image))
    
    def connect_to_pepper(self):
        """Conecta al socket de Pepper"""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.pepper_ip, self.pepper_port))
            print("Conectado a Pepper")
        except Exception as e:
            print(f"Error al conectar con Pepper: {e}")
            self.client_socket = None
            
    def send_movement_command(self, joint, angle, speed):
        """Envía un comando de movimiento a Pepper"""
        if self.client_socket:
            command = {'action': 'move', 'joint': joint, 'angle': angle, 'speed': speed}
            data_to_send = (json.dumps(command) + "\n").encode('utf-8')
            self.client_socket.sendall(data_to_send)
            print(f"Enviado comando de movimiento: {command}")

    def send_speak_command(self):
        """Envía un comando para que Pepper hable"""
        if self.client_socket:
            text = self.speak_text_input.toPlainText()
            command = {'action': 'speak', 'text': text}
            data_to_send = (json.dumps(command) + "\n").encode('utf-8')
            self.client_socket.sendall(data_to_send)
            print(f"Enviado comando de voz: {command}")

    def closeEvent(self, event):
        """Cerrar la conexión al salir de la aplicación"""
        if self.client_socket:
            self.client_socket.close()
        event.accept()

    def move_head_up(self):
        self.result_label.setText(f"Moving Pepper's head up")
        print(f"Moving Pepper's head up")
        self.send_movement_command("HeadPitch", -1, 0.2)
        
    def move_head_down(self):
        self.result_label.setText(f"Moving Pepper's head down")
        print(f"Moving Pepper's head down")
        self.send_movement_command("HeadPitch", 1, 0.2)
        
    def move_head_left(self):
        self.result_label.setText(f"Moving Pepper's head left")
        print(f"Moving Pepper's head left")
        self.send_movement_command("HeadYaw", 1, 0.2)
        
    def move_head_right(self):
        self.result_label.setText(f"Moving Pepper's head right")
        print(f"Moving Pepper's head right")
        self.send_movement_command("HeadYaw", -1, 0.2)

    def move_armr(self):
        selected_degree = self.degrees_slider_elbowr.value()
        self.result_label.setText(f"Moving Pepper's Right Arm to {selected_degree} percent")
        print(f"Moving Pepper's Right Arm to {selected_degree} percent")

    def move_arml(self):
        selected_degree = self.degrees_slider_elbowr.value()
        self.result_label.setText(f"Moving Pepper's Left Arm to {selected_degree} percent")
        print(f"Moving Pepper's Left Arm to {selected_degree} percent")

    def move_elbowr(self):
        selected_degree = self.degrees_slider_elbowr.value()
        self.result_label.setText(f"Moving Pepper's Right Elbow to {selected_degree} percent")
        print(f"Moving Pepper's Right Elbow to {selected_degree} percent")
        selected_degree = (selected_degree*1.5)/100
        #print(f"Selected degree: {selected_degree}")
        self.send_movement_command("RElbowRoll", selected_degree, 0.2)

    def move_elbowl(self):
        selected_degree = self.degrees_slider_elbowl.value()
        self.result_label.setText(f"Moving Pepper's Left Elbow to {selected_degree} percent")
        print(f"Moving Pepper's Left Elbow to {selected_degree} percent")
        selected_degree = ((selected_degree*1.5)/100)*-1
        self.send_movement_command("LElbowRoll", selected_degree, 0.2)

    def move_shoulderr(self):
        selected_degree = self.degrees_slider_shoulderr.value()
        self.result_label.setText(f"Moving Pepper's Right Shoulder to {selected_degree} percent")
        print(f"Moving Pepper's Right Shoulder to {selected_degree} percent")
        selected_degree = ((selected_degree*1.5)/100)*-1
        self.send_movement_command("RShoulderPitch", selected_degree, 0.2)

    def move_shoulderl(self):
        selected_degree = self.degrees_slider_shoulderl.value()
        self.result_label.setText(f"Moving Pepper's Left Shoulder to {selected_degree} percent")
        print(f"Moving Pepper's Left Shoulder to {selected_degree} percent")
        selected_degree = ((selected_degree*1.5)/100)*-1
        self.send_movement_command("LShoulderPitch", selected_degree, 0.2)

    def move_shoulderr_r(self):
        selected_degree = self.degrees_slider_shoulderr.value()
        self.result_label.setText(f"Moving Pepper's Right Shoulder Roll to {selected_degree} percent")
        print(f"Moving Pepper's Right Shoulder  Rollto {selected_degree} percent")
        selected_degree = ((selected_degree*1.5)/100)*-1
        self.send_movement_command("RShoulderRoll", selected_degree, 0.2)

    def move_shoulderl_r(self):
        selected_degree = self.degrees_slider_shoulderl.value()
        self.result_label.setText(f"Moving Pepper's Left Shoulder Roll to {selected_degree} percent")
        print(f"Moving Pepper's Left Shoulder Roll to {selected_degree} percent")
        selected_degree = (selected_degree*1.5)/100
        self.send_movement_command("LShoulderRoll", selected_degree, 0.2)
    
    def move_wristr(self):
        selected_degree = self.degrees_slider_wristr.value()
        self.result_label.setText(f"Moving Pepper's Right Wrist to {selected_degree} percent")
        print(f"Moving Pepper's Right Wrist to {selected_degree} percent")
        selected_degree = (selected_degree*1.5)/100
        self.send_movement_command("RWristYaw", selected_degree, 0.2)

    def move_wristl(self):
        selected_degree = self.degrees_slider_wristl.value()
        self.result_label.setText(f"Moving Pepper's Left Wrist to {selected_degree} percent")
        print(f"Moving Pepper's Left Wrist to {selected_degree} percent")
        selected_degree = (selected_degree*1.5)/100
        self.send_movement_command("LWristYaw", selected_degree, 0.2)

    def speech_to_text(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.speak_text_input.setText("Listening...")
            audio = recognizer.listen(source)
            try:
                text = recognizer.recognize_google(audio, language="es-MX")  # Usando el reconocedor de Google, Inglés (Estados Unidos): "en-US" 
                self.speak_text_input.setText(text)
                if self.client_socket:
                    command = {'action': 'speak', 'text': text}
                    data_to_send = (json.dumps(command) + "\n").encode('utf-8')
                    self.client_socket.sendall(data_to_send)
                    print(f"Enviado comando de voz: {command}")
            except sr.UnknownValueError:
                self.speak_text_input.setText("No se entendió el audio")
            except sr.RequestError:
                self.speak_text_input.setText("Error en la solicitud de Speech Recognition")
                
                """Envía un comando para que Pepper hable"""

    def toggle_audio_stream(self):
        """Activa o desactiva la transmisión de audio de Pepper"""
        if not self.is_audio_active:
            # Iniciar la transmisión de audio
            if self.client_socket:
                command = {'action': 'start_audio'}
                self.client_socket.sendall((json.dumps(command) + "\n").encode('utf-8'))
                self.is_audio_active = True
                self.start_audio_receiver()
                print("Transmisión de audio activada")
        else:
            # Detener la transmisión de audio
            if self.client_socket:
                command = {'action': 'stop_audio'}
                self.client_socket.sendall((json.dumps(command) + "\n").encode('utf-8'))
                self.is_audio_active = False
                self.stop_audio_receiver()
                print("Transmisión de audio desactivada")

    def start_audio_receiver(self):
        """Inicia el receptor de audio en un hilo separado"""
        self.audio_thread = threading.Thread(target=self.receive_audio_stream)
        self.audio_thread.start()

    def receive_audio_stream(self):
        """Recibe el audio de Pepper y lo reproduce en tiempo real"""
        p = pyaudio.PyAudio()
        self.audio_stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, output=True)

        # Configurar socket de audio para recibir desde Pepper
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.audio_socket.bind(('', 5555))
        self.audio_socket.listen(1)
        conn, addr = self.audio_socket.accept()
        print(f"Conexión de audio establecida con {addr}")

        try:
            while self.is_audio_active:
                audio_data = conn.recv(128)
                if audio_data:
                    self.audio_stream.write(audio_data)
        except Exception as e:
            print(f"Error en la recepción de audio: {e}")
        finally:
            conn.close()

    def stop_audio_receiver(self):
        """Detiene la recepción de audio"""
        if self.audio_socket:
            self.audio_socket.close()
            self.audio_socket = None
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None


# Crear una aplicación y ventana principal
app = QApplication([])
window = MainWindow()
window.show()

# Ejecutar la aplicación
app.exec()
