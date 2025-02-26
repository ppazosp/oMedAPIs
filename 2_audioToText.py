import json
import os  # Manejo del sistema de archivos y rutas
import requests  # 🔹 Para hacer la solicitud HTTP al servidor 3_textToJson.py
from flask import Flask, request, jsonify  # Framework web Flask para manejar peticiones HTTP
from werkzeug.utils import secure_filename  # Función para asegurar nombres de archivos válidos
from dotenv import load_dotenv  # Manejo de variables de entorno
from openai import OpenAI  # Cliente para interactuar con la API de OpenAI
from flasgger import Swagger  # Generación automática de documentación con API Docs

# 🔹 Cargar variables de entorno desde un archivo .env
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Clave de API de OpenAI
API_TOKEN = os.getenv('API_TOKEN')  # Token de autenticación para proteger la API

# URL del servidor 3_textToJson.py
TEXT_TO_JSON_SERVER = "http://localhost:5001/getPillInfo"

# 🔹 Inicializar cliente de OpenAI con la clave de API cargada
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔹 Configuración de Flask
app = Flask(__name__)  # Inicializa la aplicación Flask
app.config['UPLOAD_FOLDER'] = 'uploads'  # Carpeta donde se guardarán temporalmente los archivos subidos
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # Límite de tamaño de archivo: 25 MB

# 🔹 Crea la carpeta de almacenamiento de archivos si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 🔹 Configurar Swagger para generar documentación de la API
swagger = Swagger(app)

# 🔹 Definir las extensiones de archivo permitidas para la subida de audios
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg'}


def allowed_file(filename):
    """
    Verifica si el archivo tiene una extensión permitida.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 🔹 Definir el endpoint para la transcripción de audio
@app.route('/transcribe', methods=['POST'])
# @auth.login_required  # Autenticación desactivada por ahora
def transcribe_audio():
    """
    Transcribe un archivo de audio a texto usando OpenAI Whisper.
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: audio
        in: formData
        type: file
        required: true
        description: Archivo de audio (MP3, WAV, M4A, OGG)
      - name: event_json
        in: formData
        type: string
        required: true
        description: JSON con información adicional
    responses:
      200:
        description: Texto transcrito con éxito
        schema:
          type: object
          properties:
            transcript:
              type: string
              example: "Hola, esto es una prueba de transcripción."
      400:
        description: Error de validación (archivo incorrecto o faltante)
      401:
        description: No autorizado (si la autenticación estuviera activada)
      500:
        description: Error interno del servidor
    """
    # 🔹 Verificar si los argumentos se han sido enviado en la petición
    if 'audio' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de audio.'}), 400
    if 'event_json' not in request.form:
        return jsonify({'error': 'No se encontró el JSON con información adicional.'}), 400

    # Obtener argumentos
    audio_file = request.files['audio']
    event_json_str = request.form['event_json']  # Json de photoToNamePill
    try:
        event_json_photo = json.loads(event_json_str)
    except ValueError:
        return jsonify({'error': 'El JSON proporcionado de photoToNamePill no es válido.'}), 400

    # 🔹 Verificar si el archivo tiene un nombre válido
    if audio_file.filename == '':
        return jsonify({'error': 'El nombre del archivo está vacío.'}), 400

    # 🔹 Verificar si el archivo tiene una extensión permitida
    if not allowed_file(audio_file.filename):
        return jsonify({'error': 'Formato de archivo no permitido. Solo se permiten MP3, WAV, M4A y OGG.'}), 400

    # 🔹 Guardar el archivo de manera segura en el directorio de almacenamiento temporal
    filename = secure_filename(audio_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(file_path)

    try:
        # 🔹 Abrir el archivo y enviarlo a OpenAI Whisper para su transcripción
        with open(file_path, 'rb') as audio:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",  # Modelo de OpenAI para transcripción de audio
                file=audio  # Archivo de audio a transcribir
            )

        text = transcription.text
        print('Transcription: ' + text)
        # 🔹 Eliminar el archivo después de la transcripción para ahorrar espacio
        os.remove(file_path)

        # 🔹 Enviar el texto transcrito al Servidor 2 (3_textToJson.py)
        response = requests.post(TEXT_TO_JSON_SERVER, json={'transcript': text})

        if response.status_code != 200:
            return jsonify(
                {'error': 'Error al procesar el JSON en el servidor 5001', 'status_code': response.status_code}), 500

        try:
            event_json_5001 = response.json().get("event_json")
        except ValueError:
            return jsonify({'error': 'El JSON devuelto por el servidor 5001 no es válido.'}), 500

        # Check if jsons are jsons
        if not isinstance(event_json_photo, dict) or not isinstance(event_json_5001, dict):
            return jsonify({'error': 'Los datos recibidos no son JSON válidos.'}), 500

        try:
            print('event_json_photo:' + json.dumps(event_json_photo, indent=4))
            print('event_json_5001' + json.dumps(event_json_5001, indent=4))

            merged_json = {**event_json_photo, **event_json_5001}
        except ValueError:
            return jsonify({'error': 'No se ha podido hacer el merge.'}), 500

        return jsonify({'medication': merged_json})

        # Para probar solo la transcripción
        # return jsonify({"transcript": text})
    except requests.RequestException as e:
        return jsonify({'error': f'Error en la solicitud al servidor 5001: {str(e)}'}), 500
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500


# 🔹 Ejecutar el servidor Flask en el puerto 5000 si se ejecuta directamente este script
if __name__ == '__main__':
    app.run(debug=True, port=5000)
