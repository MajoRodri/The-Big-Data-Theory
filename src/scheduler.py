"""
Módulo de ingesta automática programada para The Big Data Theory.
Ejecuta capturas a tres horarios configurables por el usuario para todos los distritos
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
_horas_configuradas: list = [(7, 0), (15, 0), (22, 0)]  # lista de (hora, minuto)

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

def _tarea_ingesta(h_slot=None, m_slot=None):
    """Obtiene datos de WeatherAPI para todos los distritos y encola el resultado."""
    global _ultimo_resumen

    hora_inicio = datetime.now()
    fecha = hora_inicio.strftime("%Y-%m-%d")
    if h_slot is not None and m_slot is not None:
        hora = f"{h_slot:02d}:{m_slot:02d}"
    else:
        hora = hora_inicio.strftime("%H:%M")
    distritos = persistencia.obtener_distritos_permitidos()

    guardados = omitidos = errores = 0
    detalles: list = []
    errores_lista: list = []

    logger.info(
        "▶ Iniciando ingesta | %s | %d distritos",
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
                logger.warning("Error ❌ %s | %s: %s", distrito, codigo, mensaje)
                continue

            registro["hora"] = hora

            with _lock:
                historico = persistencia.leer_historico()
                ya_existe = any(
                    r.get("fecha") == fecha
                    and r.get("distrito", "").lower() == distrito.lower()
                    and r.get("fuente") == "api"
                    and r.get("hora") == hora
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
                        "✅ %s | %.1f°C", distrito, registro.get("temperatura", 0)
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
            logger.error("❌ Error en %s: %s", distrito, exc)

    _ultimo_resumen = {
        "ultima_ejecucion": hora_inicio,
        "guardados": guardados,
        "omitidos": omitidos,
        "errores": errores,
        "total_distritos": len(distritos),
    }

    logger.info(
        " ■ Completada | Guardados: %d | Omitidos: %d | Errores: %d",
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
    """Bucle del hilo de fondo: dispara ingesta en los horarios configurados."""
    ultimos_disparos: dict = {}  # (h, m) → fecha en que disparó por última vez
    print("\nHilo iniciado.", flush=True)

    while _activo:
        try:
            ahora = datetime.now()
            hoy = ahora.date()

            for h, m in list(_horas_configuradas):
                if ultimos_disparos.get((h, m)) == hoy:
                    continue  # ya disparó hoy en este slot
                target = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
                diff = (ahora - target).total_seconds()
                if 0 <= diff < 300:  # hasta 5 min después del horario programado
                    print(f"\n▶ Disparando ingesta {h:02d}:{m:02d}...", flush=True)
                    ultimos_disparos[(h, m)] = hoy
                    _tarea_ingesta(h, m)
                    print(f"✅ Ingesta {h:02d}:{m:02d} completada.", flush=True)

        except Exception as exc:
            logger.error("❌ Error en bucle — %s", exc)
            print(f"\n❌ Error en bucle: {exc}", flush=True)

        time.sleep(10)

    print("\nHilo detenido.", flush=True)


# ─── API pública ──────────────────────────────────────────────────────────────

def iniciar():
    """Inicia el scheduler con los horarios actualmente configurados."""
    global _hilo, _activo

    if _activo:
        return

    _activo = True
    _hilo = threading.Thread(target=_hilo_bucle, daemon=True, name="SchedulerTBDT")
    _hilo.start()
    horas_str = " | ".join(f"{h:02d}:{m:02d}h" for h, m in _horas_configuradas)
    logger.info("Iniciando | Horario: %s", horas_str)


def detener():
    """Detiene el scheduler."""
    global _activo, _hilo
    _activo = False
    _hilo = None
    logger.info("Ingesta automática detenida.")


def esta_activo() -> bool:
    return _activo and _hilo is not None and _hilo.is_alive()


def obtener_proximo_disparo() -> datetime:
    if not _activo:
        return None
    ahora = datetime.now()
    for h, m in sorted(_horas_configuradas):
        target = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
        if target > ahora:
            return target
    manana = ahora.date() + timedelta(days=1)
    h, m = sorted(_horas_configuradas)[0]
    return datetime(manana.year, manana.month, manana.day, h, m, 0)


def configurar_horas(horas: list):
    """Establece los horarios de disparo. horas: lista de tuplas (hora, minuto)."""
    global _horas_configuradas
    _horas_configuradas = sorted(horas)


def obtener_horas_configuradas() -> list:
    """Devuelve la lista de horarios configurados como tuplas (hora, minuto)."""
    return list(_horas_configuradas)


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
