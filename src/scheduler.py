"""
Módulo de ingesta automática programada para The Big Data Theory.
Ejecuta capturas en horario fijo (07:00h, 15:00h, 22:00h) para todos los distritos
vía WeatherAPI usando un hilo de fondo con bucle de tiempo propio.
"""

import logging
import queue
import threading
import time
from datetime import datetime, timedelta

import api
import persistencia

logger = logging.getLogger(__name__)

# ─── Estado interno ───────────────────────────────────────────────────────────

_hilo: threading.Thread = None
_activo: bool = False
_lock = threading.Lock()
_notification_queue: queue.Queue = queue.Queue()

_ultimo_resumen = {
    "ultima_ejecucion": None,
    "guardados": 0,
    "omitidos": 0,
    "errores": 0,
    "total_distritos": 0,
}

_errores_recientes: list = []

_SUGERENCIAS_ERROR = {
    401: "Revisar la API Key en el archivo .env",
    403: "Verificar los permisos del plan API contratado",
    404: "Verificar el nombre del distrito en config.json",
    429: "Límite de peticiones alcanzado – esperar o actualizar el plan API",
    "TIMEOUT": "Tiempo de espera agotado – revisar conectividad de red",
    "CONN_ERROR": "Error de conexión – revisar red, firewall o proxy",
}


def _obtener_sugerencia(codigo):
    if codigo in _SUGERENCIAS_ERROR:
        return _SUGERENCIAS_ERROR[codigo]
    if isinstance(codigo, int) and codigo >= 500:
        return "Error del servidor WeatherAPI – intentar más tarde"
    return "Error desconocido – revisar conectividad de red"


def _registrar_error_reciente(distrito, codigo, mensaje, sugerencia):
    entrada = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "distrito": distrito,
        "codigo": codigo if codigo is not None else "N/A",
        "mensaje": mensaje,
        "sugerencia": sugerencia,
    }
    with _lock:
        _errores_recientes.insert(0, entrada)
        if len(_errores_recientes) > 20:
            _errores_recientes.pop()


# ─── Lógica del job ───────────────────────────────────────────────────────────

