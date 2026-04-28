"""
CONFIGURACIÓN DE LOGGING - PyClima Resiliente
Proyecto II: Ingesta de datos climáticos

Este módulo centraliza toda la configuración de logging del proyecto,
incluyendo:
- Logs generales de la aplicación (app.log)
- Logs específicos de peticiones HTTP (api_requests.log)
- Configuración de niveles y formatos
"""

import logging
from pathlib import Path
import os
from dotenv import load_dotenv

# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE RUTAS
# ═════════════════════════════════════════════════════════════════════════════

load_dotenv()

RUTA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_LOGS = RUTA_PROYECTO / "logs"
ARCHIVO_LOG = CARPETA_LOGS / "app.log"
ARCHIVO_LOG_API = CARPETA_LOGS / "api_requests.log"

# Formatos de logging
FORMATO_LOG = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
FORMATO_LOG_API = "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"

# Nivel de logging por defecto
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def setup_logging(level=None):
    """
    Configura el sistema de logging para toda la aplicación.
    
    Parámetros:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Por defecto usa la variable LOG_LEVEL de .env
    
    Retorna:
        logger_raiz: Logger raíz configurado
    
    Ejemplo:
        setup_logging()  # Usar .env o INFO por defecto
        setup_logging(logging.DEBUG)  # Usar DEBUG explícitamente
    """
    
    # Usar el nivel pasado o el de .env o INFO por defecto
    if level is None:
        level = getattr(logging, LOG_LEVEL, logging.INFO)
    
    # Crear carpeta de logs si no existe
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
    
    # Obtener logger raíz
    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(level)
    
    # Limpiar handlers previos para evitar duplicados
    if logger_raiz.handlers:
        logger_raiz.handlers.clear()
    
    # Formatter general
    formatter_general = logging.Formatter(FORMATO_LOG)
    
    # ─────────────────────────────────────────────────────────────────────────
    # HANDLER 1: Archivo de logs general (app.log)
    # ─────────────────────────────────────────────────────────────────────────
    
    file_handler = logging.FileHandler(ARCHIVO_LOG, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter_general)
    logger_raiz.addHandler(file_handler)
    
    # ─────────────────────────────────────────────────────────────────────────
    # HANDLER 2: Consola (stdout)
    # ─────────────────────────────────────────────────────────────────────────
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter_general)
    logger_raiz.addHandler(console_handler)
    
    # ─────────────────────────────────────────────────────────────────────────
    # HANDLER 3: Archivo específico para logs de HTTP (api_requests.log)
    # ─────────────────────────────────────────────────────────────────────────
    
    logger_api = logging.getLogger("Api")
    logger_api.setLevel(level)
    logger_api.propagate = False  # No propagar a logger raíz
    
    formatter_api = logging.Formatter(FORMATO_LOG_API)
    
    file_handler_api = logging.FileHandler(ARCHIVO_LOG_API, encoding="utf-8")
    file_handler_api.setLevel(level)
    file_handler_api.setFormatter(formatter_api)
    logger_api.addHandler(file_handler_api)
    
    # También mostrar logs de API en consola
    console_handler_api = logging.StreamHandler()
    console_handler_api.setLevel(logging.WARNING)
    console_handler_api.setFormatter(formatter_api)
    logger_api.addHandler(console_handler_api)
    
    return logger_raiz

