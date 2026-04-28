"""
Módulo de normalización de respuestas de WeatherAPI para The Big Data Theory.
Convierte la respuesta cruda de la API al modelo interno del sistema.
"""

from datetime import datetime
import logging
import alertas
import persistencia

logger = logging.getLogger(__name__)


def normalizar_respuesta_weatherapi(datos_api: dict, latencia_ms: int) -> dict:
    """
    Normaliza la respuesta cruda de WeatherAPI al formato interno del sistema.

    Args:
        datos_api (dict): JSON crudo devuelto por WeatherAPI.
        latencia_ms (int): Latencia de la petición HTTP en milisegundos.

    Returns:
        dict or None: Datos normalizados con temperatura, humedad, viento, lluvia,
                      presión, descripción y metadatos. None si la respuesta es inválida.
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
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except (TypeError, ValueError, KeyError) as error:
        logger.error(
            "Error al normalizar respuesta de WeatherAPI: %s | datos=%s",
            error,
            datos_api,
        )
        return None


def crear_registro_api(datos_normalizados: dict, distrito: str, usuario_actual=None, fecha=None) -> dict:
    """
    Construye el registro final listo para guardar en el histórico.

    Args:
        datos_normalizados (dict): Salida de normalizar_respuesta_weatherapi().
        distrito (str): Nombre del distrito solicitado.
        usuario_actual (dict, optional): Datos del usuario autenticado.
        fecha (str, optional): Fecha del registro en formato AAAA-MM-DD.

    Returns:
        dict or None: Registro completo con todos los campos del modelo de datos, o None si falla.
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
