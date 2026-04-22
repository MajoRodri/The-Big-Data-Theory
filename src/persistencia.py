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

CONFIRMACION_REQUERIDA = "si"
logger = logging.getLogger(__name__)


def obtener_distritos_permitidos():    #Función para obtener la lista de distritos oficiales desde el archivo de configuración
    if not os.path.exists(CONFIGURACION_DE_ARCHIVO):
        print(f"Alerta: No se encontro {CONFIGURACION_DE_ARCHIVO}. Se desactivo la validacion territorial.")
        return []
    try:
        with open(CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
            return configuracion.get("distritos_oficiales", [])
    except Exception:
        return []


def obtener_umbrales_alerta():  #Función para obtener los umbrales de alerta desde el archivo de configuración
    if not os.path.exists(CONFIGURACION_DE_ARCHIVO):
        print(f"Alerta: No se encontro {CONFIGURACION_DE_ARCHIVO}. Sistema sin umbrales.")
        return {}

    try:
        with open(CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
            umbrales = configuracion.get("umbrales", {})
            return umbrales
    except Exception:
        print(f"Error al leer umbrales de {CONFIGURACION_DE_ARCHIVO}.")
        return {}


def leer_historico():    #Función para leer el histórico de datos desde el archivo JSON, con manejo de errores
    if not os.path.exists(ARCHIVO_JSON):
        print(f"Alerta: No se encontro {ARCHIVO_JSON}.")
        return []
    try:
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as archivo:
            historico = json.load(archivo)
            logger.info("Historico cargado correctamente desde %s", ARCHIVO_JSON)
            return historico
    except json.JSONDecodeError:
        print("Error: El archivo de datos esta corrupto.")
        logger.error("El archivo %s esta corrupto o tiene JSON invalido", ARCHIVO_JSON)
        return []
    except Exception as error:
        print(f"Error: No se pudo leer el archivo de datos: {error}")
        logger.error("Fallo al leer %s: %s", ARCHIVO_JSON, error)
        return []


def registrar_nuevo_dato(nuevo_registro):  #Función para registrar un nuevo dato, con validación de distrito, verificación de duplicados y confirmación del usuario
    distritos_oficiales = obtener_distritos_permitidos()
    distrito_ingresado = nuevo_registro["distrito"].strip()
    mapa_distritos = {distrito.lower(): distrito for distrito in distritos_oficiales}
    distrito_limpio = mapa_distritos.get(distrito_ingresado.lower(), distrito_ingresado)

    if distritos_oficiales and distrito_limpio not in distritos_oficiales:
        print(f"Error: '{distrito_limpio}' no es un distrito oficial de Madrid.")
        return False

    historico = leer_historico()
    for entrada in historico:
        if entrada["fecha"] == nuevo_registro["fecha"]:
            if entrada["distrito"].lower() == distrito_limpio.lower():
                print(f"ERROR: Ya existe un registro para {distrito_limpio} en la fecha {nuevo_registro['fecha']}")
                print("No se permiten duplicados en el historico.")
                return False

    print(f"\nDatos a registrar: {distrito_limpio} | {nuevo_registro['fecha']} | {nuevo_registro['temperatura']} C")

    while True:
        confirmar = input("Confirmas guardar estos datos en el sistema? (s/n): ").strip().lower()

        if confirmar == "s":
            nuevo_registro["distrito"] = distrito_limpio
            historico.append(nuevo_registro)

            try:
                with open(ARCHIVO_JSON, "w", encoding="utf-8") as archivo:
                    json.dump(historico, archivo, indent=4, ensure_ascii=False)
                print("Registro guardado exitosamente.")
                return True
            except Exception as error:
                print(f"Error critico al escribir en el disco: {error}")
                return False

        if confirmar == "n":
            print("Operacion cancelada. No se han guardado los datos.")
            return False

        print("No te he entendido. Escribe solo 's' o 'n'.\n")


def actualizar_base_de_datos(historico_modificado):  #Función para actualizar la base de datos con un histórico modificado, con manejo de errores
    try:
        with open(ARCHIVO_JSON, "w", encoding="utf-8") as archivo:
            json.dump(historico_modificado, archivo, indent=4, ensure_ascii=False)
        return True
    except Exception as error:
        print(f"Error al actualizar la base de datos: {error}")
        return False


def inicializar_archivo_datos():   #Función para inicializar el archivo de datos si no existe, con manejo de errores
    if not os.path.exists(ARCHIVO_JSON):
        print(f"Inicializando sistema: Creando nueva base de datos ({ARCHIVO_JSON})...")
        try:
            with open(ARCHIVO_JSON, "w", encoding="utf-8") as archivo:
                json.dump([], archivo)
            logger.info("Base de datos inicializada correctamente en %s", ARCHIVO_JSON)
        except Exception as error:
            print(f"Error critico al crear la base de datos: {error}")
            logger.error("Error critico al crear %s: %s", ARCHIVO_JSON, error)
