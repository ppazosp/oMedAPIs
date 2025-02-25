import os  # Manejo del sistema de archivos y rutas
import requests # 🔹 Para hacer la solicitud HTTP al servidor textToJson.py
from flask import Flask, request, jsonify  # Framework web Flask para manejar peticiones HTTP
from werkzeug.utils import secure_filename  # Función para asegurar nombres de archivos válidos
from dotenv import load_dotenv  # Manejo de variables de entorno
from openai import OpenAI  # Cliente para interactuar con la API de OpenAI
from flasgger import Swagger  # Generación automática de documentación con API Docs

# 🔹 Cargar variables de entorno desde un archivo .env
load_dotenv()
OPENAI_API_KEY = os.getenv('pazos_key')  # Clave de API de OpenAI
API_TOKEN = os.getenv('API_TOKEN')  # Token de autenticación para proteger la API

# URL del servidor textToJson.py
TEXT_TO_JSON_SERVER = "http://localhost:5001/format_event"

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
    # 🔹 Verificar si el archivo ha sido enviado en la petición
    if 'audio' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de audio.'}), 400

    audio_file = request.files['audio']  # Obtener el archivo desde la solicitud HTTP

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

        # 🔹 Enviar el texto transcrito al Servidor 2 (textToJson.py)
        response = requests.post(TEXT_TO_JSON_SERVER, json={"transcript": text})

        # 🔹 Eliminar el archivo después de la transcripción para ahorrar espacio
        os.remove(file_path)

        if response.status_code == 200:
            event_json = response.json().get("event")
            return jsonify({"transcript": text, "event_json": event_json})


        # 🔹 Retornar el texto transcrito como respuesta en formato JSON
        return jsonify({"error": "Error al convertir texto a JSON"}), 500

    except Exception as e:
        # 🔹 Si ocurre un error, eliminar el archivo solo si aún existe
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error in transcribe_audio': str(e)}), 500

# 🔹 Ejecutar el servidor Flask en el puerto 5000 si se ejecuta directamente este script
if __name__ == '__main__':
    app.run(debug=True, port=5000)
