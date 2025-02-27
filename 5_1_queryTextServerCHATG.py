import base64
import os
from datetime import datetime

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from flasgger import Swagger
from flask_httpauth import HTTPTokenAuth

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
    return True  # Puedes reemplazar con una verificación real si lo deseas

@app.route('/resumeDay', methods=['POST'])
def getDayInfo():
    """
    Genera un resumen del día basado en las tomas de medicamentos registradas.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            schedule:
              type: object
              description: JSON con las tomas de medicamentos por franja horaria
    responses:
      200:
        description: Resumen del día generado correctamente
    """

    # Obtener datos del JSON recibido
    data = request.get_json()
    if not data or "schedule" not in data:
        return jsonify({"error": "No se encontró la clave 'schedule' en la solicitud."}), 400

    schedule = data["schedule"]

    # Generar un resumen estructurado para OpenAI
    summary_text = "**Resumen del Día**\n\n"

    for franja, tomas in schedule.items():
        if tomas:
            summary_text += f"**{franja.replace('_', ' ').title()}**\n"
            for toma in tomas:
                summary_text += (
                    f"🔹 **{toma['medicamento']}** - {toma['cantidad_por_dosis']} mg\n"
                    f"   - Paciente: {toma['paciente']}\n"
                    f"   - Hora de toma: {toma['hora_toma']}\n"
                    f"   - Dosis restantes: {toma['dosis_restantes']}\n"
                    f"   - Parte afectada: {toma['parte_afectada']}\n\n"
                )

    hour = datetime.now().strftime("%H:%M")
    print(hour)
    # Generar `prompt` para OpenAI
    prompt = f"""
    A partir del siguiente listado de tomas de medicamentos del día de hoy, genera un texto sencillo hablando sobre los medicamentos del dia de hoy a modo de resumen para el paciente. Quiero que hagas alusion unicamente a que pastillas que va a tomar y brevemente a su propósito. No hace falta que hables de las dosis distante y refiere al paciente como su nombre de ser necesario. Tambien  quiero que hagas alusion al dia como algo que va a ocurrir, por ello solo habla de las pastillas que ocurran luego de la hora actual: {hour}

    {summary_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Eres un asistente experto en salud y bienestar con confianza como para tutear a tus pacientes. Hablas correctamente y formal"},
                {"role": "user", "content": prompt}
            ]
        )

        resume = response.choices[0].message.content

        # Intentar generar audio con OpenAI TTS
        try:
            tts_response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=resume
            )
        except Exception as e:
            print(f"Error con tts-1: {e}, intentando con tts-1-hd")
            tts_response = client.audio.speech.create(
                model="tts-1-hd",
                voice="alloy",
                input=resume
            )

        # Guardar audio en un archivo temporal
        audio_file = "output_audio.mp3"
        with open(audio_file, "wb") as f:
            f.write(tts_response.content)

        # Leer el archivo de audio y convertirlo a base64
        with open(audio_file, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({"summary": resume, "audio_base64": audio_base64})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
