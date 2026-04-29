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
from normalizador import normalizar_respuesta_weatherapi, normalizar_respuesta_weatherapi_historico, crear_registro_api

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")
WEATHERAPI_BASE_URL = os.getenv("WEATHERAPI_BASE_URL", "http://api.weatherapi.com/v1/current.json")
WEATHERAPI_HISTORY_URL = "http://api.weatherapi.com/v1/history.json"
WEATHERAPI_TIMEOUT = int(os.getenv("WEATHERAPI_TIMEOUT_SEGUNDOS", "5"))
WEATHERAPI_REINTENTOS = int(os.getenv("WEATHERAPI_REINTENTOS", "3"))

logger = logging.getLogger(__name__)

_ultimo_error = {"codigo": None, "mensaje": "", "ciudad": ""}

_session = requests.Session()
_session.headers.update({"User-Agent": "TheBigDataTheory/2.0"})


def obtener_respuesta_weatherapi(ciudad: str, idioma: str = "es") -> tuple:
    """
    Consulta WeatherAPI y devuelve la respuesta JSON cruda junto con la latencia medida.
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

    for intento in range(1, WEATHERAPI_REINTENTOS + 1):
        try:
            inicio = time.time()
            response = _session.get(
                WEATHERAPI_BASE_URL,
                params=params,
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


def obtener_respuesta_weatherapi_historico(ciudad: str, fecha: str) -> tuple:
    """
    Consulta WeatherAPI history.json para una fecha pasada y devuelve la respuesta JSON con la latencia.
    """
    if not WEATHERAPI_API_KEY:
        logger.error("WEATHERAPI_API_KEY no configurada en .env")
        return None, None

    params = {
        "key": WEATHERAPI_API_KEY,
        "q": ciudad.strip(),
        "dt": fecha,
        "lang": "es",
    }

    for intento in range(1, WEATHERAPI_REINTENTOS + 1):
        try:
            inicio = time.time()
            response = _session.get(
                WEATHERAPI_HISTORY_URL,
                params=params,
                timeout=WEATHERAPI_TIMEOUT,
            )
            latencia_ms = int((time.time() - inicio) * 1000)

            if response.status_code == 200:
                logger.info(
                    f"✅ WeatherAPI History OK | Ciudad: {ciudad} | Fecha: {fecha} | Latencia: {latencia_ms}ms"
                )
                return response.json(), latencia_ms

            if response.status_code == 401:
                _ultimo_error.update({"codigo": 401, "mensaje": "API key inválida o expirada", "ciudad": ciudad})
                logger.error("🔴 WeatherAPI History AUTH ERROR | Status: 401")
                return None, None

            if response.status_code == 403:
                _ultimo_error.update({"codigo": 403, "mensaje": "Acceso denegado al endpoint history", "ciudad": ciudad})
                logger.error("🔴 WeatherAPI History FORBIDDEN | Status: 403")
                return None, None

            if response.status_code == 404:
                _ultimo_error.update({"codigo": 404, "mensaje": f"Ciudad '{ciudad}' no encontrada", "ciudad": ciudad})
                logger.warning("🟡 WeatherAPI History NOT FOUND | Status: 404 | Ciudad: %s", ciudad)
                return None, None

            if response.status_code == 429:
                delay = 60 * intento
                _ultimo_error.update({"codigo": 429, "mensaje": "Límite de peticiones alcanzado", "ciudad": ciudad})
                logger.warning("⏸️ WeatherAPI History RATE LIMIT | Intento %d/%d | Esperando %ds", intento, WEATHERAPI_REINTENTOS, delay)
                time.sleep(delay)
                continue

            if response.status_code >= 500:
                delay = 5 * intento
                _ultimo_error.update({"codigo": response.status_code, "mensaje": "Error del servidor WeatherAPI", "ciudad": ciudad})
                logger.warning("⚠️ WeatherAPI History SERVER ERROR | Status: %s | Intento %d/%d", response.status_code, intento, WEATHERAPI_REINTENTOS)
                time.sleep(delay)
                continue

            _ultimo_error.update({"codigo": response.status_code, "mensaje": f"Error HTTP {response.status_code}", "ciudad": ciudad})
            logger.error("❌ WeatherAPI History ERROR | Status: %s | %s", response.status_code, response.text[:200])
            return None, None

        except requests.Timeout:
            _ultimo_error.update({"codigo": "TIMEOUT", "mensaje": "Tiempo de espera agotado", "ciudad": ciudad})
            if intento < WEATHERAPI_REINTENTOS:
                time.sleep(5 * intento)
            continue

        except requests.ConnectionError as error:
            _ultimo_error.update({"codigo": "CONN_ERROR", "mensaje": "Error de conexión de red", "ciudad": ciudad})
            if intento < WEATHERAPI_REINTENTOS:
                time.sleep(5 * intento)
            continue

        except Exception as error:
            _ultimo_error.update({"codigo": "ERROR", "mensaje": str(error)[:100], "ciudad": ciudad})
            logger.error("❌ WeatherAPI History UNEXPECTED ERROR | %s: %s", type(error).__name__, error)
            return None, None

    logger.error("🔴 WeatherAPI History FALLÓ | Ciudad: %s | Fecha: %s | Agotados %d reintentos", ciudad, fecha, WEATHERAPI_REINTENTOS)
    return None, None


def obtener_registro_climatico(ciudad, usuario_actual=None, fecha=None):
    """
    Orquesta la consulta a WeatherAPI y devuelve un registro listo para persistencia.
    Usa history.json para fechas pasadas y current.json para la fecha de hoy.
    """
    from datetime import date as _date

    query = persistencia.obtener_query_api(ciudad)
    hoy = _date.today().isoformat()
    es_fecha_pasada = fecha is not None and fecha < hoy

    if es_fecha_pasada:
        datos_raw, latencia_ms = obtener_respuesta_weatherapi_historico(query, fecha)
        if not datos_raw:
            return None
        datos_normalizados = normalizar_respuesta_weatherapi_historico(datos_raw, latencia_ms)
    else:
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


