import json
import cv2
import numpy as np
import base64
import pyperclip


def crop_medicine_box(base64_string):
    print("Iniciando el proceso de recorte de la imagen...")

    # Convertir base64 a imagen
    try:
        image_data = base64.b64decode(base64_string)
        image_np = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"Error al decodificar la imagen base64: {e}")
        return None

    print("Imagen cargada correctamente.")

    # Convertir a escala de grises
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("gray.png", gray)  # Guarda la imagen de bordes en el disco

    contrast_factor = 2.0  # Puedes aumentar este valor para mayor contraste
    contrast_image = cv2.convertScaleAbs(gray, alpha=contrast_factor, beta=0)

    # Aplicar un filtro bilateral para reducir el ruido sin perder bordes
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # Usar Canny para detección de bordes
    edges = cv2.Canny(gray, 20, 20, apertureSize=3)
    cv2.imwrite("edges.png", edges)  # Guarda la imagen de bordes en el disco
    print("Imagen de bordes guardada como 'edges.png'.")

    # Encontrar contornos
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Contornos encontrados: {len(contours)}")

    print(f"Total de contornos encontrados: {len(contours)}")
    for c in contours:
        epsilon = 0.04 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, epsilon, True)
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        print(f"Contorno: Área = {cv2.contourArea(c)}, Relación de aspecto = {aspect_ratio}")

    # Filtrar contornos por área y forma (evitar ruido)
    filtered_contours = [c for c in contours if cv2.contourArea(c) > 1000]
    print(f"Contornos después de filtrar por área: {len(filtered_contours)}")

    '''if not filtered_contours:
        print("No se encontraron contornos válidos.")
        return None  # No se encontró una caja clara'''

    # Filtrar por una mejor relación de aspecto (más rectangular)
    best_contour = None
    max_aspect_ratio = 0

    for c in filtered_contours:
        # Aproximar el contorno a un polígono
        epsilon = 0.04 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, epsilon, True)

        # Calcular la relación de aspecto (ancho/alto)
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        print(
            f"Área: {cv2.contourArea(c)}, Relación de aspecto: {aspect_ratio}")  # Ver valores de área y relación de aspecto

        if 1.5 < aspect_ratio < 2.5:  # Relación de aspecto entre 1.5 y 2.5
            if cv2.contourArea(c) > cv2.contourArea(best_contour) if best_contour is not None else 0:
                best_contour = c

    '''if best_contour is None:
        print("No se encontró un contorno adecuado.")
        return None  # No se encontró un buen contorno'''

    # Obtener el rectángulo delimitador
    x, y, w, h = cv2.boundingRect(best_contour)

    # Expandir un poco el área para evitar recortes excesivos
    padding = 15
    x = max(x - padding, 0)
    y = max(y - padding, 0)
    w = min(w + 2 * padding, image.shape[1] - x)
    h = min(h + 2 * padding, image.shape[0] - y)

    # Recortar la imagen
    cropped_image = image[y:y + h, x:x + w]
    print(f"Imagen recortada con dimensiones: {cropped_image.shape}")

    # Convertir de OpenCV a base64
    _, buffer = cv2.imencode(".png", cropped_image)
    base64_cropped = base64.b64encode(buffer).decode("utf-8")

    # Dibuja los contornos en la imagen original
    image_with_contours = image.copy()
    cv2.drawContours(image_with_contours, filtered_contours, -1, (0, 255, 0), 2)
    cv2.imwrite("contours.png", image_with_contours)  # Guarda la imagen con contornos dibujados
    print("Imagen con contornos guardada como 'contours.png'.")

    cv2.imwrite("buffer.png", cropped_image)  # Guarda la imagen de bordes en el disco


    return base64_cropped


def addCroppedPhoto(event_json, img_b64_str):
    """
    Procesa la imagen en base64, recorta la caja del medicamento y
    añade la imagen recortada al JSON de entrada.

    :param event_json: Diccionario con la información del medicamento.
    :param img_b64_str: Cadena en base64 con la imagen.
    :return: JSON con los datos del medicamento y la imagen recortada en base64.
    """
    print("Procesando el JSON y la imagen base64...")

    if isinstance(event_json, str):
        try:
            event_json = json.loads(event_json)
        except json.JSONDecodeError as e:
            print(f"Error al parsear JSON: {e}")
            return json.dumps({"error": "Formato JSON inválido"})

    cropped_b64 = crop_medicine_box(img_b64_str)

    if cropped_b64 is None:
        print("No se pudo procesar la imagen.")
        event_json["cropped_image"] = None
    else:
        # Agregar la imagen recortada al JSON original
        event_json["cropped_image"] = cropped_b64

    return json.dumps(event_json, indent=4)  # Retornar el JSON con formato bonito


import os


def main():
    print("Iniciando el script...")
    # Ruta de la imagen en la misma carpeta que el script .py
    image_path = os.path.join(os.path.dirname(__file__),
                              'lejosBlanco.jpeg')  # Cambia 'imagen.jpg' por el nombre de tu archivo

    # Leer la imagen y convertirla a base64
    try:
        with open(image_path, 'rb') as img_file:
            img_b64_str = base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error al leer la imagen: {e}")
        return

    # Crear un ejemplo de JSON para el evento
    event_json = {
        "medication": "Aspirina",
        "dose": "500mg",
        "time": "08:00 AM"
    }

    # Llamar a la función para agregar la imagen recortada al JSON
    result_json = addCroppedPhoto(event_json, img_b64_str)

    # Copiar el JSON resultante al portapapeles
    try:
        pyperclip.copy(result_json)
        print("Imagen en base64 copiada al portapapeles.")
    except Exception as e:
        print(f"Error al copiar al portapapeles: {e}")


if __name__ == "__main__":
    main()
