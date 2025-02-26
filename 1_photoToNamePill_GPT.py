import base64
import datetime
import json
import os
import re

import magic
from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, request, jsonify
from flask_httpauth import HTTPTokenAuth
from openai import OpenAI as openai

# Ruta donde se guardarán los archivos JSON
JSON_FOLDER = "json_files"
os.makedirs(JSON_FOLDER, exist_ok=True)  # Crea la carpeta si no existe

from cropPhoto import addCroppedPhoto

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
API_TOKEN = os.getenv('API_TOKEN')

client = openai(api_key=OPENAI_API_KEY)

# Flask setup
app = Flask(__name__)
swagger = Swagger(app)
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    '''if not token:
        token = request.headers.get("Authorization")  # Extraer manualmente
        if token and token.startswith("Bearer "):
            token = token.split(" ")[1]  # Obtener solo el token
    print(f"Token recibido: {token}")
    print(f"Token esperado: {API_TOKEN}")
    return token == API_TOKEN'''
    return True

@app.route('/img_to_text', methods=['POST'])
@auth.login_required
def format_event():
    """
    Analiza una imagen de medicamento y extrae la información relevante en formato JSON
    ---
    parameters:
      - name: image
        in: formData
        type: file
        required: true
        description: Imagen del medicamento desde la cual extraer la información
    responses:
      200:
        description: Información del medicamento extraída correctamente
        content:
          application/json:
            schema:
              type: object
              properties:
                resultado:
                  type: string
                  description: JSON con la información extraída del medicamento (nombre, tipo, dosis, frecuencia, etc.)
      400:
        description: Error por falta de imagen en la solicitud
      404:
        description: La imagen proporcionada no fue encontrada
      500:
        description: Error interno del servidor al procesar la imagen
    """

    if 'image' not in request.files:
        return jsonify({"error": "No se ha proporcionado una imagen en la solicitud."}), 400

    image = request.files['image']
    img_b64_str = image_to_base64(image)
    image.seek(0)
    mime_type = magic.Magic(mime=True)
    mime = mime_type.from_buffer(image.read())
    print(mime)

# Prepare the prompt
    prompt = f'''
        A partir de la siguiente imagen, quiero que me extraigas la siguiente información relevante del medicamento de manera ordenada y la presentes en el siguiente formato JSON:

            Nombre del medicamento (ejemplo: Paracetamol)
            Cantidad de dosis del medicamento: (ejemplo: 50 capsulas)
            Cantidad de cada dosis (ejemplo: 200mg)

        Si alguno de los datos no está disponible o no se menciona explícitamente en la imagen ponlo como null. 

        El formato JSON debe ser el siguiente:

        "nombre_del_medicamento": "Paracetamol",
        "numero_de_comprimidos": "10 comprimidos",
        "cantidad_dosis": "500mg",

        Instrucciones adicionales:

    Si no hay información suficiente para completar un campo, ponlo como null.
    Saca la información exclusivamente de la imagen, no añadas nada de tu propio conocimiento
    Si un campo no es aplicable o no se menciona, omítelo del JSON.
    El resultado debe ser exclusivamente el JSON solicitado.
        '''

    # Convert image to base64
    #{"type": "image_url","image_url": {"url": f"data:image/jpeg;base64,{img_b64_str}"},},],},
    
    try:
        # Call the OpenAI API with both image and prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpg;base64,{img_b64_str}"}}
                    ],
                },
            ],
        )

        event_json_str = response.choices[0].message.content

        event_json_str_clean = clearJson_1(event_json_str)

        # 🔹 3️⃣ Convertir el string limpio en JSON real
        try:
            new_event_json_str = addCroppedPhoto(event_json_str_clean, img_b64_str)
            clean_json = clearJson_2(new_event_json_str)
            event_json_final = json.loads(clean_json)

        except json.JSONDecodeError as e:
            return jsonify({'error': f'JSON inválido generado por OpenAI: {str(e)}', 'raw_output': event_json_final}), 500

        json_filename = save_json_to_file(event_json_final)

        return jsonify({
            "event_json": event_json_final,
            "json_file": json_filename  # Retorna la ubicación del archivo guardado
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        return jsonify({"error": f"Hubo un error al procesar la imagen: {str(e)}"}), 500

def save_json_to_file(event_json):
    """ Guarda el JSON en un archivo dentro de la carpeta json_files. """
    try:
        # Crear un nombre de archivo único usando la fecha y hora
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{JSON_FOLDER}/medicamento_{timestamp}.json"

        # Guardar el JSON en el archivo
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(event_json, f, indent=4, ensure_ascii=False)

        print(f"✅ JSON guardado en {filename}")
        return filename  # Retornar el nombre del archivo para referencia
    except Exception as e:
        print(f"❌ Error guardando el JSON: {e}")
        return None


def image_to_base64(image_file):
    """
    Convert the uploaded image file to a base64 string
    """
    try:
        # Read the image file and convert to base64
        img_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        return img_b64
    except Exception as e:
        raise Exception(f"Error al convertir la imagen a base64: {e}")

def clearJson_1(event_json):
    ## Limpieza del json
    # 🔹 1️⃣ Eliminar los bloques ```json ... ```
    event_json = re.sub(r"^```json|```$", "", event_json.strip(), flags=re.MULTILINE).strip()

    # 🔹 2️⃣ Eliminar caracteres de escape innecesarios (\n y \")
    return event_json.replace("\n", "").replace("\\n", "").replace('\\"', '"')

def clearJson_2(event_json):
    ## Limpieza del json
    # 🔹 2️⃣ Eliminar caracteres de escape innecesarios (\n y \")
    return event_json.replace("\n", "").replace("\\n", "").replace('\\"', '"')


if __name__ == '__main__':
    print(f"API_TOKEN en el servidor: {API_TOKEN}")  # Esto debe imprimir un valor, no None
    app.run(debug=True, port=5002)