from supabase import create_client
import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from flasgger import Swagger

# Cargar credenciales de Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración de Flask
app = Flask(__name__)
swagger = Swagger(app)

# 🔹 Definimos las franjas horarias según lo solicitado
FRANJAS_HORARIAS = {
    "JUSTAWAKE": ("06:00:00", "07:00:00"),
    "BEFOREBREAKFAST": ("07:00:00", "08:00:00"),
    "AFTERBREAKFAST": ("08:00:00", "10:30:00"),
    "MIDDAY": ("10:30:00", "12:30:00"),
    "BEFORELUNCH": ("12:30:00", "13:30:00"),
    "AFTERLUNCH": ("13:30:00", "15:30:00"),
    "MIDAFTERNOON": ("15:30:00", "17:30:00"),
    "BEFOREDINNER": ("17:30:00", "19:30:00"),
    "AFTERDINNER": ("19:30:00", "21:30:00"),
    "PREVIOUSTOSLEEP": ("21:    30:00", "23:59:59"),
}

# 🔹 Función para llamar a Supabase y obtener los medicamentos por franja
def get_medicamentos_por_franja(franja_inicio, franja_fin):
    try:
        response = supabase.rpc("get_tomas_por_franja", {
            "start_time": franja_inicio,
            "end_time": franja_fin
        }).execute()
        return response.data  # ✅ Retornamos solo los datos sin metadatos extra
    except Exception as e:
        return {"error": f"Error al ejecutar Supabase RPC: {str(e)}"}

# 🔹 Endpoint para obtener medicamentos en todas las franjas horarias
@app.route('/medicamentos', methods=['GET'])
def get_medicamentos():
    """
    Obtiene los medicamentos según la franja horaria definida.
    ---
    responses:
      200:
        description: Retorna los medicamentos organizados por franja horaria
    """
    resultado = {}

    for franja, (inicio, fin) in FRANJAS_HORARIAS.items():
        resultado[franja] = get_medicamentos_por_franja(inicio, fin)

    return jsonify(resultado)

# 🔹 Iniciar servidor Flask
if __name__ == '__main__':
    app.run(debug=True, port=5006)
