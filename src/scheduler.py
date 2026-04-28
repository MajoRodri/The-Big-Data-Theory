"""
Módulo de ingesta automática programada para The Big Data Theory.
Ejecuta capturas en horario fijo (07:00h, 15:00h, 22:00h) para todos los distritos
vía WeatherAPI usando APScheduler en un hilo de fondo (daemon thread).
"""

import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import Api
import persistencia

logger = logging.getLogger(__name__)

# ─── Estado interno ───────────────────────────────────────────────────────────

_scheduler = None
_lock = threading.Lock()

_ultimo_resumen = {
    "ultima_ejecucion": None,
    "guardados": 0,
    "omitidos": 0,
    "errores": 0,
    "total_distritos": 0,
}

_errores_recientes = []

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
    return "Error desconocido – revisar logs del sistema (app.log)"


def _registrar_error_reciente(distrito, codigo, mensaje, sugerencia):
    global _errores_recientes
    entrada = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "distrito": distrito,
        "codigo": codigo if codigo is not None else "N/A",
        "mensaje": mensaje,
        "sugerencia": sugerencia,
    }
    _errores_recientes.insert(0, entrada)
    if len(_errores_recientes) > 20:
        _errores_recientes.pop()


# ─── Lógica del job ───────────────────────────────────────────────────────────

def _tarea_ingesta():
    """Job periódico: obtiene datos de WeatherAPI para todos los distritos configurados."""
    global _ultimo_resumen

    fecha = datetime.now().strftime("%Y-%m-%d")
    distritos = persistencia.obtener_distritos_permitidos()
    guardados = omitidos = errores = 0

    logger.info(
        "Scheduler: ▶ Iniciando ingesta | %s | %d distritos",
        datetime.now().strftime("%H:%M:%S"), len(distritos),
    )

    for distrito in distritos:
        try:
            registro = Api.obtener_registro_climatico(distrito)
            if not registro:
                errores += 1
                err = Api._ultimo_error.copy()
                codigo = err.get("codigo")
                mensaje = err.get("mensaje", "Sin respuesta de la API")
                sugerencia = _obtener_sugerencia(codigo)
                _registrar_error_reciente(distrito, codigo, mensaje, sugerencia)
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
                    logger.debug("Scheduler: ya existe %s/%s, omitido.", distrito, fecha)
                else:
                    historico.append(registro)
                    persistencia.actualizar_base_de_datos(historico)
                    guardados += 1
                    logger.info(
                        "Scheduler: ✅ %s | %.1f°C | %dms",
                        distrito,
                        registro.get("temperatura", 0),
                        registro.get("latencia_ms", 0),
                    )
                    alertas_activas = registro.get("alertas", [])
                    for alerta in alertas_activas:
                        logger.warning(
                            "Scheduler: 🚨 ALERTA %s | %s",
                            distrito,
                            alerta,
                        )

        except Exception as e:
            errores += 1
            logger.error("Scheduler: ❌ Error en %s: %s", distrito, e)
            _registrar_error_reciente(distrito, None, str(e)[:100], "Revisar logs del sistema (app.log)")

    _ultimo_resumen = {
        "ultima_ejecucion": datetime.now(),
        "guardados": guardados,
        "omitidos": omitidos,
        "errores": errores,
        "total_distritos": len(distritos),
    }

    logger.info(
        "Scheduler: ■ Ingesta completada | Guardados: %d | Omitidos: %d | Errores: %d",
        guardados, omitidos, errores,
    )


# ─── API pública ──────────────────────────────────────────────────────────────

def iniciar():
    """Inicia el scheduler con horario fijo: 07:00h, 15:00h y 22:00h."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _tarea_ingesta,
        "cron",
        hour="7,15,22",
        id="ingesta_automatica",
        next_run_time=datetime.now(),
    )
    _scheduler.start()
    logger.info("Scheduler iniciado | Horario fijo: 07:00h | 15:00h | 22:00h")


def detener():
    """Detiene el scheduler y libera el hilo de fondo."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    logger.info("Scheduler detenido.")


def esta_activo():
    return _scheduler is not None and _scheduler.running


def obtener_proximo_disparo():
    if not (_scheduler and _scheduler.running):
        return None
    jobs = _scheduler.get_jobs()
    return jobs[0].next_run_time if jobs else None


def obtener_resumen():
    return _ultimo_resumen.copy()


def obtener_errores_recientes():
    return list(_errores_recientes)
