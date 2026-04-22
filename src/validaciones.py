"""
MÓDULO DE VALIDACIONES (DEV 2 - David)
--------------------------------------
Este módulo contiene todas las reglas de calidad de datos del Ayuntamiento.
Proporciona funciones seguras que no rompen el programa si el usuario se equivoca.

Instrucciones para el equipo:
- DEV 1: Importa estas funciones en tu menu.py (ej: from validaciones import validar_temperatura)
- DEV 3: Usa validar_duplicado antes de guardar en tu archivo JSON.
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTACIONES
# Antes de que el programa empiece a funcionar, necesita "traer herramientas"
# de otros sitios. Esto es como abrir el cajón de herramientas antes de trabajar.
# ─────────────────────────────────────────────────────────────────────────────

# 'datetime' es una herramienta de Python que sabe trabajar con fechas y horas.
# La necesitamos para poder comparar la fecha que escribe el usuario con la fecha de hoy.
from datetime import datetime

# 'json' es una herramienta para leer y escribir archivos .json (que son como
# hojas de cálculo en formato texto). La usamos para leer el config.json y los
# archivos de empleados y usuarios.
import json

# 'difflib' es una herramienta de Python especializada en comparar textos.
# La usamos para la "magia de corrección tipográfica": si el usuario escribe
# "Retiro" con una 'o' de más, difflib es capaz de sugerir "Retiro".
import difflib
import persistencia


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_temperatura()
# ─────────────────────────────────────────────────────────────────────────────
def validar_temperatura():
    """
    Solicita y valida la temperatura.
    Rango permitido: -20 a 50 grados Celsius.
    
    DEV 1: Llama a esta función sin parámetros.
    Retorna: Un número float (ej. 25.5).
    """
    # 'while True' es un bucle infinito. Imagínalo como una puerta giratoria:
    # el usuario está atrapado dentro dando vueltas hasta que introduzca un dato
    # correcto. Solo saldrá cuando el programa ejecute 'return'.
    while True:
        # 'try' es como un escudo protector. Le dice a Python:
        # "Intenta ejecutar esto, pero si algo sale mal, no te caigas".
        try:
            # input() detiene el programa y espera a que el usuario escriba algo.
            # .strip() elimina los espacios en blanco accidentales al principio
            # y al final de lo que escribió (como si recortaras los bordes de un papel).
            entrada = input("Introduce la temperatura (-20 a 50 °C) [o 'c' para cancelar]: ").strip()
            
            # .lower() convierte lo que escribió el usuario a minúsculas.
            # Así, si escribe 'C', 'c' o 'C ' (con espacio), todo se trata igual.
            # Si escribió 'c' para cancelar, lanzamos KeyboardInterrupt para salir.
            if entrada.lower() == 'c': raise KeyboardInterrupt # Simula la cancelación
            
            # float() intenta convertir el texto que escribió el usuario en un número
            # decimal. Si el usuario escribió "25.5", esto lo convierte en el número 25.5.
            # Si escribió "hola", Python no puede convertirlo y lanza un ValueError,
            # que el 'except' de abajo capturará como un error.
            temp = float(entrada)
            
            # Aquí comprobamos si el número está dentro del rango permitido.
            # Si la temperatura es lógica (entre -20 y 50 grados), la devolvemos.
            if -20 <= temp <= 50:
                # 'return' es la salida de la función Y del bucle infinito.
                # Es como abrir la puerta giratoria y dejar salir al usuario con el dato válido.
                return temp  
            else:
                # Si el número no está en el rango, informamos del error.
                # El bucle 'while True' hará que la pregunta se repita automáticamente.
                print(f"❌ Error: {temp}°C está fuera del rango permitido (-20 a 50).")
        
        # 'except ValueError' es la red de seguridad del 'try'.
        # Se activa SOLO cuando float() no pudo convertir el texto a número.
        # Es como decir: "Si el usuario escribió letras en lugar de números, haz esto".
        except ValueError:
            print("❌ Error: Por favor, introduce un número válido (ejemplo: 25.5).")
        
        # Este print se ejecuta siempre al final de cada vuelta fallida del bucle,
        # recordando al usuario que debe intentarlo de nuevo.
        print("🔄 Inténtalo de nuevo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_humedad()
# ─────────────────────────────────────────────────────────────────────────────
def validar_humedad():
    """
    Solicita y valida la humedad ambiental.
    Rango permitido: 0 a 100%.
    
    DEV 1: Llama a esta función sin parámetros.
    Retorna: Un número float (ej. 45.0).
    """
    # Mismo patrón de bucle infinito que en validar_temperatura().
    # El usuario no puede salir hasta que introduzca un dato correcto.
    while True:
        try:
            entrada = input("Introduce la humedad (0 a 100%) [o 'c' para cancelar]: ").strip()
            # Si escribe 'c', cancelamos igual que en la función anterior.
            if entrada.lower() == 'c': raise KeyboardInterrupt
            
            # Convertimos el texto a número decimal.
            humedad = float(entrada)
            
            # La humedad solo puede estar entre 0% y 100%. Si está en ese rango, la devolvemos.
            if 0 <= humedad <= 100:
                return humedad  
            else:
                print(f"❌ Error: {humedad}% no es una humedad lógica (debe ser de 0 a 100).")
        
        except ValueError:
            print("❌ Error: Introduce un valor numérico para la humedad.")
            
        print("🔄 Inténtalo de nuevo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_viento()
# ─────────────────────────────────────────────────────────────────────────────
def validar_viento():
    """
    Solicita y valida la velocidad del viento.
    Rango permitido: 0 a 150 km/h.
    
    DEV 1: Llama a esta función sin parámetros.
    Retorna: Un número float (ej. 12.5).
    """
    # Mismo patrón de bucle + escudo de errores que las funciones anteriores.
    while True:
        try:
            entrada = input("Introduce la velocidad del viento (0 a 150 km/h) [o 'c' para cancelar]: ").strip()
            if entrada.lower() == 'c': raise KeyboardInterrupt
            
            viento = float(entrada)
            
            # El viento no puede ser negativo y ponemos un límite lógico de 150 km/h.
            if 0 <= viento <= 150:
                return viento  
            else:
                print(f"❌ Error: {viento} km/h está fuera del rango lógico (0 a 150).")
        
        except ValueError:
            print("❌ Error: La velocidad del viento debe ser un valor numérico.")
            
        print("🔄 Inténtalo de nuevo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_fecha()
# Esta función tiene una responsabilidad extra: no solo valida el formato,
# sino que también impide registrar fechas que aún no han ocurrido.
# ─────────────────────────────────────────────────────────────────────────────
def validar_fecha():
    """
    Solicita y valida una fecha.
    Formato estricto: AAAA-MM-DD.
    Solo permite fechas actuales o pasadas (no futuras).
    """
    while True:
        entrada = input("Introduce la fecha (formato AAAA-MM-DD, ej: 2026-04-06) [o 'c' para cancelar]: ").strip()
        # Si el usuario escribe 'c', cancelamos la operación.
        if entrada.lower() == 'c': raise KeyboardInterrupt

        # Comprobamos que el usuario no haya pulsado Enter sin escribir nada.
        if not entrada:
            print("❌ Error: La fecha no puede estar vacía.")
            # 'continue' salta directamente al inicio del bucle 'while',
            # ignorando todo el código que hay debajo. Es como decir "vuelve a empezar".
            continue

        try:
            # datetime.strptime() es como un lector de fechas muy estricto.
            # Le decimos: "Lee este texto (entrada) y espera que tenga este formato (%Y-%m-%d)".
            # Si el texto no tiene ese formato exacto, lanza un ValueError.
            # Por ejemplo, "32-13-2026" fallaría porque el día 32 no existe.
            fecha_ingresada = datetime.strptime(entrada, "%Y-%m-%d")
            
            # datetime.now() obtiene la fecha y hora exactas de este momento en el ordenador.
            # Es nuestra referencia para saber qué es "hoy".
            fecha_actual = datetime.now()

            # Comparamos las dos fechas. Si la que escribió el usuario es posterior a hoy,
            # no la aceptamos. No podemos registrar datos climáticos del futuro.
            if fecha_ingresada > fecha_actual:
                print(f"❌ Error: No se permiten fechas futuras. La fecha ingresada ({entrada}) es posterior a hoy ({fecha_actual.strftime('%Y-%m-%d')}).")
                print("🔄 Inténtalo de nuevo.\n")
                # 'continue' vuelve al inicio del bucle para pedir la fecha de nuevo.
                continue

            # Si llegamos aquí, la fecha tiene formato correcto Y no es futura.
            # La devolvemos como texto (string) en formato AAAA-MM-DD.
            return entrada

        except ValueError:
            # Si strptime() no pudo interpretar la fecha, llegamos aquí.
            # Puede ser porque el formato es incorrecto o la fecha no existe (ej: 30 de febrero).
            print("❌ Error: Formato incorrecto o fecha inexistente. Usa AAAA-MM-DD.")

        print("🔄 Inténtalo de nuevo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_zona()
# Esta es la función más compleja del módulo. No solo valida, sino que también
# sugiere correcciones si el usuario se equivoca al escribir.
# ─────────────────────────────────────────────────────────────────────────────
def validar_zona():
    """
    Solicita el nombre de la zona y lo coteja con config.json.
    - No distingue mayúsculas/minúsculas.
    - Devuelve el nombre exacto oficial (ej. si escribes 'retiro', devuelve 'Retiro').
    - Sugiere el nombre si hay un error tipográfico.
    """
    # PASO 1: Cargar el archivo de distritos oficiales.
    # Antes de poder validar nada, necesitamos saber qué distritos son válidos.
    # Esa información está guardada en el archivo config.json.
    try:
        # Abrimos config.json en modo lectura ('r') con codificación UTF-8
        # (para que lea correctamente tildes y caracteres especiales como la ñ).
        with open(persistencia.CONFIGURACION_DE_ARCHIVO, 'r', encoding='utf-8') as archivo:
            # json.load() lee el contenido del archivo y lo convierte en un
            # diccionario de Python (como una tabla de datos en memoria).
            config = json.load(archivo)
            # .get() busca la clave "distritos_oficiales" dentro del diccionario.
            # Si no la encuentra, devuelve una lista vacía [] en lugar de dar error.
            distritos_oficiales = config.get("distritos_oficiales", [])
    except FileNotFoundError:
        # Si el archivo config.json no existe en la carpeta, capturamos el error
        # y avisamos al usuario en lugar de que el programa se rompa.
        print("❌ Error crítico: No se encuentra el archivo 'config.json'.")
        print("⚠️ Avisa al equipo técnico para restaurar el archivo.")
        # Devolvemos None (que es como decir "nada" o "vacío") para indicar el fallo.
        return None 
    except json.JSONDecodeError:
        # Si el archivo existe pero su contenido está mal formateado (corrupto),
        # json.load() lanza este error y lo capturamos aquí.
        print("❌ Error crítico: El archivo 'config.json' está corrupto.")
        return None

    # PASO 2: Crear el "diccionario traductor".
    # Problema: El usuario puede escribir "retiro", "Retiro" o "RETIRO".
    # Solución: Creamos un diccionario donde las claves son los nombres en minúsculas
    # y los valores son los nombres oficiales con sus mayúsculas correctas.
    # Ejemplo: {"retiro": "Retiro", "centro": "Centro", "barajas": "Barajas", ...}
    # Esto nos permite buscar en minúsculas pero devolver siempre el nombre correcto.
    mapa_distritos = {distrito.lower(): distrito for distrito in distritos_oficiales}
    
    # Guardamos solo las claves (los nombres en minúsculas) en una lista.
    # La necesitaremos para el corrector tipográfico de difflib.
    lista_minusculas = list(mapa_distritos.keys())

    # PASO 3: Bucle de validación con corrector tipográfico.
    while True:
        zona_input = input("Introduce la zona (ej: Retiro, Centro) [o 'c' para cancelar]: ").strip()
        if zona_input.lower() == 'c': raise KeyboardInterrupt
        
        if not zona_input:
            print("❌ Error: La zona no puede estar vacía.")
            print("🔄 Inténtalo de nuevo.\n")
            continue

        # Convertimos lo que escribió el usuario a minúsculas para buscar en el mapa.
        zona_lower = zona_input.lower()

        # COMPROBACIÓN EXACTA: ¿Lo que escribió está en nuestro diccionario traductor?
        if zona_lower in mapa_distritos:
            # Si la encontramos, devolvemos el nombre oficial correcto (con mayúsculas).
            return mapa_distritos[zona_lower]

        # CORRECTOR TIPOGRÁFICO: Si no fue exacto, buscamos algo parecido.
        # difflib.get_close_matches() compara la palabra del usuario con toda
        # nuestra lista de distritos y devuelve las más parecidas.
        # n=1 significa "dame solo la mejor sugerencia".
        # cutoff=0.6 significa "solo sugiere si hay al menos un 60% de similitud".
        sugerencias = difflib.get_close_matches(zona_lower, lista_minusculas, n=1, cutoff=0.6)

        if sugerencias:
            # Si difflib encontró algo parecido, recuperamos el nombre oficial de esa sugerencia.
            zona_sugerida = mapa_distritos[sugerencias[0]]
            # Preguntamos al usuario si eso era lo que quería escribir.
            confirmacion = input(f"🤔 No encuentro '{zona_input}'. ¿Querías decir '{zona_sugerida}'? (s/n): ").strip().lower()
            
            if confirmacion == 's':
                # Si confirma, devolvemos la sugerencia como si fuera la entrada original.
                return zona_sugerida
            else:
                print("❌ Entendido. Zona descartada.")
        else:
            # Si ni siquiera hay nada parecido, informamos claramente.
            print(f"❌ Error: '{zona_input}' no coincide con ningún distrito oficial de Madrid.")
            
        print("🔄 Inténtalo de nuevo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_acceso()
# Actúa como el portero de la discoteca para el REGISTRO de nuevos usuarios.
# Solo deja pasar a quien tenga su número en la lista de empleados.json.
# ─────────────────────────────────────────────────────────────────────────────
def validar_acceso():
    """
    Valida que el empleado exista en empleados.json.
    Devuelve el número de empleado si es válido, None si no.
    PARA REGISTRO DE NUEVO USUARIO.
    """
    # Solo se permiten 3 intentos para no facilitar que alguien adivine por fuerza bruta.
    max_intentos = 3
    # Contador que lleva la cuenta de cuántos intentos ha gastado el usuario.
    intento = 0

    # PASO 1: Cargar la lista de empleados autorizados desde el archivo.
    try:
        with open(persistencia.ARCHIVO_EMPLEADOS, "r", encoding='utf-8') as f:
            lista_autorizados = json.load(f)
    except FileNotFoundError:
        print("❌ Error crítico: El archivo 'empleados.json' no existe.")
        return None
    except json.JSONDecodeError:
        print("❌ Error crítico: El archivo 'empleados.json' está corrupto.")
        return None

    # PASO 2: Bucle de intentos (máximo 3).
    # A diferencia de 'while True', este bucle tiene condición de parada:
    # se detiene cuando 'intento' llega a ser igual a 'max_intentos' (3).
    while intento < max_intentos:
        try:
            numero_ingresado = input(f"Introduce tu número de empleado [{intento + 1}/{max_intentos}] [o 'c' para cancelar]: ").strip()

            if numero_ingresado.lower() == 'c':
                raise KeyboardInterrupt

            if not numero_ingresado:
                print("❌ Error: El número de empleado no puede estar vacío.")
                # Sumamos un intento fallido aunque el campo esté vacío.
                intento += 1
                continue

            # Comprobamos si el número que escribió está en la lista de autorizados.
            # El operador 'in' busca el elemento dentro de la lista: es como preguntar
            # "¿está este nombre en la lista de invitados?".
            if numero_ingresado in lista_autorizados:
                print(f"✅ Número de empleado {numero_ingresado} validado correctamente.")
                # Si está, devolvemos el número y salimos de la función.
                return numero_ingresado
            else:
                # Si no está, sumamos un intento y calculamos cuántos quedan.
                intento += 1
                intentos_restantes = max_intentos - intento
                print(f"❌ Número de empleado NO reconocido.")
                if intentos_restantes > 0:
                    print(f"🔄 Intentos restantes: {intentos_restantes}\n")
                else:
                    print(f"❌ Has agotado los {max_intentos} intentos.\n")
                    
        except KeyboardInterrupt:
            print("❌ Validación cancelada por el usuario.")
            return None
    
    # Si el bucle termina porque se agotaron los intentos, devolvemos None.
    return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_duplicado()
# Actúa como un revisor que comprueba si ya existe un registro igual
# antes de guardarlo. Evita que haya datos repetidos en la base de datos.
# ─────────────────────────────────────────────────────────────────────────────
def validar_duplicado(nueva_fecha, nueva_zona, historial):
    """
    Comprueba si ya existe un registro para la misma fecha y zona.
    
    DEV 3 / DEV 1: Pasad a esta función la fecha, la zona y el JSON cargado.
    Retorna: True (si hay error de duplicado) o False (si todo está correcto).
    """
    # Recorremos todos los registros existentes en la base de datos (el historial).
    # 'for registro in historial' es como leer las fichas de una carpeta una por una.
    for registro in historial:
        # Para cada ficha, comprobamos SI la fecha Y la zona coinciden con lo nuevo.
        # .lower() en la zona es para que la comparación ignore mayúsculas/minúsculas.
        if registro['fecha'] == nueva_fecha and registro['distrito'].lower() == nueva_zona.lower():
            print(f"❌ Error: Ya existen datos para '{nueva_zona}' en la fecha {nueva_fecha}.")
            print("⚠️ No se permiten registros duplicados para la misma zona el mismo día.")
            # Devolvemos True para indicar: "Sí, hay duplicado, hay un problema".
            return True 
            
    # Si el bucle termina sin haber encontrado ninguna coincidencia, devolvemos False:
    # "No hay duplicado, todo está bien, puedes guardar".
    return False


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_usuario_sesion()
# Similar a validar_acceso(), pero este portero trabaja para el LOGIN.
# Busca al usuario en usuarios.json (los ya registrados), no en empleados.json.
# ─────────────────────────────────────────────────────────────────────────────
def validar_usuario_sesion():
    """
    Valida que el usuario exista en usuarios.json.
    Devuelve el número de empleado si es válido, None si no.
    PARA INICIAR SESIÓN SOLAMENTE.
    """
    max_intentos = 3
    intento = 0

    try:
        with open(persistencia.ARCHIVO_USUARIOS, "r", encoding='utf-8') as f:
            # Cargamos la lista de usuarios registrados (cada uno es un diccionario
            # con nombre, apellidos, num_empleado y password).
            usuarios_registrados = json.load(f)
            # Extraemos solo los números de empleado de cada usuario en una lista.
            # Esto es más eficiente para buscar: comparamos números contra números,
            # no diccionarios enteros contra números.
            numeros_usuarios = [u.get("num_empleado") for u in usuarios_registrados]
    except FileNotFoundError:
        print("❌ Error crítico: El archivo 'usuarios.json' no existe.")
        return None
    except json.JSONDecodeError:
        print("❌ Error crítico: El archivo 'usuarios.json' está corrupto.")
        return None

    # Bucle de intentos con máximo 3, igual que en validar_acceso().
    while intento < max_intentos:
        try:
            numero_ingresado = input(f"Introduce tu número de empleado [{intento + 1}/{max_intentos}] [o 'c' para cancelar]: ").strip()

            if numero_ingresado.lower() == 'c':
                raise KeyboardInterrupt

            if not numero_ingresado:
                print("❌ Error: El número de empleado no puede estar vacío.")
                intento += 1
                continue

            # Buscamos el número introducido en la lista de números de usuarios registrados.
            if numero_ingresado in numeros_usuarios:
                print(f"✅ Usuario {numero_ingresado} encontrado.")
                return numero_ingresado
            else:
                intento += 1
                intentos_restantes = max_intentos - intento
                if intentos_restantes > 0:
                    print(f"❌ Este usuario no está registrado. Intentos restantes: {intentos_restantes}")
                else:
                    print("❌ Has agotado los intentos.")
        except KeyboardInterrupt:
            # Si el usuario cancela con 'c', relanzamos el KeyboardInterrupt
            # para que lo capture quien llamó a esta función.
            raise

    return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: validar_lluvia()
# Mismo patrón que validar_temperatura(), validar_humedad() y validar_viento().
# ─────────────────────────────────────────────────────────────────────────────
def validar_lluvia():
    """
    Solicita y valida la cantidad de lluvia (precipitaciones).
    Rango permitido: 0 a 500 mm.
    
    DEV 1 / DEV 2: Llama a esta función sin parámetros.
    Retorna: Un número float (ej. 15.5).
    """
    while True:
        try:
            entrada = input("Introduce la cantidad de lluvia (0 a 500 mm) [o 'c' para cancelar]: ").strip()
            if entrada.lower() == 'c': raise KeyboardInterrupt
            
            lluvia = float(entrada)
            
            # La lluvia no puede ser negativa y ponemos un tope lógico de 500mm,
            # que equivale a una precipitación extrema pero posible en registros históricos.
            if 0 <= lluvia <= 500:
                return lluvia  
            else:
                print(f"❌ Error: {lluvia} mm está fuera del rango lógico (0 a 500).")
        
        except ValueError:
            print("❌ Error: La cantidad de lluvia debe ser un valor numérico (ejemplo: 12.5).")
            
        print("🔄 Inténtalo de nuevo.\n")
