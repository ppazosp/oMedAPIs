import json
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image

def crop_medicine_box(base64_string):
    # Convertir base64 a imagen
    image_data = base64.b64decode(base64_string)
    image_np = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    # Convertir a escala de grises
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Aplicar un umbral adaptativo para mejorar la detección de bordes
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # Encontrar contornos
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filtrar contornos por área y forma (evitar ruido)
    filtered_contours = [c for c in contours if cv2.contourArea(c) > 5000]

    if not filtered_contours:
        return None  # No se encontró una caja clara

    # Encontrar el contorno con la mejor forma de rectángulo
    best_contour = max(filtered_contours, key=cv2.contourArea)

    # Obtener el rectángulo rotado mínimo
    rect = cv2.minAreaRect(best_contour)
    box = cv2.boxPoints(rect)
    box = np.int32(box)  # Convertir coordenadas a enteros

    # Obtener el área de la caja delimitadora
    x, y, w, h = cv2.boundingRect(best_contour)

    # Expandir un poco el área para evitar recortes excesivos
    padding = 10
    x = max(x - padding, 0)
    y = max(y - padding, 0)
    w = min(w + 2 * padding, image.shape[1] - x)
    h = min(h + 2 * padding, image.shape[0] - y)

    # Recortar la imagen
    cropped_image = image[y:y+h, x:x+w]

    # Convertir de OpenCV a base64
    _, buffer = cv2.imencode(".png", cropped_image)
    base64_cropped = base64.b64encode(buffer).decode("utf-8")

    return base64_cropped


def addCroppedPhoto(event_json, img_b64_str):
    """
    Procesa la imagen en base64, recorta la caja del medicamento y
    añade la imagen recortada al JSON de entrada.

    :param event_json: Diccionario con la información del medicamento.
    :param img_b64_str: Cadena en base64 con la imagen.
    :return: JSON con los datos del medicamento y la imagen recortada en base64.
    """

    if isinstance(event_json, str):
        try:
            event_json = json.loads(event_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "Formato JSON inválido"})


    cropped_b64 = crop_medicine_box(img_b64_str)

    # Agregar la imagen recortada al JSON original
    event_json["cropped_image"] = cropped_b64
    print(event_json)
    return json.dumps(event_json, indent=4)  # Retornar el JSON con formato bonito



