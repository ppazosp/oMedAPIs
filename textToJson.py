import datetime
import os
import requests # 🔹 Para hacer la solicitud HTTP al servidor textToJson.py

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

# URL del servidor jsonToEvent.py
JSON_TO_EVENT_SERVER = "http://localhost:5002/create_event"

# Configuración de Flask
app = Flask(__name__)
swagger = Swagger(app)
auth = HTTPTokenAuth(scheme='Bearer')


@auth.verify_token
def verify_token(token):
    return True
    # return token == API_TOKEN


@app.route('/format_event', methods=['POST'])
# @auth.login_required
def format_event():
    """
    Analiza una transcripción y devuelve funciones de Google Calendar
    ---
    parameters:
      - name: transcript
        in: formData
        type: string
        required: true
        description: Texto de la transcripción del evento
    responses:
      200:
        description: Funciones de Google Calendar generadas correctamente
        content:
          application/json:
            schema:
              type: object
              properties:
                event:
                  type: string
                  description: JSON con las funciones de Google Calendar
      400:
        description: Error por falta de transcripción
      500:
        description: Error interno del servidor
    """

    # transcript = request.json.get('transcript')

    data = request.get_json()
    transcript = data.get('transcript')

    if not transcript:
        return jsonify({'error': 'No se proporcionó la transcripción.'}), 400

    # Obtener la fecha de hoy en formato "YYYY-MM-DD"
    today_date = datetime.date.today().isoformat()

    json_template = json.dumps({
        "functionName": "insert",
        "functionArgs": [
            {"calendarId": "primary"},
            {"event": {
                "summary": "<Título del evento>",
                "start": {"dateTime": "<Fecha y hora de inicio>", "timeZone": "Europe/Madrid"},
                "end": {"dateTime": "<Fecha y hora de fin>", "timeZone": "Europe/Madrid"},
                "description": "Categoría: <Categoría Detectada> <Texto original del evento>",
                "extendedProperties": {
                    "private": {
                        "category": "<Categoría Detectada>"
                    }
                }
            }}
        ]
    }, indent=4)  # 🔹 Convierte el JSON en un string bien formateado

    prompt = f'''
    A partir del siguiente json: "{transcript}", quiero que generes un JSON con la información necesaria para crear un evento en Google Calendar.

    **Instrucciones:**
    1. **Detecta correctamente la fecha y la hora** mencionadas en el texto. Si se menciona "mañana", usa la fecha de mañana. Si se menciona una fecha en el futuro (por ejemplo, "próximo lunes"), interpreta esa fecha correctamente. Ten en cuenta que hoy es {today_date}

    2. **Clasifica este evento en una de las siguientes categorías**:
       - Trabajo exigente (trabajos exigentes)
       - Trabajo relajado (trabajos con menos carga)
       - Ocio
       - Deporte
       - Tareas de casa (comer, limpiar…)
       - Descanso
       - Sueño
       - Reunion

    3. **Genera un JSON con la siguiente estructura**:

    {json_template}

    4. **No devuelvas ningún otro texto, solo el JSON en la estructura especificada.**

    5. **Asegúrate de que el JSON sea válido y bien formateado.**
    
    6. **Cuando añadas la palabra "event" asegurate de ponerla con este formato: "event": [**
    '''

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en crear eventos para Google Calendar."},
                {"role": "user", "content": prompt}
            ]
        )

        event_json = response.choices[0].message.content

        ### Limpieza del json
        # 🔹 1️⃣ Eliminar los bloques ```json ... ```
        clean_json_str = re.sub(r"^```json|```$", "", event_json.strip(), flags=re.MULTILINE).strip()

        # 🔹 2️⃣ Eliminar caracteres de escape innecesarios (\n y \")
        clean_json_str = clean_json_str.replace("\n", "").replace("\\n", "").replace('\\"', '"')

        # 🔹 3️⃣ Convertir el string limpio en JSON real
        try:
            event_json = json.loads(clean_json_str)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'JSON inválido generado por OpenAI: {str(e)}', 'raw_output': clean_json_str}), 500

        # 🔹 Enviar el json formateado al Servidor 3 (jsonToEvent.py)
        calendar_response = requests.post(JSON_TO_EVENT_SERVER, json={"event": event_json})

        if calendar_response.status_code == 200:
            return jsonify({"event_json": event_json, "calendar_response": calendar_response.json()})

        return jsonify({"error": "Error al enviar evento a Google Calendar", "response": calendar_response.text}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)