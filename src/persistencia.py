"""
Módulo de persistencia para The Big Data Theory.
Gestiona la lectura y escritura de datos climáticos en archivos JSON.
"""

import json
import logging
import os
from pathlib import Path

RUTA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_DATA = RUTA_PROYECTO / "data"

ARCHIVO_JSON = CARPETA_DATA / "datos_clima.json"
CONFIGURACION_DE_ARCHIVO = CARPETA_DATA / "config.json"
ARCHIVO_EMPLEADOS = CARPETA_DATA / "empleados.json"
ARCHIVO_USUARIOS = CARPETA_DATA / "usuarios.json"

logger = logging.getLogger(__name__)


def obtener_distritos_permitidos():
    """
    Obtiene la lista de distritos oficiales desde el archivo de configuración.

    Returns:
        list: Lista de nombres de distritos. Lista vacía si no existe el archivo.
    """
    if not os.path.exists(CONFIGURACION_DE_ARCHIVO):
        return []
    try:
        with open(CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
            return configuracion.get("distritos_oficiales", [])
    except Exception:
        return []


def obtener_umbrales_alerta():
    """
    Obtiene los umbrales de alerta climática desde el archivo de configuración.

    Returns:
        dict: Diccionario con los valores de umbral. Vacío si no existe el archivo.
    """
    if not os.path.exists(CONFIGURACION_DE_ARCHIVO):
        return {}

    try:
        with open(CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
            return configuracion.get("umbrales", {})
    except Exception:
        print(f"Error al leer umbrales de {CONFIGURACION_DE_ARCHIVO}.")
        return {}


def leer_historico():
    """
    Lee el histórico de datos climáticos desde el archivo JSON.

    Returns:
        list: Lista de registros climáticos. Lista vacía si el archivo no existe o está corrupto.
    """
    if not os.path.exists(ARCHIVO_JSON):
        return []
    try:
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as archivo:
            historico = json.load(archivo)
            return historico
    except json.JSONDecodeError:
        print("Error: El archivo de datos esta corrupto.")
        logger.error("El archivo %s esta corrupto o tiene JSON invalido", ARCHIVO_JSON)
        return []
    except Exception as error:
        print(f"Error: No se pudo leer el archivo de datos: {error}")
        logger.error("Fallo al leer %s: %s", ARCHIVO_JSON, error)
        return []


def registrar_nuevo_dato(nuevo_registro, forzar=False):
    """
    Registra un nuevo dato climático con validación de distrito, deduplicación y confirmación.

    Args:
        nuevo_registro (dict): Registro climático a guardar.
        forzar (bool): Si True, omite la confirmación interactiva (para operaciones masivas
                       donde el usuario ya confirmó antes del bucle).

    Returns:
        bool: True si el registro fue guardado, False si fue rechazado o cancelado.
    """
    distritos_oficiales = obtener_distritos_permitidos()
    distrito_ingresado = nuevo_registro["distrito"].strip()
    mapa_distritos = {distrito.lower(): distrito for distrito in distritos_oficiales}
    distrito_limpio = mapa_distritos.get(distrito_ingresado.lower(), distrito_ingresado)

    if distritos_oficiales and distrito_limpio not in distritos_oficiales:
        print(f"Error: '{distrito_limpio}' no es un distrito oficial de Madrid.")
        return False

    historico = leer_historico()
    fuente_nueva = nuevo_registro.get("fuente", "manual")
    registros_misma_clave = [
        e for e in historico
        if e.get("fecha") == nuevo_registro["fecha"]
        and e.get("distrito", "").lower() == distrito_limpio.lower()
    ]
    if len(registros_misma_clave) >= 2:
        print(f"ERROR: Ya existen 2 registros para {distrito_limpio} en {nuevo_registro['fecha']}.")
        print("No se permiten más de dos registros por distrito y fecha.")
        return False
    if any(e.get("fuente", "manual") == fuente_nueva for e in registros_misma_clave):
        print(f"ERROR: Ya existe un registro con fuente '{fuente_nueva}' para {distrito_limpio} en {nuevo_registro['fecha']}.")
        print("Solo se permite un registro manual y uno de API por distrito y fecha.")
        return False

    if not forzar:
        print(f"\nDatos a registrar: {distrito_limpio} | {nuevo_registro['fecha']} | {nuevo_registro['temperatura']} C")
        while True:
            confirmar = input("Confirmas guardar estos datos en el sistema? (s/n): ").strip().lower()
            if confirmar == "s":
                break
            if confirmar == "n":
                print("Operacion cancelada. No se han guardado los datos.")
                return False
            print("No te he entendido. Escribe solo 's' o 'n'.\n")

    nuevo_registro["distrito"] = distrito_limpio
    historico.append(nuevo_registro)

    try:
        with open(ARCHIVO_JSON, "w", encoding="utf-8") as archivo:
            json.dump(historico, archivo, indent=4, ensure_ascii=False)
        if not forzar:
            print("Registro guardado exitosamente.")
        return True
    except Exception as error:
        print(f"Error critico al escribir en el disco: {error}")
        return False


def actualizar_base_de_datos(historico_modificado):
    """
    Sobreescribe el archivo JSON con el histórico modificado en memoria.

    Args:
        historico_modificado (list): Lista completa de registros climáticos actualizada.

    Returns:
        bool: True si la escritura fue exitosa.
    """
    try:
        with open(ARCHIVO_JSON, "w", encoding="utf-8") as archivo:
            json.dump(historico_modificado, archivo, indent=4, ensure_ascii=False)
        return True
    except Exception as error:
        print(f"Error al actualizar la base de datos: {error}")
        return False


def obtener_query_api(distrito):
    """Devuelve el alias de consulta para WeatherAPI si está configurado, o el nombre del distrito."""
    try:
        with open(CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
            return config.get("alias_api", {}).get(distrito, distrito)
    except Exception:
        return distrito


def inicializar_archivo_datos():
    """
    Crea el archivo de datos vacío si no existe, para el primer arranque del sistema.
    """
    if not os.path.exists(ARCHIVO_JSON):
        print("Inicializando sistema: Creando nueva base de datos...")
        try:
            with open(ARCHIVO_JSON, "w", encoding="utf-8") as archivo:
                json.dump([], archivo)
            logger.info("Base de datos inicializada correctamente en %s", ARCHIVO_JSON)
        except Exception as error:
            print(f"Error critico al crear la base de datos: {error}")
            logger.error("Error critico al crear %s: %s", ARCHIVO_JSON, error)


def actualizar_umbrales_alerta(nuevos_umbrales):
    """
    Actualiza los umbrales de alerta en config.json manteniendo compatibilidad con ambos esquemas
    de claves: temperatura_max/temperatura_min (nuevo) y temp_max_roja/temp_min_critica (antiguo).

    Args:
        nuevos_umbrales (dict): Diccionario con los nuevos valores de umbral.

    Returns:
        bool: True si la actualización fue exitosa.
    """
    try:
        if os.path.exists(CONFIGURACION_DE_ARCHIVO):
            with open(CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
                configuracion = json.load(archivo)
        else:
            configuracion = {}

        umbrales_base = configuracion.get("umbrales", {}).copy()
        umbrales_base.update(nuevos_umbrales)

        # Mantiene sincronizados los nombres del esquema antiguo cuando se actualizan los del nuevo
        if "temperatura_max" in nuevos_umbrales:
            umbrales_base["temp_max_roja"] = nuevos_umbrales["temperatura_max"]
            umbrales_base["temp_max_naranja"] = round(nuevos_umbrales["temperatura_max"] - 5.0, 1)
        if "temperatura_min" in nuevos_umbrales:
            umbrales_base["temp_min_critica"] = nuevos_umbrales["temperatura_min"]
            umbrales_base["temp_min_alerta"] = round(nuevos_umbrales["temperatura_min"] + 5.0, 1)
        if "lluvia_max" in nuevos_umbrales:
            umbrales_base["lluvia_roja"] = nuevos_umbrales["lluvia_max"]
            umbrales_base["lluvia_naranja"] = round(nuevos_umbrales["lluvia_max"] * 0.4, 1)

        configuracion["umbrales"] = umbrales_base

        with open(CONFIGURACION_DE_ARCHIVO, "w", encoding="utf-8") as archivo:
            json.dump(configuracion, archivo, indent=4, ensure_ascii=False)

        logger.info("Umbrales de alerta actualizados correctamente")
        return True

    except Exception as error:
        print(f"Error al actualizar umbrales de alerta: {error}")
        logger.error("Error al actualizar umbrales: %s", error)
        return False
