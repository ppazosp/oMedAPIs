import os
import base64
import re
import json
import cv2
import numpy as np
import pytesseract
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flasgger import Swagger
from flask_httpauth import HTTPTokenAuth
import magic
import cropPhoto

import pytesseract

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Verifica la ruta con `which tesseract`

# Cargar variables de entorno
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

# Configurar Flask
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
    Analiza una imagen de medicamento y extrae la información relevante en formato JSON usando OCR
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
                  description: JSON con la información extraída del medicamento (nombre, cantidad de una dosis y número de comprimidos)
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

    # Volver al inicio del archivo antes de leerlo nuevamente
    image.seek(0)

    # Determina el tipo MIME de la imagen
    mime_type = magic.Magic(mime=True)
    mime = mime_type.from_buffer(image.read())

    # Verificar tamaño del archivo
    image.seek(0, os.SEEK_END)  # Mover puntero al final
    file_size = image.tell()  # Obtener tamaño en bytes
    image.seek(0)  # Volver al inicio

    if file_size == 0:
        return jsonify({"error": "El archivo de imagen está vacío."}), 400

    # Procesar la imagen y extraer texto con OCR
    extracted_text = extract_text_from_image(image)

    # Obtener datos relevantes del texto
    medication_info = parse_medicine_info(extracted_text)

    # Recortar la imagen de la caja del medicamento
    new_event_json = cropPhoto.addCroppedPhoto(medication_info, img_b64_str)

    return new_event_json

def image_to_base64(image_file):
    """
    Convierte el archivo de imagen subido a una cadena base64.
    """
    try:
        img_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        return img_b64
    except Exception as e:
        raise Exception(f"Error al convertir la imagen a base64: {e}")

def extract_text_from_image(image, null=None):
    """
    Convierte la imagen en texto usando OCR (Tesseract).
    """
    try:
        # Leer imagen y convertir a OpenCV
        image_data = np.frombuffer(image.read(), np.uint8)

        if image_data.size == 0:
            raise ValueError("El archivo de imagen está vacío o no se pudo leer correctamente.")

        img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("No se pudo decodificar la imagen. Puede estar corrupta o en un formato no soportado.")

        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Aplicar un filtro de umbral adaptativo para mejorar el texto
        processed_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 11, 2)

        # Usar OCR para extraer el texto
        extracted_text = pytesseract.image_to_string(processed_img, lang="spa")

        return extracted_text
    except Exception as e:
        raise Exception(f"Error en OCR: {e}")

def parse_medicine_info(text):
    """
    Extrae la información relevante del texto detectado en la imagen.
    """
    try:
        # Inicializar valores
        nombre_del_medicamento = None
        cantidad_dosis = None
        numero_de_comprimidos = None

        # Expresión regular para encontrar dosis (ej: 500mg, 20mg, 1g)
        dosis_match = re.search(r"(\d+\s?(mg|g|ml))", text, re.IGNORECASE)
        if dosis_match:
            cantidad_dosis = dosis_match.group(1)

        # Expresión regular para encontrar número de comprimidos (ej: 20 comprimidos, 10 tablets)
        comprimidos_match = re.search(r"(\d+)\s?(comprimidos|tablets|capsulas)", text, re.IGNORECASE)
        if comprimidos_match:
            numero_de_comprimidos = comprimidos_match.group(1)

        # Se asume que el nombre es la palabra más grande en la imagen
        words = text.split("\n")
        words = [w.strip() for w in words if len(w.strip()) > 3]
        words.sort(key=len, reverse=True)  # Ordenar por longitud de palabras
        if words:
            nombre_del_medicamento = words[0]  # Se asume que la palabra más grande es el nombre

        # Crear JSON con la información extraída
        medication_info = {
            "nombre_del_medicamento": nombre_del_medicamento or "null",
            "cantidad_dosis": cantidad_dosis or "null",
            "numero_de_comprimidos": numero_de_comprimidos or "null"
        }

        return medication_info
    except Exception as e:
        raise Exception(f"Error al analizar la información del medicamento: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=5002)
