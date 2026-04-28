"""
Módulo de ingesta de datos climáticos vía WeatherAPI para The Big Data Theory.
Gestiona la conexión, reintentos, manejo de errores HTTP y normalización de respuestas.
"""

import os
import time
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv

import alertas
import persistencia
from normalizador import normalizar_respuesta_weatherapi, crear_registro_api

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")
WEATHERAPI_BASE_URL = os.getenv("WEATHERAPI_BASE_URL", "http://api.weatherapi.com/v1/current.json")
WEATHERAPI_TIMEOUT = int(os.getenv("WEATHERAPI_TIMEOUT_SEGUNDOS", "5"))
WEATHERAPI_REINTENTOS = int(os.getenv("WEATHERAPI_REINTENTOS", "3"))

logger = logging.getLogger(__name__)

_ultimo_error = {"codigo": None, "mensaje": "", "ciudad": ""}


def obtener_respuesta_weatherapi(ciudad: str, idioma: str = "es") -> tuple:
    """
    Consulta WeatherAPI y devuelve la respuesta JSON cruda junto con la latencia medida.

    Args:
        ciudad (str): Nombre de la ciudad o distrito a consultar.
        idioma (str): Código de idioma para la descripción de la condición. Por defecto "es".

    Returns:
        tuple: (dict respuesta_json, int latencia_ms) o (None, None) si falla.
    """
    if not WEATHERAPI_API_KEY:
        logger.error("WEATHERAPI_API_KEY no configurada en .env")
        return None, None

    params = {
        "key": WEATHERAPI_API_KEY,
        "q": ciudad.strip(),
        "lang": idioma,
        "aqi": "no"
    }

    headers = {
        "User-Agent": "TheBigDataTheory/2.0"
    }

    for intento in range(1, WEATHERAPI_REINTENTOS + 1):
        try:
            inicio = time.time()
            response = requests.get(
                WEATHERAPI_BASE_URL,
                params=params,
                headers=headers,
                timeout=WEATHERAPI_TIMEOUT
            )
            latencia_ms = int((time.time() - inicio) * 1000)

            if response.status_code == 200:
                logger.info(
                    f"✅ WeatherAPI OK | Ciudad: {ciudad} | "
                    f"Status: 200 | Latencia: {latencia_ms}ms"
                )
                return response.json(), latencia_ms

            if response.status_code == 401:
                logger.error(
                    f"🔴 WeatherAPI AUTH ERROR | Status: 401 | "
                    f"API key inválida o expirada"
                )
                _ultimo_error.update({"codigo": 401, "mensaje": "API key inválida o expirada", "ciudad": ciudad})
                return None, None

            if response.status_code == 403:
                logger.error(
                    f"🔴 WeatherAPI FORBIDDEN | Status: 403 | "
                    f"Acceso denegado al endpoint"
                )
                _ultimo_error.update({"codigo": 403, "mensaje": "Acceso denegado al endpoint", "ciudad": ciudad})
                return None, None

            if response.status_code == 404:
                logger.warning(
                    f"🟡 WeatherAPI NOT FOUND | Status: 404 | "
                    f"Ciudad '{ciudad}' no encontrada"
                )
                _ultimo_error.update({"codigo": 404, "mensaje": f"Ciudad '{ciudad}' no encontrada", "ciudad": ciudad})
                return None, None

            if response.status_code == 429:
                delay = 60 * intento
                logger.warning(
                    f"⏸️ WeatherAPI RATE LIMIT | Status: 429 | "
                    f"Intento {intento}/{WEATHERAPI_REINTENTOS} | Esperando {delay}s..."
                )
                _ultimo_error.update({"codigo": 429, "mensaje": "Límite de peticiones alcanzado", "ciudad": ciudad})
                time.sleep(delay)
                continue

            if response.status_code >= 500:
                delay = 5 * intento
                logger.warning(
                    f"⚠️ WeatherAPI SERVER ERROR | Status: {response.status_code} | "
                    f"Intento {intento}/{WEATHERAPI_REINTENTOS} | Esperando {delay}s..."
                )
                _ultimo_error.update({"codigo": response.status_code, "mensaje": "Error del servidor WeatherAPI", "ciudad": ciudad})
                time.sleep(delay)
                continue

            logger.error(
                f"❌ WeatherAPI ERROR | Status: {response.status_code} | "
                f"Respuesta: {response.text[:200]}"
            )
            _ultimo_error.update({"codigo": response.status_code, "mensaje": f"Error HTTP {response.status_code}", "ciudad": ciudad})
            return None, None

        except requests.Timeout:
            delay = 5 * intento
            logger.warning(
                f"⏸️ WeatherAPI TIMEOUT | Intento {intento}/{WEATHERAPI_REINTENTOS} | "
                f"Servidor tardó más de {WEATHERAPI_TIMEOUT}s | Esperando {delay}s..."
            )
            _ultimo_error.update({"codigo": "TIMEOUT", "mensaje": "Tiempo de espera agotado", "ciudad": ciudad})
            if intento < WEATHERAPI_REINTENTOS:
                time.sleep(delay)
            continue

        except requests.ConnectionError as error:
            delay = 5 * intento
            logger.warning(
                f"⏸️ WeatherAPI CONNECTION ERROR | Intento {intento}/{WEATHERAPI_REINTENTOS} | "
                f"Error: {str(error)[:100]} | Esperando {delay}s..."
            )
            _ultimo_error.update({"codigo": "CONN_ERROR", "mensaje": "Error de conexión de red", "ciudad": ciudad})
            if intento < WEATHERAPI_REINTENTOS:
                time.sleep(delay)
            continue

        except Exception as error:
            logger.error(
                f"❌ WeatherAPI UNEXPECTED ERROR | {type(error).__name__}: {error}"
            )
            _ultimo_error.update({"codigo": "ERROR", "mensaje": str(error)[:100], "ciudad": ciudad})
            return None, None

    logger.error(
        f"🔴 WeatherAPI FALLÓ | Ciudad: {ciudad} | "
        f"Agotados {WEATHERAPI_REINTENTOS} reintentos"
    )
    return None, None


