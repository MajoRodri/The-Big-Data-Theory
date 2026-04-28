"""
Módulo de datos históricos desde Open-Meteo Archive para The Big Data Theory.
Implementa caché inteligente: verifica la BD local antes de llamar a la API externa,
descargando solo las fechas que falten y guardándolas en datos_clima.json.
"""

import json
import logging
import time
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

import requests

import alertas
import persistencia

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = 10
RUTA_CONFIG = Path(__file__).resolve().parent.parent / "data" / "config.json"

_VARIABLES = (
    "temperature_2m_mean,"
    "relative_humidity_2m_mean,"
    "windspeed_10m_max,"
    "precipitation_sum"
)

logger = logging.getLogger("api_history")


# ─── Helpers internos ────────────────────────────────────────────────────────

def _cargar_alias_api() -> dict:
    """Lee el mapa distrito → 'lat,lon' del config.json."""
    try:
        with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f).get("alias_api", {})
    except Exception as exc:
        logger.error("No se pudo leer alias_api de config.json: %s", exc)
        return {}


def _coordenadas(distrito: str) -> Optional[tuple]:
    """
    Devuelve (latitud, longitud) para un distrito usando alias_api del config.

    Args:
        distrito: Nombre oficial del distrito de Madrid.

    Returns:
        Tupla (lat, lon) como floats, o None si no existe la entrada.
    """
    alias = _cargar_alias_api()
    coords_str = alias.get(distrito)
    if not coords_str:
        logger.warning("Coordenadas no encontradas para el distrito: %s", distrito)
        return None
    try:
        lat, lon = coords_str.split(",")
        return float(lat.strip()), float(lon.strip())
    except ValueError:
        logger.error("Formato inválido de coordenadas para %s: %s", distrito, coords_str)
        return None


