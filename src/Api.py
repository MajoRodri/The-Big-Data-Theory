import os
from datetime import datetime

import requests

import alertas
import persistencia

API_URL = "http://api.weatherapi.com/v1/current.json"
API_KEY_ENV = "PACHITO"
REQUEST_TIMEOUT = 10


def obtener_clima_api(ciudad, api_key=None):
    """
    Consulta WeatherAPI y devuelve el JSON crudo de la respuesta.
    """
    clave_api = api_key or os.getenv(API_KEY_ENV)
    if not clave_api:
        raise ValueError(
            f"No se encontro la clave de la API. Define la variable de entorno {API_KEY_ENV}."
        )

    parametros = {
        "key": clave_api,
        "q": ciudad,
        "lang": "es",
    }

    try:
        respuesta = requests.get(API_URL, params=parametros, timeout=REQUEST_TIMEOUT)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.exceptions.HTTPError as error:
        detalle = _extraer_error_api(error.response)
        raise RuntimeError(f"Error de WeatherAPI: {detalle}") from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"No se pudo conectar con WeatherAPI: {error}") from error


def transformar_respuesta_a_registro(datos_api, distrito=None, usuario_actual=None, fecha=None):
    """
    Traduce la respuesta externa al formato interno del proyecto.
    """
    if not datos_api:
        raise ValueError("No se recibieron datos de la API para transformar.")

    datos_actuales = datos_api.get("current", {})
    datos_ubicacion = datos_api.get("location", {})

    distrito_final = distrito or datos_ubicacion.get("name", "Desconocido")
    fecha_final = fecha or datos_ubicacion.get("localtime", "")[:10] or datetime.now().strftime("%Y-%m-%d")

    temperatura = float(datos_actuales.get("temp_c", 0.0))
    humedad = float(datos_actuales.get("humidity", 0.0))
    viento = float(datos_actuales.get("wind_kph", 0.0))
    lluvia = float(datos_actuales.get("precip_mm", 0.0))

    datos_registro = {
        "temperatura": temperatura,
        "humedad": humedad,
        "viento": viento,
        "lluvia": lluvia,
    }
    alertas_activas = alertas.evaluar_alertas(
        datos_registro,
        persistencia.obtener_umbrales_alerta(),
    )

    return {
        "fecha": fecha_final,
        "distrito": distrito_final,
        "temperatura": temperatura,
        "temp": temperatura,
        "humedad": humedad,
        "viento": viento,
        "lluvia": lluvia,
        "alertas": alertas_activas,
        "registrado_por": _obtener_identificador_usuario(usuario_actual),
        "editado": False,
        "fuente": "WeatherAPI",
        "condicion": datos_actuales.get("condition", {}).get("text", "Sin datos"),
    }


def obtener_registro_climatico(ciudad, usuario_actual=None, fecha=None, api_key=None):
    """
    Orquesta la consulta externa y devuelve un registro listo para persistencia.py.
    """
    datos_api = obtener_clima_api(ciudad, api_key=api_key)
    return transformar_respuesta_a_registro(
        datos_api,
        distrito=ciudad,
        usuario_actual=usuario_actual,
        fecha=fecha,
    )


def guardar_registro_climatico(ciudad, usuario_actual=None, fecha=None, api_key=None):
    """
    Obtiene el registro desde la API y lo guarda usando la capa de persistencia del proyecto.
    """
    nuevo_registro = obtener_registro_climatico(
        ciudad,
        usuario_actual=usuario_actual,
        fecha=fecha,
        api_key=api_key,
    )
    return persistencia.registrar_nuevo_dato(nuevo_registro)


def _extraer_error_api(respuesta):
    if respuesta is None:
        return "respuesta vacia del servicio externo"

    try:
        datos_error = respuesta.json()
        error = datos_error.get("error", {})
        mensaje = error.get("message")
        if mensaje:
            return mensaje
    except ValueError:
        pass

    return f"codigo HTTP {respuesta.status_code}"


def _obtener_identificador_usuario(usuario_actual):
    if isinstance(usuario_actual, dict):
        return usuario_actual.get("num_empleado", "API")
    return "API"


if __name__ == "__main__":
    ciudad_buscada = input("Introduce un distrito o ciudad: ").strip()

    try:
        registro = obtener_registro_climatico(ciudad_buscada)
        print(
            f"Clima actual en {registro['distrito']}: "
            f"{registro['condicion']} | {registro['temperatura']} C"
        )
    except Exception as error:
        print(f"No se pudo obtener el clima: {error}")
