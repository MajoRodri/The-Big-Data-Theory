import base64
import hashlib
import hmac
import json
import os

import persistencia
import pwinput
import validaciones

DB_EMPLEADOS = persistencia.ARCHIVO_EMPLEADOS
ARCHIVO_USUARIOS = persistencia.ARCHIVO_USUARIOS
ALGORITMO_HASH = "pbkdf2_sha256"
ITERACIONES_HASH = 200000


def cargar_datos(archivo):  # Valida la existencia del archivo y su formato correcto, para evitar errores posteriores al cargar datos
    if not os.path.exists(archivo):
        return []
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Advertencia: El archivo '{archivo}' esta corrupto o tiene formato invalido")
        return []
    except Exception as e:
        print(f"Advertencia: No se pudo leer '{archivo}': {e}")
        return []


def guardar_datos(archivo, datos):  # Funcion para guardar datos en formato JSON, con manejo de errores
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def generar_hash_password(password):  # Genera un hash seguro de la contraseña con salt aleatorio
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERACIONES_HASH,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(hash_bytes).decode("ascii")
    return f"{ALGORITMO_HASH}${ITERACIONES_HASH}${salt_b64}${hash_b64}"


def verificar_password(password, password_hash):  # Verifica una contraseña contra el hash almacenado
    try:
        algoritmo, iteraciones, salt_b64, hash_b64 = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if algoritmo != ALGORITMO_HASH:
        return False

    try:
        salt = base64.b64decode(salt_b64.encode("ascii"))
        hash_guardado = base64.b64decode(hash_b64.encode("ascii"))
        hash_calculado = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iteraciones),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(hash_calculado, hash_guardado)


def migrar_passwords_usuarios():  # Migra usuarios con password en claro a password_hash sin romper el flujo
    usuarios = cargar_datos(ARCHIVO_USUARIOS)
    cambios = 0

    for usuario in usuarios:
        if usuario.get("password_hash"):
            continue

        password_plano = usuario.get("password")
        if not password_plano:
            continue

        usuario["password_hash"] = generar_hash_password(password_plano)
        usuario.pop("password", None)
        cambios += 1

    if cambios:
        guardar_datos(ARCHIVO_USUARIOS, usuarios)

    return cambios


def registrar_usuario():  # Funcion para registrar un nuevo usuario, validando que el numero de empleado exista en empleados.json
    try:
        print("\n--- REGISTRO DE NUEVO USUARIO ---")
        migrar_passwords_usuarios()

        print("\n[PASO 1/3] Verificacion de autenticidad del empleado")
        print("-" * 50)
        num_empleado = validaciones.validar_acceso()

        if num_empleado is None:
            print("No se puede continuar sin un numero de empleado valido")
            return

        usuarios = cargar_datos(ARCHIVO_USUARIOS)
        if any(u.get("num_empleado") == num_empleado for u in usuarios):
            print("Este numero de empleado ya tiene un usuario registrado")
            return

        print("\n[PASO 2/3] Informacion personal")
        print("-" * 50)
        nombre = input("Nombre: ").strip()
        apellidos = input("Apellidos: ").strip()

        if not nombre or not apellidos:
            print("Error: Nombre y apellidos no pueden estar vacios")
            return

        print("\n[PASO 3/3] Identificador de acceso")
        print("-" * 50)
        while True:
            pw = pwinput.pwinput("Contrasena (8+ alfanumericos): ", mask="*")
            if len(pw) >= 8 and pw.isalnum():
                break
            print("Error: Minimo 8 caracteres sin simbolos")

        usuarios.append(
            {
                "nombre": nombre,
                "apellidos": apellidos,
                "num_empleado": num_empleado,
                "password_hash": generar_hash_password(pw),
            }
        )
        guardar_datos(ARCHIVO_USUARIOS, usuarios)
        print("\nRegistro exitoso. Ya puedes iniciar sesion")

    except Exception as e:
        print(f"Error durante el registro: {e}")
        print("Por favor, intenta de nuevo.")


def iniciar_sesion():
    print("\n--- INICIAR SESION ---")
    max_intentos_pw = 3
    intento_pw = 0
    migrar_passwords_usuarios()

    num = validaciones.validar_usuario_sesion()

    if num is None:
        print("No se pudo validar el usuario. Vuelve al menu principal")
        return None

    while intento_pw < max_intentos_pw:
        pw = pwinput.pwinput(f"Contrasena [{intento_pw + 1}/{max_intentos_pw}]: ", mask="*")

        for u in cargar_datos(ARCHIVO_USUARIOS):
            if u.get("num_empleado") != num:
                continue

            password_hash = u.get("password_hash")
            password_plano = u.get("password")

            if password_hash and verificar_password(pw, password_hash):
                print(f"\nBienvenido/a, {u['nombre']} {u['apellidos']} (ID: {u['num_empleado']})")
                return u

            if password_plano and password_plano == pw:
                print(f"\nBienvenido/a, {u['nombre']} {u['apellidos']} (ID: {u['num_empleado']})")
                return u

        intento_pw += 1
        if intento_pw < max_intentos_pw:
            print("Contrasena incorrecta. Intenta de nuevo.")
            print(f"Intentos restantes: {max_intentos_pw - intento_pw}\n")

    print(f"Has agotado los {max_intentos_pw} intentos de contrasena. Vuelve al menu principal")
    return None