def _fetch_open_meteo(
    lat: float,
    lon: float,
    fecha_inicio: str,
    fecha_fin: str,
) -> Optional[dict]:
    """
    Realiza la petición HTTP a Open-Meteo Archive y devuelve la respuesta JSON.

    Args:
        lat: Latitud del punto geográfico.
        lon: Longitud del punto geográfico.
        fecha_inicio: Fecha de inicio del rango (AAAA-MM-DD).
        fecha_fin: Fecha de fin del rango (AAAA-MM-DD).

    Returns:
        Diccionario con la respuesta JSON, o None si la petición falla.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": fecha_inicio,
        "end_date": fecha_fin,
        "daily": _VARIABLES,
        "timezone": "Europe/Madrid",
    }
    _REINTENTOS = 3
    for intento in range(1, _REINTENTOS + 1):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT)

            if resp.status_code == 200:
                logger.info(
                    "Open-Meteo OK | lat=%.3f lon=%.3f | %s → %s",
                    lat, lon, fecha_inicio, fecha_fin,
                )
                return resp.json()

            if resp.status_code == 400:
                logger.error(
                    "Open-Meteo 400 BAD REQUEST | %s → %s | %s",
                    fecha_inicio, fecha_fin, resp.text[:200],
                )
                return None

            if resp.status_code in (401, 403):
                logger.error(
                    "Open-Meteo %s ACCESO DENEGADO | lat=%.3f lon=%.3f",
                    resp.status_code, lat, lon,
                )
                return None

            if resp.status_code == 404:
                logger.error(
                    "Open-Meteo 404 NO ENCONTRADO | lat=%.3f lon=%.3f | %s → %s",
                    lat, lon, fecha_inicio, fecha_fin,
                )
                return None

            if resp.status_code == 429:
                delay = 30 * intento
                logger.warning(
                    "Open-Meteo 429 RATE LIMIT | intento %d/%d | esperando %ds",
                    intento, _REINTENTOS, delay,
                )
                if intento < _REINTENTOS:
                    time.sleep(delay)
                continue

            if resp.status_code >= 500:
                delay = 5 * intento
                logger.warning(
                    "Open-Meteo %s SERVER ERROR | intento %d/%d | esperando %ds",
                    resp.status_code, intento, _REINTENTOS, delay,
                )
                if intento < _REINTENTOS:
                    time.sleep(delay)
                continue

            logger.error(
                "Open-Meteo HTTP %s | lat=%.3f lon=%.3f | %s → %s | %s",
                resp.status_code, lat, lon, fecha_inicio, fecha_fin, resp.text[:200],
            )
            return None

        except requests.Timeout:
            logger.warning(
                "Open-Meteo TIMEOUT | intento %d/%d | lat=%.3f lon=%.3f | %s → %s",
                intento, _REINTENTOS, lat, lon, fecha_inicio, fecha_fin,
            )
            if intento < _REINTENTOS:
                time.sleep(5 * intento)
        except requests.ConnectionError as exc:
            logger.warning(
                "Open-Meteo CONNECTION ERROR | intento %d/%d | %s → %s | %s",
                intento, _REINTENTOS, fecha_inicio, fecha_fin, exc,
            )
            if intento < _REINTENTOS:
                time.sleep(5 * intento)
        except Exception as exc:
            logger.error("Open-Meteo ERROR inesperado: %s", exc)
            return None

    logger.error(
        "Open-Meteo FALLÓ tras %d intentos | lat=%.3f lon=%.3f | %s → %s",
        _REINTENTOS, lat, lon, fecha_inicio, fecha_fin,
    )
    return None


def _convertir_a_registros(respuesta: dict, distrito: str) -> list:
    """
    Convierte la respuesta diaria de Open-Meteo al formato interno del sistema.

    Args:
        respuesta: JSON crudo de Open-Meteo con la clave 'daily'.
        distrito: Nombre del distrito al que pertenecen los datos.

    Returns:
        Lista de registros en el formato del modelo interno de datos.
    """
    diario = respuesta.get("daily", {})
    fechas = diario.get("time", [])
    temps = diario.get("temperature_2m_mean", [])
    humedades = diario.get("relative_humidity_2m_mean", [])
    vientos = diario.get("windspeed_10m_max", [])
    lluvias = diario.get("precipitation_sum", [])

    umbrales = persistencia.obtener_umbrales_alerta()
    registros = []

    for i, fecha in enumerate(fechas):
        temp = float(temps[i]) if i < len(temps) and temps[i] is not None else 0.0
        humedad = float(humedades[i]) if i < len(humedades) and humedades[i] is not None else 0.0
        viento = float(vientos[i]) if i < len(vientos) and vientos[i] is not None else 0.0
        lluvia = float(lluvias[i]) if i < len(lluvias) and lluvias[i] is not None else 0.0

        alertas_activas = alertas.evaluar_alertas(
            {"temperatura": temp, "humedad": humedad, "viento": viento, "lluvia": lluvia},
            umbrales,
        )
        registros.append({
            "fecha": fecha,
            "distrito": distrito,
            "fuente": "historico",
            "proveedor_api": "open-meteo-archive",
            "temperatura": round(temp, 1),
            "temp": round(temp, 1),
            "humedad": round(humedad, 1),
            "viento": round(viento, 1),
            "lluvia": round(lluvia, 1),
            "alertas": alertas_activas,
            "registrado_por": "Sistema",
            "editado": False,
        })

    return registros


def _guardar_en_lote(registros_nuevos: list) -> tuple:
    """
    Inserta múltiples registros en la BD con una sola operación de escritura.
    Respeta las reglas de deduplicación: máximo 2 por fecha+distrito, sin fuente repetida.

    Args:
        registros_nuevos: Lista de registros a insertar.

    Returns:
        Tupla (guardados, omitidos) con el conteo de registros procesados.
    """
    if not registros_nuevos:
        return 0, 0

    historico = persistencia.leer_historico()
    distritos_oficiales = persistencia.obtener_distritos_permitidos()
    mapa_dist = {d.lower(): d for d in distritos_oficiales}

    existentes: dict = {}
    for r in historico:
        key = (r.get("fecha", ""), r.get("distrito", "").lower())
        existentes.setdefault(key, []).append(r.get("fuente", "manual"))

    guardados = 0
    omitidos = 0
    nuevos = []

    for reg in registros_nuevos:
        dist_lower = reg.get("distrito", "").lower()
        dist_oficial = mapa_dist.get(dist_lower, reg.get("distrito", ""))
        key = (reg.get("fecha", ""), dist_lower)
        fuentes = existentes.get(key, [])

        if len(fuentes) >= 2 or reg.get("fuente") in fuentes:
            omitidos += 1
            continue

        reg = dict(reg)
        reg["distrito"] = dist_oficial
        nuevos.append(reg)
        fuentes = list(fuentes) + [reg.get("fuente")]
        existentes[key] = fuentes
        guardados += 1

    if nuevos:
        historico.extend(nuevos)
        persistencia.actualizar_base_de_datos(historico)

    return guardados, omitidos


def _fechas_presentes(distrito: str, fecha_inicio: str, fecha_fin: str) -> set:
    """
    Devuelve el conjunto de fechas ya existentes en la BD para un distrito y rango.

    Args:
        distrito: Nombre oficial del distrito.
        fecha_inicio: Inicio del rango (AAAA-MM-DD).
        fecha_fin: Fin del rango (AAAA-MM-DD).

    Returns:
        Conjunto de strings con las fechas ya almacenadas.
    """
    historico = persistencia.leer_historico()
    return {
        r["fecha"]
        for r in historico
        if r.get("distrito", "").lower() == distrito.lower()
        and fecha_inicio <= r.get("fecha", "") <= fecha_fin
    }


# ─── API pública ─────────────────────────────────────────────────────────────

def asegurar_datos_rango(
    distrito: str,
    fecha_inicio: str,
    fecha_fin: str,
) -> list:
    """
    Garantiza que existan registros para el distrito en el rango de fechas dado.
    Descarga de Open-Meteo Archive solo las fechas que falten en la BD local.

    Args:
        distrito: Nombre oficial del distrito de Madrid.
        fecha_inicio: Fecha de inicio del rango (AAAA-MM-DD).
        fecha_fin: Fecha de fin del rango (AAAA-MM-DD).

    Returns:
        Lista de mensajes de error. Lista vacía si todo fue correcto.
    """
    coords = _coordenadas(distrito)
    if not coords:
        err = f"{distrito}: coordenadas no encontradas en config.json"
        logger.error(err)
        return [err]

    presentes = _fechas_presentes(distrito, fecha_inicio, fecha_fin)
    inicio = date.fromisoformat(fecha_inicio)
    fin = date.fromisoformat(fecha_fin)
    todas = {str(inicio + timedelta(days=i)) for i in range((fin - inicio).days + 1)}
    faltantes = todas - presentes

    if not faltantes:
        return []

    lat, lon = coords
    respuesta = _fetch_open_meteo(lat, lon, fecha_inicio, fecha_fin)
    if respuesta is None:
        err = f"{distrito}: Open-Meteo no respondió ({fecha_inicio} → {fecha_fin})"
        logger.error(err)
        return [err]

    registros = _convertir_a_registros(respuesta, distrito)
    registros_faltantes = [r for r in registros if r["fecha"] in faltantes]
    _guardar_en_lote(registros_faltantes)
    return []


def asegurar_datos_mes(distrito: str, anio: int, mes: int) -> list:
    """
    Garantiza que existan datos diarios para un distrito durante un mes completo.

    Args:
        distrito: Nombre oficial del distrito de Madrid.
        anio: Año como entero (ej. 2023).
        mes: Mes como entero 1-12.

    Returns:
        Lista de mensajes de error. Lista vacía si todo fue correcto.
    """
    _, dias = monthrange(anio, mes)
    return asegurar_datos_rango(
        distrito,
        f"{anio}-{mes:02d}-01",
        f"{anio}-{mes:02d}-{dias:02d}",
    )


def asegurar_datos_anio(distrito: str, anio: int) -> list:
    """
    Garantiza que existan datos diarios para un distrito durante un año completo.

    Args:
        distrito: Nombre oficial del distrito de Madrid.
        anio: Año como entero (ej. 2023).

    Returns:
        Lista de mensajes de error. Lista vacía si todo fue correcto.
    """
    return asegurar_datos_rango(distrito, f"{anio}-01-01", f"{anio}-12-31")


def consultar_datos_mes_sin_guardar(distrito: str, anio: int, mes: int) -> list:
    """
    Consulta Open-Meteo para un distrito/año/mes y devuelve los registros diarios
    sin guardar nada en la BD local. Recorta el rango al día de hoy si el mes es
    el actual, para no pedir fechas futuras.

    Args:
        distrito: Nombre oficial del distrito de Madrid.
        anio: Año como entero.
        mes: Mes como entero 1-12.

    Returns:
        Lista de registros diarios en formato interno, o lista vacía si falla.
    """
    coords = _coordenadas(distrito)
    if not coords:
        logger.error("Coordenadas no encontradas para %s", distrito)
        return []

    _, dias = monthrange(anio, mes)
    fecha_inicio = f"{anio}-{mes:02d}-01"
    fecha_fin_mes = f"{anio}-{mes:02d}-{dias:02d}"
    hoy = date.today()
    fecha_fin = min(fecha_fin_mes, str(hoy))

    if fecha_inicio > str(hoy):
        logger.warning("Mes %s/%s es futuro — sin datos disponibles", mes, anio)
        return []

    lat, lon = coords
    respuesta = _fetch_open_meteo(lat, lon, fecha_inicio, fecha_fin)
    if respuesta is None:
        return []

    return _convertir_a_registros(respuesta, distrito)


_LAT_MADRID_CENTRO = 40.42
_LON_MADRID_CENTRO = -3.676


def consultar_medias_anuales_madrid(anio_inicio: int, anio_fin: int) -> dict:
    """
    Consulta Open-Meteo Archive para el centroide de Madrid en el rango de años dado.
    No guarda nada en la BD local — solo devuelve las medias anuales.

    Args:
        anio_inicio: Primer año del rango (inclusive).
        anio_fin: Último año del rango (inclusive).

    Returns:
        Diccionario {str(anio): float(media_temp)} para cada año con datos disponibles.
    """
    hoy = date.today()
    medias = {}
    for anio in range(anio_inicio, anio_fin + 1):
        fecha_inicio = f"{anio}-01-01"
        fecha_fin = min(f"{anio}-12-31", str(hoy))

        if fecha_inicio > str(hoy):
            logger.warning("Año %s es futuro — sin datos disponibles", anio)
            continue

        respuesta = _fetch_open_meteo(
            _LAT_MADRID_CENTRO, _LON_MADRID_CENTRO,
            fecha_inicio, fecha_fin,
        )
        if respuesta is None:
            logger.warning("Sin respuesta de Open-Meteo para el año %s", anio)
            continue
        temps = [
            t for t in respuesta.get("daily", {}).get("temperature_2m_mean", [])
            if t is not None
        ]
        if temps:
            medias[str(anio)] = round(sum(temps) / len(temps), 2)
    return medias


def asegurar_datos_fecha_todos_distritos(
    fecha: str,
    callback_progreso: Optional[Callable] = None,
) -> dict:
    """
    Garantiza que todos los distritos tengan datos para la fecha indicada.
    Agrupa todos los registros nuevos en una sola escritura para mayor eficiencia.

    Args:
        fecha: Fecha exacta en formato AAAA-MM-DD.
        callback_progreso: Función opcional llamada antes de cada descarga.
                           Firma: callback(actual: int, total: int, distrito: str).

    Returns:
        Diccionario {nombre_distrito: True si hay datos, False si falló la descarga}.
    """
    distritos = persistencia.obtener_distritos_permitidos()
    historico = persistencia.leer_historico()
    presentes = {r.get("distrito", "") for r in historico if r.get("fecha") == fecha}
    pendientes = [d for d in distritos if d not in presentes]
    resultado = {d: True for d in distritos}

    if not pendientes:
        return resultado

    todos_nuevos = []
    for i, distrito in enumerate(pendientes):
        if callback_progreso:
            callback_progreso(i + 1, len(pendientes), distrito)
        coords = _coordenadas(distrito)
        if not coords:
            resultado[distrito] = False
            logger.error("Coordenadas no encontradas para %s.", distrito)
            continue
        lat, lon = coords
        respuesta = _fetch_open_meteo(lat, lon, fecha, fecha)
        if respuesta is None:
            resultado[distrito] = False
            logger.error("Open-Meteo no respondió para %s en %s.", distrito, fecha)
            continue
        registros = _convertir_a_registros(respuesta, distrito)
        todos_nuevos.extend(registros)

    if todos_nuevos:
        _guardar_en_lote(todos_nuevos)

    return resultado