def obtener_registro_climatico(ciudad, usuario_actual=None, fecha=None):
    """
    Orquesta la consulta a WeatherAPI y devuelve un registro listo para persistencia.

    Args:
        ciudad (str): Nombre del distrito o ciudad.
        usuario_actual (dict, optional): Datos del usuario autenticado.
        fecha (str, optional): Fecha del registro en formato AAAA-MM-DD. Por defecto la fecha actual.

    Returns:
        dict or None: Registro climático completo, o None si la consulta falla.
    """
    query = persistencia.obtener_query_api(ciudad)
    datos_raw, latencia_ms = obtener_respuesta_weatherapi(query)
    if not datos_raw:
        return None

    datos_normalizados = normalizar_respuesta_weatherapi(datos_raw, latencia_ms)
    if not datos_normalizados:
        return None

    return crear_registro_api(
        datos_normalizados,
        distrito=ciudad,
        usuario_actual=usuario_actual,
        fecha=fecha,
    )


def guardar_registro_climatico(ciudad, usuario_actual=None, fecha=None):
    """
    Obtiene el registro climático desde la API y lo guarda en el histórico.

    Args:
        ciudad (str): Nombre del distrito o ciudad.
        usuario_actual (dict, optional): Datos del usuario autenticado.
        fecha (str, optional): Fecha del registro en formato AAAA-MM-DD.

    Returns:
        bool: True si el registro fue guardado correctamente.
    """
    nuevo_registro = obtener_registro_climatico(
        ciudad,
        usuario_actual=usuario_actual,
        fecha=fecha,
    )

    if not nuevo_registro:
        logger.error(f"No se pudo obtener datos para {ciudad}")
        return False

    return persistencia.registrar_nuevo_dato(nuevo_registro)


def test_conexion_api():
    """
    Función de prueba para verificar que la API funciona correctamente.
    Úsala así desde terminal:

        python -c "from Api import test_conexion_api; test_conexion_api()"
    """
    print("\n" + "="*70)
    print("🧪 PRUEBA DE CONEXIÓN A WeatherAPI")
    print("="*70 + "\n")

    ciudades_prueba = ["Madrid", "Barcelona", "Valencia"]

    for ciudad in ciudades_prueba:
        print(f"📍 Consultando: {ciudad}")
        datos = obtener_registro_climatico(ciudad)

        if datos:
            print(f"   ✅ Temperatura: {datos['temperatura']}°C")
            print(f"   ✅ Humedad: {datos['humedad']}%")
            print(f"   ✅ Viento: {datos['viento']} km/h")
            print(f"   ✅ Latencia: {datos['latencia_ms']}ms\n")
        else:
            print(f"   ❌ Fallo al obtener datos\n")

if __name__ == "__main__":
    ciudad_buscada = input("Introduce un distrito o ciudad: ").strip()

    try:
        registro = obtener_registro_climatico(ciudad_buscada)
        if registro:
            print(
                f"Clima actual en {registro['distrito']}: "
                f"{registro['descripcion']} | {registro['temperatura']}°C"
            )
        else:
            print("No se pudo obtener el clima")
    except Exception as error:
        print(f"No se pudo obtener el clima: {error}")
