import datetime
import os
import requests  # 🔹 Para hacer la solicitud HTTP al servidor 3_textToJson.py

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from flasgger import Swagger
from flask_httpauth import HTTPTokenAuth
import json
import re

# Cargar variables de entorno
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
API_TOKEN = os.getenv('API_TOKEN')

client = OpenAI(api_key=OPENAI_API_KEY)

# Configuración de Flask
app = Flask(__name__)
swagger = Swagger(app)
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    return True

@app.route('/selectQuery', methods=['POST'])
# @auth.login_required
def getPillInfo():
    """
    Analiza una transcripción y devuelve información estructurada sobre la medicación
    ---
    parameters:
      - name: transcript
        in: formData
        type: string
        required: true
        description: Texto de la transcripción del paciente
    responses:
      200:
        description: Información de la medicación extraída correctamente
        content:
          application/json:
            schema:
              type: object
              properties:
                event:
                  type: string
                  description: JSON con la información de la medicación
      400:
        description: Error por falta de transcripción
      500:
        description: Error interno del servidor
    """

    data = request.get_json()
    transcript = data.get('transcript')

    if not transcript:
        return jsonify({'error': 'No se proporcionó la transcripción.'}), 400

    # Obtener la fecha de hoy en formato "YYYY-MM-DD"
    today_date = datetime.date.today().isoformat()

    json_template = json.dumps({
        "event_json": {
            "frecuencia": "<horas entre cada ingestion (poner solo el número en horas)>",
            "primera_ingestion": "<Fecha y hora de la primera toma (en formato local date time)>",
            "parte_afectada": "<Parte del cuerpo afectada>"
        }
    }, indent=4)  # 🔹 Convierte el JSON en un string bien formateado

    today_date = datetime.date.today().isoformat()

    prompt = f'''
    A partir del siguiente texto de transcripción de un paciente, extrae la siguiente información y devuelve un JSON con estos campos:

    1. **Frecuencia**: Cada vez que debe tomar la pastilla. Si te dice dos veces al dia será cada 12 horas o si te dice 3 veces al dia serán 8 horas).
    2. **Día y hora de primera ingestión**: Fecha y hora en formato "DD/MM/YYYY HH:MM" si está disponible, o solo "DD/MM/YYYY". Para referirse a este punto, la transcripción puede decir frases como "Empezaré..." "La primera pastilla la tomaré...". En resumen toda frase que implique empezar a tomar las pastillas seguidas de una fecha. Ten en cuenta que hoy es {today_date}
    3. **Parte del cuerpo afectada**: Indicar la parte del cuerpo a la que se refiere el medicamento. Es importante que se meta en alguna de estas categorías:**
    - HEART_RELATED
    - DIGESTIVE
    - GENERAL_BODY
    - BRAIN_RELATED
    - PSYCHOLOGICAL

    **Notas importantes:**
    - La transcripción proviene de personas mayores o con dificultades de accesibilidad, por lo que el audio puede tener errores.
    - Si no es posible extraer la información de un campo, devuelve "null_NoEspecify" en su lugar.
    - Extrae exclusivamente la información mencionada en el audio sin añadir suposiciones.
    - Devuelve **únicamente** un JSON válido con la estructura especificada.

    Plantilla de JSON esperado:
    {json_template}

    **Texto de transcripción:**
    "{transcript}"
    '''

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Eres un asistente experto en interpretar instrucciones médicas de reconocimientode medicamentos desde transcripciones de audio. Tienes que tener en cuenta que el audio lo realiza una "},
                {"role": "user", "content": prompt}
            ]
        )

        event_json = response.choices[0].message.content
        # 🔹 1️⃣ Eliminar los bloques ```json ... ```
        event_json = re.sub(r"^```json|```$", "", event_json.strip(), flags=re.MULTILINE).strip()
        ### Limpieza del json
        # 🔹 2️⃣ Eliminar caracteres de escape innecesarios (\n y \")
        clean_json_str = event_json.replace("\n", "").replace("\\n", "").replace('\\"', '"')
        # 🔹 3️⃣ Convertir el string limpio en JSON real
        try:
            event_json = json.loads(clean_json_str)
            print('Output' + json.dumps(event_json, indent=4))
        except json.JSONDecodeError as e:
            return jsonify({'error': f'JSON inválido generado por OpenAI: {str(e)}', 'raw_output': clean_json_str}), 500

        return jsonify(event_json)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5002)