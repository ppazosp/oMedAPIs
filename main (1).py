import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI as openai
from flasgger import Swagger
from flask_httpauth import HTTPTokenAuth
import magic

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
API_TOKEN = os.getenv('API_TOKEN')
PAZOS_KEY = os.getenv('PAZOS_KEY')

client = openai(api_key=PAZOS_KEY)

# Flask setup
app = Flask(__name__)
swagger = Swagger(app)
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    return token == API_TOKEN

@app.route('/img_to_text', methods=['POST'])
#@auth.login_required
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
    
    # Verifica si se proporcionó una imagen
    if 'image' not in request.files:
        return jsonify({"error": "No se ha proporcionado una imagen en la solicitud."}), 400

    image = request.files['image']
    img_b64_str = image_to_base64(image)

    # Determina el tipo MIME de la imagen
    image.seek(0)
    mime_type = magic.Magic(mime=True)
    mime = mime_type.from_buffer(image.read())
    print(mime)

    # Preparar el prompt para OpenAI
    prompt = f'''
    A partir de la siguiente imagen, quiero que me extraigas la siguiente información relevante del medicamento de manera ordenada y la presentes en el siguiente formato JSON:

    Nombre del medicamento (ejemplo: Paracetamol)
    Cantidad total del medicamento (ejemplo: 50g)
    Cantidad de cada dosis (ejemplo: 200mg)

    Si alguno de los datos no está disponible o no se menciona explícitamente en la imagen ponlo como null.

    El formato JSON debe ser el siguiente:

    "nombre_del_medicamento": "Paracetamol",
    "cantidad_total": "20g",
    "cantidad_dosis": "500mg",

    Instrucciones adicionales:

    - Si no hay información suficiente para completar un campo, ponlo como null.
    - Saca la información exclusivamente de la imagen, no añadas nada de tu propio conocimiento.
    - Si un campo no es aplicable o no se menciona, omítelo del JSON.
    - El resultado debe ser exclusivamente el JSON solicitado.
    '''

    try:
        # Llamar a la API de OpenAI con la imagen y el prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt},
                {"role": "user", "content": f"data:{mime};base64,{img_b64_str}"}
            ]
        )

        # Obtener la respuesta en formato JSON
        event_json = response.choices[0].message.content
        return jsonify({'response': event_json})

    except Exception as e:
        return jsonify({"error": f"Hubo un error al procesar la imagen: {str(e)}"}), 500

def image_to_base64(image_file):
    """
    Convierte el archivo de imagen subido a una cadena base64
    """
    try:
        img_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        return img_b64
    except Exception as e:
        raise Exception(f"Error al convertir la imagen a base64: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=5001)
