import base64
import getpass
import hashlib
import hmac
import json
import os

import alertas
import persistencia
import pwinput
import validaciones

DB_EMPLEADOS = persistencia.ARCHIVO_EMPLEADOS
ARCHIVO_USUARIOS = persistencia.ARCHIVO_USUARIOS
ARCHIVO_CLIMA = persistencia.ARCHIVO_JSON
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


def _obtener_temperatura_registro(registro):  # Funcion auxiliar para obtener la temperatura de un registro, considerando posibles variaciones en la clave (temp o temperatura)
    return registro.get("temp", registro.get("temperatura", 0))


def _pedir_float_editable(mensaje, valor_actual, minimo=None, maximo=None):  # Funcion auxiliar para pedir un valor numerico editable, con validacion de rango y formato, y opcion de mantener el valor actual
    while True:
        entrada = input(f"{mensaje} (actual: {valor_actual}) [Enter para mantener]: ").strip()
        if not entrada:
            return float(valor_actual)

        try:
            valor = float(entrada)
        except ValueError:
            print("Error: Debes introducir un valor numerico valido")
            continue

        if minimo is not None and valor < minimo:
            print(f"Error: El valor no puede ser menor que {minimo}")
            continue
        if maximo is not None and valor > maximo:
            print(f"Error: El valor no puede ser mayor que {maximo}")
            continue

        return valor


def _pedir_distrito_editable(distrito_actual):  # Funcion auxiliar para pedir un distrito editable, validando contra la lista de distritos oficiales en config.json, y opcion de mantener el valor actual
    try:
        with open(persistencia.CONFIGURACION_DE_ARCHIVO, "r", encoding="utf-8") as archivo:
            distritos = json.load(archivo).get("distritos_oficiales", [])
    except (FileNotFoundError, json.JSONDecodeError):
        print("No se pudo validar el distrito mencionado en la base de datos")
        return distrito_actual

    mapa = {d.lower(): d for d in distritos}

    while True:
        entrada = input(f"Nuevo distrito (actual: {distrito_actual}) [Enter para mantener]: ").strip()
        if not entrada:
            return distrito_actual

        zona_normalizada = entrada.lower()
        if zona_normalizada in mapa:
            return mapa[zona_normalizada]

        print("Distrito no reconocido. Introduce un distrito oficial o pulsa Enter para mantener el actual")


def imprimir_detalle(r, idx=None):  # Funcion para imprimir el detalle de un registro de clima, con formato legible, mostrando alertas y si el registro ha sido editado
    id_txt = f"ID: {idx} | " if idx is not None else ""
    edit_txt = " [EDITADO]" if r.get("editado") else ""
    alertas_txt = ", ".join(r.get("alertas", [])) if r.get("alertas") else "Ninguna"
    print(f"{id_txt}Fecha: {r['fecha']} | Distrito: {r['distrito']} | Zona: {r.get('zona', 'N/A')}")
    print(f"      Temp: {_obtener_temperatura_registro(r)}C | Hum: {r['humedad']}% | Viento: {r['viento']}km/h")
    print(f"      Lluvia: {r['lluvia']}mm | Alertas: {alertas_txt}{edit_txt}")
    print("-" * 75)


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


def consultar_y_editar_historial(num_empleado):  # Funcion para que un usuario pueda consultar sus registros de clima y editar uno de ellos.
    registros = cargar_datos(ARCHIVO_CLIMA)
    mis_indices = [i for i, r in enumerate(registros) if r.get("registrado_por") == num_empleado]

    if not mis_indices:
        print("No tienes registros.")
        return

    for i in mis_indices:
        imprimir_detalle(registros[i], i)

    opcion = input("\nID del registro que deseas corregir por completo? (Enter para salir): ").strip()

    if opcion.isdigit() and int(opcion) in mis_indices:
        idx = int(opcion)
        if registros[idx].get("editado"):
            print("ERROR: Este registro ya fue corregido anteriormente y esta bloqueado")
        else:
            print(f"\nVas a editar TODO el registro de {registros[idx]['distrito']} del dia {registros[idx]['fecha']}.")
            confirmar = input("Estas seguro de que quieres continuar? Solo podras hacerlo UNA VEZ (si/no): ").strip().lower()

            if confirmar == "si":
                try:
                    print("\n--- INTRODUCE LOS NUEVOS DATOS CORRECTOS ---")

                    distrito_actual = registros[idx].get("distrito", "")
                    temp_actual = _obtener_temperatura_registro(registros[idx])
                    humedad_actual = registros[idx].get("humedad", 0)
                    viento_actual = registros[idx].get("viento", 0)
                    lluvia_actual = registros[idx].get("lluvia", 0)

                    distrito_final = _pedir_distrito_editable(distrito_actual)
                    temp_final = _pedir_float_editable("Nueva Temperatura", temp_actual, -20, 50)
                    humedad_final = _pedir_float_editable("Nueva Humedad %", humedad_actual, 0, 100)
                    viento_final = _pedir_float_editable("Nueva Velocidad del Viento km/h", viento_actual, 0, 150)
                    lluvia_final = _pedir_float_editable("Nueva Lluvia mm", lluvia_actual, 0)

                    for i, reg in enumerate(registros):
                        if i != idx and reg.get("fecha") == registros[idx].get("fecha") and reg.get("distrito", "").lower() == distrito_final.lower():
                            print("La correccion generaria un duplicado para esa fecha y distrito")
                            return

                    umbrales = persistencia.obtener_umbrales_alerta()
                    alertas_activas = alertas.evaluar_alertas(
                        {
                            "temperatura": temp_final,
                            "humedad": humedad_final,
                            "viento": viento_final,
                            "lluvia": lluvia_final,
                        },
                        umbrales,
                    )

                    registros[idx]["distrito"] = distrito_final
                    registros[idx]["temp"] = temp_final
                    registros[idx]["temperatura"] = temp_final
                    registros[idx]["humedad"] = humedad_final
                    registros[idx]["viento"] = viento_final
                    registros[idx]["lluvia"] = lluvia_final
                    registros[idx]["alertas"] = alertas_activas
                    registros[idx]["editado"] = True

                    guardar_datos(ARCHIVO_CLIMA, registros)
                    print("\nRegistro corregido y guardado con exito.")

                except ValueError:
                    print("Error: Has introducido un formato de numero incorrecto. No se guardaron los cambios")
            else:
                print("Operacion cancelada.")


def consultar_por_distrito():  # Funcion para consultar registros por distrito
    distrito = input("Distrito: ").strip().title()
    for r in cargar_datos(ARCHIVO_CLIMA):
        if r.get("distrito") == distrito:
            imprimir_detalle(r)


def consultar_por_fecha():  # Funcion para consultar registros por fecha
    fecha = input("Fecha (YYYY-MM-DD): ")
    for r in cargar_datos(ARCHIVO_CLIMA):
        if r.get("fecha") == fecha:
            imprimir_detalle(r)


def obtener_nombre_operario(num_empleado):  # Funcion para obtener el nombre del operario a partir de su numero de empleado
    if not num_empleado or num_empleado == "Desconocido":
        return "Operario Desconocido"

    usuarios = cargar_datos(ARCHIVO_USUARIOS)

    for u in usuarios:
        if u["num_empleado"] == num_empleado:
            return f"Usuario: {u['nombre']} {u['apellidos']} (ID: {num_empleado})"

    return f"Usuario no registrado (ID: {num_empleado})"