def _tarea_ingesta():
    """Obtiene datos de WeatherAPI para todos los distritos y encola el resultado."""
    global _ultimo_resumen

    hora_inicio = datetime.now()
    fecha = hora_inicio.strftime("%Y-%m-%d")
    distritos = persistencia.obtener_distritos_permitidos()

    guardados = omitidos = errores = 0
    detalles: list = []
    errores_lista: list = []

    logger.info(
        "Scheduler ▶ Iniciando ingesta | %s | %d distritos",
        hora_inicio.strftime("%H:%M:%S"), len(distritos),
    )

    for distrito in distritos:
        try:
            registro = api.obtener_registro_climatico(distrito)

            if not registro:
                errores += 1
                err = api._ultimo_error.copy()
                codigo = err.get("codigo")
                mensaje = err.get("mensaje", "Sin respuesta de la API")
                sugerencia = _obtener_sugerencia(codigo)
                _registrar_error_reciente(distrito, codigo, mensaje, sugerencia)
                errores_lista.append({
                    "distrito": distrito,
                    "codigo": codigo,
                    "mensaje": mensaje,
                    "sugerencia": sugerencia,
                })
                logger.warning("Scheduler ❌ %s | Error %s: %s", distrito, codigo, mensaje)
                continue

            with _lock:
                historico = persistencia.leer_historico()
                ya_existe = any(
                    r.get("fecha") == fecha
                    and r.get("distrito", "").lower() == distrito.lower()
                    and r.get("fuente") == "api"
                    for r in historico
                )
                if ya_existe:
                    omitidos += 1
                    detalles.append({
                        "distrito": distrito,
                        "estado": "omitido",
                        "temp": registro.get("temperatura", 0),
                        "humedad": registro.get("humedad", 0),
                        "viento": registro.get("viento", 0),
                        "lluvia": registro.get("lluvia", 0),
                        "http_code": 200,
                        "alertas": registro.get("alertas", []),
                    })
                else:
                    historico.append(registro)
                    persistencia.actualizar_base_de_datos(historico)
                    guardados += 1
                    detalles.append({
                        "distrito": distrito,
                        "estado": "guardado",
                        "temp": registro.get("temperatura", 0),
                        "humedad": registro.get("humedad", 0),
                        "viento": registro.get("viento", 0),
                        "lluvia": registro.get("lluvia", 0),
                        "http_code": 200,
                        "alertas": registro.get("alertas", []),
                    })
                    logger.info(
                        "Scheduler ✅ %s | %.1f°C", distrito, registro.get("temperatura", 0)
                    )

        except Exception as exc:
            errores += 1
            sugerencia = "Revisar conectividad de red"
            _registrar_error_reciente(distrito, None, str(exc)[:100], sugerencia)
            errores_lista.append({
                "distrito": distrito,
                "codigo": "ERROR",
                "mensaje": str(exc)[:100],
                "sugerencia": sugerencia,
            })
            logger.error("Scheduler ❌ Error en %s: %s", distrito, exc)

    _ultimo_resumen = {
        "ultima_ejecucion": hora_inicio,
        "guardados": guardados,
        "omitidos": omitidos,
        "errores": errores,
        "total_distritos": len(distritos),
    }

    logger.info(
        "Scheduler ■ Completada | Guardados: %d | Omitidos: %d | Errores: %d",
        guardados, omitidos, errores,
    )

    _notification_queue.put({
        "timestamp": hora_inicio,
        "guardados": guardados,
        "omitidos": omitidos,
        "errores": errores,
        "detalles": detalles,
        "errores_lista": errores_lista,
    })


def _hilo_bucle():
    """Bucle del hilo de fondo: dispara ingesta a las 07:00, 15:00 y 22:00."""
    HORAS = {7, 15, 22}
    disparado: set = set()

    while _activo:
        ahora = datetime.now()
        clave = (ahora.date(), ahora.hour)

        if ahora.hour in HORAS and clave not in disparado:
            disparado.add(clave)
            _tarea_ingesta()

        # Limpiar claves de días anteriores
        hoy = ahora.date()
        disparado = {k for k in disparado if k[0] == hoy}

        time.sleep(30)


# ─── API pública ──────────────────────────────────────────────────────────────

def iniciar():
    """Inicia el scheduler y lanza una ingesta inmediata en hilo separado."""
    global _hilo, _activo

    if _activo:
        return

    _activo = True
    _hilo = threading.Thread(target=_hilo_bucle, daemon=True, name="SchedulerTBDT")
    _hilo.start()
    logger.info("Scheduler iniciado | Horario: 07:00h | 15:00h | 22:00h")


def detener():
    """Detiene el scheduler."""
    global _activo, _hilo
    _activo = False
    _hilo = None
    logger.info("Scheduler detenido.")


def esta_activo() -> bool:
    return _activo and _hilo is not None and _hilo.is_alive()


def obtener_proximo_disparo() -> datetime:
    if not _activo:
        return None
    ahora = datetime.now()
    for hora in sorted([7, 15, 22]):
        if ahora.hour < hora:
            return ahora.replace(hour=hora, minute=0, second=0, microsecond=0)
    manana = ahora.date() + timedelta(days=1)
    return datetime(manana.year, manana.month, manana.day, 7, 0, 0)


def obtener_resumen() -> dict:
    return _ultimo_resumen.copy()


def obtener_errores_recientes() -> list:
    return list(_errores_recientes)


def obtener_notificacion_pendiente() -> dict:
    """Devuelve la siguiente notificación de ingesta pendiente, o None si no hay."""
    try:
        return _notification_queue.get_nowait()
    except queue.Empty:
        return None
