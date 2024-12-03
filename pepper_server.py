from flask import Flask, render_template, request, Response, jsonify
import qi
import numpy as np
import threading
import logging
import time
from PIL import Image
import io

# Configurar el logger
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Conectar a los servicios de Pepper
session = qi.Session()

def connect_to_pepper():
    connected = False
    while not connected:
        try:
            session.connect("tcp://127.0.0.1:9559")
            connected = True
            logging.info("Conectado a la sesin de Pepper.")
        except RuntimeError as e:
            logging.error("No se puede conectar a Pepper: %s", e)
            logging.info("Reintentando en 5 segundos...")
            time.sleep(5)

connect_to_pepper()

# Inicializar Pepper
def initialize_pepper():
    global motion_service, autonomous_life_service
    try:
        # Acceder a los servicios ALAutonomousLife y ALMotion
        autonomous_life_service = session.service("ALAutonomousLife")
        motion_service = session.service("ALMotion")

        # Desactivar Autonomous Life
        autonomous_life_service.setState("disabled")
        logging.info("Autonomous Life desactivado.")

        # Despertar a Pepper
        motion_service.wakeUp()
        logging.info("Pepper se ha despertado exitosamente.")
    except Exception as e:
        logging.error("Error al inicializar Pepper: %s", e)

initialize_pepper()

# Inicializar otros servicios
try:
    tts_service = session.service("ALTextToSpeech")
    logging.info("Servicio ALTextToSpeech inicializado exitosamente.")
except Exception as e:
    logging.error("Error al inicializar ALTextToSpeech: %s", e)
    tts_service = None

try:
    video_service = session.service("ALVideoDevice")
    logging.info("Servicio ALVideoDevice inicializado exitosamente.")
except Exception as e:
    logging.error("Error al inicializar ALVideoDevice: %s", e)
    video_service = None

# Variable global para el ID de suscripcion de la camara
name_id = None

def gen_video_stream():
    global name_id
    resolution = 2  # VGA
    color_space = 11  # kRGBColorSpace
    fps = 15

    if not video_service:
        logging.error("El servicio de video no esta disponible.")
        return

    try:
        name_id = video_service.subscribeCamera("python_client", 0, resolution, color_space, fps)
        logging.info("Suscrito al servicio de video con ID: %s", name_id)
    except Exception as e:
        logging.error("Error al suscribirse a la camara: %s", e)
        return

    try:
        while True:
            nao_image = video_service.getImageRemote(name_id)
            if nao_image is not None:
                image_width = nao_image[0]
                image_height = nao_image[1]
                array = nao_image[6]

                array = bytes(array)
                image = Image.frombytes("RGB", (image_width, image_height), array)

                img_io = io.BytesIO()
                image.save(img_io, 'JPEG')
                img_io.seek(0)
                jpeg_data = img_io.read()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
            else:
                logging.warning("No se pudo obtener la imagen de la camara.")
                continue
    except Exception as e:
        logging.error("Error en gen_video_stream: %s", e)
    finally:
        if name_id:
            video_service.unsubscribe(name_id)
            logging.info("Desuscrito del servicio de video con ID: %s", name_id)

@app.route('/video_feed')
def video_feed():
    return Response(gen_video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move_joint', methods=['POST'])
def move_joint():
    data = request.get_json()
    logging.info("Comando de movimiento recibido: %s", data)

    joint = data.get('joint')
    angle = data.get('angle')
    speed = data.get('speed', 0.1)

    if not joint or angle is None:
        logging.error("Parametros invalidos para mover la articulacion: %s", data)
        return jsonify({'status': 'error', 'message': 'Parametros invalidos'}), 400

    try:
        angle = float(angle)
        speed = float(speed)
        motion_service.setAngles(joint, angle, speed)
        logging.info("Articulacion %s movida exitosamente a angulo %f con velocidad %f", joint, angle, speed)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error("Error al mover la articulacion %s: %s", joint, e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/say', methods=['POST'])
def say_text():
    data = request.get_json()
    logging.info("Solicitud de texto a voz recibida: %s", data)

    text = data.get('text')

    if not text:
        logging.error("No se proporciono texto para TTS.")
        return jsonify({'status': 'error', 'message': 'No se proporciono texto'}), 400

    try:
        tts_service.say(text)
        logging.info("Texto dicho exitosamente: %s", text)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error("Error en TTS: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/perform_action', methods=['POST'])
def perform_action():
    data = request.get_json()
    action = data.get('action')

    if action == 'greet':
        try:
            tts_service.say("Hello! I am Pepper. Nice to meet you!")
            motion_service.setAngles("HeadYaw", 0.3, 0.2)
            motion_service.setAngles("HeadPitch", -0.2, 0.2)
            time.sleep(2)  # Pause for effect
            motion_service.setAngles("HeadYaw", -0.3, 0.2)
            time.sleep(2)
            motion_service.setAngles("HeadYaw", 0.0, 0.2)  # Return to neutral
            return jsonify({'status': 'success', 'message': 'Greet action performed.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    elif action == 'wave':
        try:
            motion_service.setAngles("RShoulderPitch", -0.5, 0.3)
            motion_service.setAngles("RElbowRoll", 1.5, 0.3)
            time.sleep(1)  # Simulate waving
            tts_service.say("Hello, everyone!")
            motion_service.setAngles("RShoulderPitch", 1.5, 0.3)
            motion_service.setAngles("RElbowRoll", 0.0, 0.3)
            return jsonify({'status': 'success', 'message': 'Wave action performed.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    elif action == 'presentation':
        try:
            tts_service.say("Hello! My name is Pepper. I am a humanoid robot designed to assist and interact with people.")
            motion_service.setAngles("HeadYaw", 0.2, 0.2)
            time.sleep(1)
            motion_service.setAngles("HeadYaw", -0.2, 0.2)
            tts_service.say("I can move, talk, and interact with you in many ways.")
            motion_service.setAngles("LShoulderPitch", 1.0, 0.3)
            motion_service.setAngles("RShoulderPitch", 1.0, 0.3)
            time.sleep(2)
            motion_service.setAngles("LShoulderPitch", 1.5, 0.3)
            motion_service.setAngles("RShoulderPitch", 1.5, 0.3)
            tts_service.say("I am here to assist you. Let us explore the future together!")
            return jsonify({'status': 'success', 'message': 'Presentation completed.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    elif action == 'home':
        try:
            # Resetting head and arms to home position
            motion_service.setAngles("HeadYaw", 0.0, 0.2)
            motion_service.setAngles("HeadPitch", 0.0, 0.2)
            motion_service.setAngles("LShoulderPitch", 1.5, 0.2)
            motion_service.setAngles("RShoulderPitch", 1.5, 0.2)
            motion_service.setAngles("LShoulderRoll", 0.0, 0.2)
            motion_service.setAngles("RShoulderRoll", 0.0, 0.2)
            motion_service.setAngles("LElbowYaw", -1.0, 0.2)
            motion_service.setAngles("RElbowYaw", 1.0, 0.2)
            motion_service.setAngles("LElbowRoll", -0.5, 0.2)
            motion_service.setAngles("RElbowRoll", 0.5, 0.2)
            motion_service.setAngles("LWristYaw", 0.0, 0.2)
            motion_service.setAngles("RWristYaw", 0.0, 0.2)
            return jsonify({'status': 'success', 'message': 'Returned to home position.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    else:
        return jsonify({'status': 'error', 'message': 'Unknown action.'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8070)
