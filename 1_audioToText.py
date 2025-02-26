from datetime import datetime
import json
import os  # Manejo del sistema de archivos y rutas
import requests  # 🔹 Para hacer la solicitud HTTP al servidor 3_textToJson.py
from flask import Flask, request, jsonify  # Framework web Flask para manejar peticiones HTTP
from werkzeug.utils import secure_filename  # Función para asegurar nombres de archivos válidos
from dotenv import load_dotenv  # Manejo de variables de entorno
from openai import OpenAI  # Cliente para interactuar con la API de OpenAI
from flasgger import Swagger  # Generación automática de documentación con API Docs
from supabase import create_client, Client

# 🔹 Cargar variables de entorno desde un archivo .env
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Clave de API de OpenAI
API_TOKEN = os.getenv('API_TOKEN')  # Token de autenticación para proteger la API
# Configurar Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")  # URL de Supabase
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # API Key de Supabase

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# URL de los servidores
PHOTO_TO_NAME_SERVER = "http://localhost:5001/img_to_text"
TEXT_TO_JSON_SERVER = "http://localhost:5002/getPillInfo"

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

# 🔹 Definir las extensiones de archivo permitidas
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def allowed_file(filename, allowed_extensions):
    """
    Verifica si el archivo tiene una extensión permitida.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def insert(data):
    # Definir cada campo por separado
    # Extraer valores del JSON recibido
    nombre = data.get("nombre_del_medicamento")
    dosis = data.get("cantidad_por_dosis")
    cantidad = data.get("numero_de_comprimidos")
    parte_afectada = data.get("parte_afectada")
    frecuencia = data.get("frecuencia")
    fecha_inicio = data.get("primera_ingestion")
    imagen = data.get("cropped_image")


    if not nombre or not dosis or not cantidad:
        return {"error": "Faltan datos obligatorios para el medicamento"}

    # Crear diccionario con los valores
    medicamento = {
        "nombre": nombre,
        "cantidad_por_dosis": dosis,
        "numero_comprimidos": cantidad,
        "parte_afectada": parte_afectada,
    }
    print(medicamento)
    tratamiento = {
        "nombre_medicamento": nombre,
        "nombre_paciente":"Candela",
        "fecha_inicio": datetime.strptime(fecha_inicio, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S"), #
        "frecuencia":frecuencia,
        "imagen": imagen,
    }
    print(tratamiento)
    # Insertar en Supabase
    response = supabase.table("medicamento").insert(medicamento).execute()
    response = supabase.table("tratamiento").insert(tratamiento).execute()

    print(response)  # Verificar respuesta

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
      - name: photo
        in: formData
        type: file
        required: true
        description: Imagen relacionada con la transcripción
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
    if 'photo' not in request.files:
        return jsonify({'error': 'No se encontró la imagen.'}), 400

    # Obtener arg audio
    audio_file = request.files['audio']
    image_file = request.files['photo']

    # 🔹 Verificar si el archivo tiene un nombre válido
    if audio_file.filename == '':
        return jsonify({'error': 'El nombre del archivo está vacío.'}), 400

    # 🔹 Verificar si el archivo tiene una extensión permitida
    if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
        return jsonify({'error': 'Formato de archivo de audio no permitido.'}), 400
    if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
        return jsonify({'error': 'Formato de archivo de imagen no permitido.'}), 400

    # 🔹 Guardar el archivo de manera segura en el directorio de almacenamiento temporal
    filename = secure_filename(audio_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(file_path)

    image_filename = secure_filename(image_file.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    image_file.save(image_path)

    try:
        # Información de la imagen
        with open(image_path, 'rb') as image_file:
            files = {'photo': image_file}  # Enviar la imagen en multipart/form-data
            event_json_photo = requests.post(PHOTO_TO_NAME_SERVER, files=files).json().get('event_json')

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
            # Comprobaciones
            #print('event_json_photo:' + json.dumps(event_json_photo, indent=4))
            #print('event_json_5001' + json.dumps(event_json_5001, indent=4))

            merged_json = {**event_json_photo, **event_json_5001}
            insert(merged_json)
        except ValueError:
            return jsonify({'error': 'No se ha podido hacer el merge.'}), 500

        return jsonify(merged_json)

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