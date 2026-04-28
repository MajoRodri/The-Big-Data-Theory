"""
Módulo de ingesta automática programada para The Big Data Theory.
Ejecuta capturas en horarios específicos (7:00, 15:00, 22:00) vía WeatherAPI
usando APScheduler en un hilo de fondo (daemon thread).
"""

import logging
import os
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import Api
import persistencia

logger = logging.getLogger(__name__)

# ─── Estado interno ───────────────────────────────────────────────────────────

_scheduler = None
_horarios_ingesta = list(map(int, os.getenv("SCHEDULER_HORARIOS_INGESTA", "7,15,22").split(",")))
_intervalo_minutos = int(os.getenv("SCHEDULER_FRECUENCIA_MINUTOS", "30"))
_hora_inicio = int(os.getenv("SCHEDULER_HORAS_ACTIVAS_DESDE", "6"))
_hora_fin = int(os.getenv("SCHEDULER_HORAS_ACTIVAS_HASTA", "23"))

# Protege escrituras concurrentes al JSON cuando el scheduler corre en paralelo
_lock = threading.Lock()

_ultimo_resumen = {
    "ultima_ejecucion": None,
    "guardados": 0,
    "omitidos": 0,
    "errores": 0,
    "total_distritos": 0,
}


# ─── Lógica del job ───────────────────────────────────────────────────────────

def _dentro_de_horas_activas():
    """
    Comprueba si la hora actual está dentro del rango horario configurado para ingesta.

    Returns:
        bool: True si la hora actual está entre _hora_inicio y _hora_fin.
    """
    hora = datetime.now().hour
    return _hora_inicio <= hora < _hora_fin


def _tarea_ingesta():
    """Job periódico: obtiene datos de WeatherAPI para todos los distritos configurados."""
    global _ultimo_resumen

    if not _dentro_de_horas_activas():
        logger.info(
            "Scheduler: Fuera de horario activo (%dh–%dh). Ciclo omitido.",
            _hora_inicio, _hora_fin,
        )
        return

    fecha = datetime.now().strftime("%Y-%m-%d")
    distritos = persistencia.obtener_distritos_permitidos()
    guardados = omitidos = errores = 0

    logger.info(
        "Scheduler: ▶ Iniciando ingesta | %s | %d distritos",
        datetime.now().strftime("%H:%M:%S"), len(distritos),
    )

    for distrito in distritos:
        try:
            registro = Api.obtener_registro_climatico(
                distrito,
                usuario_actual={"num_empleado": "SYSTEM", "nombre": "Sistema Automático"}
            )
            if not registro:
                errores += 1
                logger.warning("Scheduler: ❌ No se pudo obtener datos para %s", distrito)
                continue

            # Agregar metadata de quién solicitó la ingesta
            registro["solicitado_por"] = "Sistema Automático"

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

        except Exception as e:
            errores += 1
            logger.error("Scheduler: ❌ Error en %s: %s", distrito, e)

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


# ─── API pública ─────────────────────────────────────────────────────────────

def iniciar(horarios=None):
    """
    Inicia el scheduler con trabajos en horarios específicos (7:00, 15:00, 22:00).
    
    Args:
        horarios (list, optional): Lista de horas para programar las ingestas.
                                   Por defecto usa SCHEDULER_HORARIOS_INGESTA del .env
    """
    global _scheduler, _horarios_ingesta

    if horarios:
        _horarios_ingesta = horarios
    
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)

    _scheduler = BackgroundScheduler(daemon=True)
    
    # Agregar un job para cada hora configurada
    for hora in _horarios_ingesta:
        job_id = f"ingesta_automatica_{hora:02d}"
        _scheduler.add_job(
            _tarea_ingesta,
            "cron",
            hour=hora,
            minute=0,
            second=0,
            id=job_id,
            replace_existing=True
        )
        logger.info("Scheduler: Job programado a las %02d:00", hora)
    
    _scheduler.start()
    logger.info(
        "Scheduler iniciado | Horarios: %s | Horario activo: %dh–%dh",
        ",".join(f"{h:02d}:00" for h in sorted(_horarios_ingesta)),
        _hora_inicio, _hora_fin,
    )


def detener():
    """Detiene el scheduler y libera el hilo de fondo."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    logger.info("Scheduler detenido.")


def configurar_intervalo(minutos):
    """
    Actualiza el intervalo de ingesta sin reiniciar el scheduler (se aplica en el próximo inicio).

    Args:
        minutos (int): Nuevo intervalo en minutos (se clampea entre 5 y 120).
    """
    global _intervalo_minutos
    _intervalo_minutos = max(5, min(120, int(minutos)))


def esta_activo():
    """
    Indica si el scheduler está actualmente en ejecución.

    Returns:
        bool: True si el scheduler está activo.
    """
    return _scheduler is not None and _scheduler.running


def obtener_intervalo():
    """
    Devuelve los horarios configurados para la ingesta automática.

    Returns:
        list: Lista de horas (números enteros) programadas.
    """
    return sorted(_horarios_ingesta)


def obtener_proximo_disparo():
    """
    Devuelve la fecha y hora de la próxima ejecución programada del job.

    Returns:
        datetime or None: Próxima ejecución, o None si el scheduler no está activo.
    """
    if not (_scheduler and _scheduler.running):
        return None
    jobs = _scheduler.get_jobs()
    return jobs[0].next_run_time if jobs else None


def obtener_resumen():
    """
    Devuelve una copia del resumen del último ciclo de ingesta ejecutado.

    Returns:
        dict: Diccionario con ultima_ejecucion, guardados, omitidos, errores y total_distritos.
    """
    return _ultimo_resumen.copy()
