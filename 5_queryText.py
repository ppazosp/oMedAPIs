from supabase import create_client
import os
from dotenv import load_dotenv

# Cargar credenciales
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_medicamentos_por_franja(franja_inicio, franja_fin):
    response = supabase.rpc("get_tomas_por_franja", {
        "start_time": franja_inicio,
        "end_time": franja_fin
    }).execute()
    return response

# Prueba para la franja JUSTAWAKE (6:00 - 7:00)
print(get_medicamentos_por_franja("06:00", "24:00"))
