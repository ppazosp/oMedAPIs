# Requires "requests" to be installed (see python-requests.org)
import os
import requests
from dotenv import load_dotenv

load_dotenv()

CROPPER_API = os.getenv('REMOVE_KEY')

# Función para usar la API de Remove.bg
def remove_background(image_path, output_path, api_key=CROPPER_API):
    # URL de la API de Remove.bg
    url = "https://api.remove.bg/v1.0/removebg"

    # Abrir la imagen
    with open(image_path, "rb") as image_file:
        files = {"image_file": image_file}

        # Enviar la solicitud a la API de Remove.bg
        response = requests.post(url, files=files, data={"size": "auto"}, headers={"X-Api-Key": api_key})

        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            print("Fondo eliminado correctamente.")

            # Guardar la imagen recortada
            '''with open(output_path, "wb") as out_file:
                out_file.write(response.content)'''
            print(f"Imagen recortada guardada en: {output_path}")
            return response.content
        else:
            print(f"Error: {response.status_code}, {response.text}")

# Ruta de la imagen original
image_path = 'cerca.jpeg'  # Sustituir por la ruta de tu imagen

# Ruta de salida para la imagen recortada
output_path = 'cropped_image.png'  # Puedes cambiar el formato si es necesario

# Tu clave API de Remove.bg
api_key = CROPPER_API  # Sustituir con tu clave API

# Llamar a la función para eliminar el fondo
remove_background(image_path, output_path)
