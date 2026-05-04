"""
Módulo de normalización de respuestas de WeatherAPI para The Big Data Theory.
Convierte la respuesta cruda de la API al modelo interno del sistema.
"""

from datetime import datetime, UTC
import logging
import alertas
import persistencia

logger = logging.getLogger(__name__)


def normalizar_respuesta_weatherapi(datos_api: dict, latencia_ms: int) -> dict:
    """
    Normaliza la respuesta cruda de WeatherAPI al formato interno del sistema.
    """
    if not datos_api or not isinstance(datos_api, dict):
        logger.error("Respuesta de WeatherAPI inválida o vacía")
        return None

    try:
        current = datos_api.get("current", {})
        location = datos_api.get("location", {})
        condicion = current.get("condition", {}).get("text", "Sin datos")

        return {
            "temperatura": float(current.get("temp_c", 0.0)),
            "humedad": float(current.get("humidity", 0.0)),
            "viento": float(current.get("wind_kph", 0.0)),
            "lluvia": float(current.get("precip_mm", 0.0)),
            "presion": float(current.get("pressure_mb", 0.0)),
            "descripcion": condicion,
            "latencia_ms": int(latencia_ms),
            "timestamp": datetime.now(UTC).isoformat(),
            "ubicacion": {
                "nombre": location.get("name", ""),
                "region": location.get("region", ""),
                "pais": location.get("country", ""),
            },
        }
    except (TypeError, ValueError, KeyError) as error:
        logger.error(
            "Error al normalizar respuesta de WeatherAPI: %s | datos=%s",
            error,
            datos_api,
        )
        return None


def normalizar_respuesta_weatherapi_historico(datos_api: dict, latencia_ms: int) -> dict:
    """
    Normaliza la respuesta de WeatherAPI history.json al formato interno del sistema.
    """
    if not datos_api or not isinstance(datos_api, dict):
        logger.error("Respuesta de WeatherAPI history inválida o vacía")
        return None

    try:
        forecastday = datos_api.get("forecast", {}).get("forecastday", [])
        if not forecastday:
            logger.error("WeatherAPI history: forecastday vacío")
            return None

        dia = forecastday[0].get("day", {})
        condicion = dia.get("condition", {}).get("text", "Sin datos")

        return {
            "temperatura": float(dia.get("avgtemp_c", 0.0)),
            "humedad": float(dia.get("avghumidity", 0.0)),
            "viento": float(dia.get("maxwind_kph", 0.0)),
            "lluvia": float(dia.get("totalprecip_mm", 0.0)),
            "presion": 0.0,
            "descripcion": condicion,
            "latencia_ms": int(latencia_ms),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except (TypeError, ValueError, KeyError, IndexError) as error:
        logger.error(
            "Error al normalizar respuesta history de WeatherAPI: %s | datos=%s",
            error,
            datos_api,
        )
        return None


def crear_registro_api(datos_normalizados: dict, distrito: str, usuario_actual=None, fecha=None) -> dict:
    """
    Construye el registro final listo para guardar en el histórico.
    """
    if not datos_normalizados:
        logger.error("No se pueden crear datos de registro sin normalización previa")
        return None

    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    usuario_id = None
    if isinstance(usuario_actual, dict):
        usuario_id = usuario_actual.get("num_empleado", "API")

    alertas_activas = alertas.evaluar_alertas(
        {
            "temperatura": datos_normalizados["temperatura"],
            "humedad": datos_normalizados["humedad"],
            "viento": datos_normalizados["viento"],
            "lluvia": datos_normalizados["lluvia"],
        },
        persistencia.obtener_umbrales_alerta(),
    )

    return {
        "fecha": fecha,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "distrito": distrito,
        "fuente": "api",
        "proveedor_api": "weatherapi",
        "temperatura": datos_normalizados["temperatura"],
        "temp": datos_normalizados["temperatura"],
        "humedad": datos_normalizados["humedad"],
        "viento": datos_normalizados["viento"],
        "lluvia": datos_normalizados["lluvia"],
        "presion": datos_normalizados["presion"],
        "descripcion": datos_normalizados["descripcion"],
        "alertas": alertas_activas,
        "registrado_por": usuario_id,
        "editado": False,
        "latencia_ms": datos_normalizados["latencia_ms"],
        "timestamp": datos_normalizados["timestamp"],
        "condicion": datos_normalizados["descripcion"]
    }
