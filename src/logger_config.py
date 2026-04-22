import logging
from pathlib import Path


RUTA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_LOGS = RUTA_PROYECTO / "logs"
ARCHIVO_LOG = CARPETA_LOGS / "app.log"
FORMATO_LOG = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(level=logging.INFO):
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)

    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(level)

    if logger_raiz.handlers:
        logger_raiz.handlers.clear()

    formatter = logging.Formatter(FORMATO_LOG)

    file_handler = logging.FileHandler(ARCHIVO_LOG, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger_raiz.addHandler(file_handler)
    logger_raiz.addHandler(console_handler)

    return logger_raiz
