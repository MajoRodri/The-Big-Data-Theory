"""
Punto de Entrada - PyClima Resiliente
Responsable: Equipo "Guardianes del Dato"
Descripción: Archivo principal que arranca la interfaz del usuario.
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTACIONES
# Este archivo necesita "piezas" que están en otros archivos del proyecto.
# 'from' e 'import' son las instrucciones para traer esas piezas aquí.
# Es como llamar a tus compañeros de equipo antes de empezar el partido.
# ─────────────────────────────────────────────────────────────────────────────

# Importamos la clase InterfazPyClima desde el archivo interfaz.py.
# Una 'clase' es como un molde o plantilla: con ella crearemos el objeto 'app'
# que gestionará todos los menús del programa.
from interfaz import InterfazPyClima

# Importamos el módulo auth completo (auth.py).
# Al escribir 'import auth' (sin 'from'), traemos el módulo entero.
# Luego usaremos sus funciones escribiendo auth.iniciar_sesion() o auth.registrar_usuario(),
# dejando claro de dónde viene cada función.
import auth

# Importamos el módulo persistencia completo (persistencia.py).
# Lo necesitamos para llamar a persistencia.inicializar_archivo_datos()
# al arrancar el programa, que se asegura de que el archivo de datos exista.
import persistencia
from logger_config import setup_logging

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE PRINCIPAL: if __name__ == "__main__"
#
# Esta es una de las líneas más importantes de Python y merece una explicación
# especial. Cuando Python ejecuta un archivo, le asigna una variable interna
# llamada __name__. Si el archivo se está ejecutando DIRECTAMENTE (es decir,
# el usuario escribió "python main.py" en la terminal), Python pone
# __name__ = "__main__". Si en cambio este archivo fuera importado por OTRO
# archivo, __name__ tendría el nombre del archivo ("main"), no "__main__".
#
# En resumen: todo el código dentro de este 'if' SOLO se ejecuta cuando
# lanzamos el programa directamente con "python main.py".
# Es la puerta de entrada oficial al programa.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # 'try' envuelve TODO el arranque del programa como un gran escudo protector.
    # Si algo falla de forma inesperada en cualquier punto del arranque,
    # el programa no se cerrará con un error feo: llegará al 'except' de abajo
    # y mostrará un mensaje controlado.
    try:
        setup_logging()

        # ─────────────────────────────────────────────────────────────────────
        # PASO 1: Mensaje de bienvenida
        # Simplemente imprimimos el banner de presentación del sistema.
        # ─────────────────────────────────────────────────────────────────────
        print("\n" + "="*50)
        print("🌦️  SISTEMA PYCLIMA RESILIENTE")
        print("Sistema de Monitoreo Climático Avanzado")
        print("="*50)

        # ─────────────────────────────────────────────────────────────────────
        # PASO 2: Inicialización del sistema
        # Llamamos a esta función de persistencia.py para que compruebe si el
        # archivo datos_clima.json existe. Si no existe, lo crea vacío.
        # Es como encender las luces y comprobar que todo está en orden
        # antes de abrir el negocio.
        # ─────────────────────────────────────────────────────────────────────
        persistencia.inicializar_archivo_datos()
        auth.migrar_passwords_usuarios()

        # ─────────────────────────────────────────────────────────────────────
        # PASO 3: Preparar la variable del usuario autenticado
        # Creamos la variable 'usuario_autenticado' y la ponemos a None
        # (que en Python significa "vacío" o "nada").
        # Esta variable actuará como un "semáforo en rojo": mientras esté
        # en None, el programa sabe que nadie ha iniciado sesión todavía
        # y no dejará pasar al menú principal.
        # ─────────────────────────────────────────────────────────────────────
        usuario_autenticado = None

        # ─────────────────────────────────────────────────────────────────────
        # PASO 4: El Bucle de Bienvenida — "El Muro de Seguridad"
        #
        # 'while not usuario_autenticado' significa:
        # "Mientras usuario_autenticado sea None (o vacío), sigue dando vueltas".
        # El bucle SOLO se rompe cuando 'usuario_autenticado' deja de ser None,
        # es decir, cuando auth.iniciar_sesion() devuelve los datos de un usuario
        # válido. Es como un torniquete de metro: no puedes pasar hasta que
        # pases tu tarjeta válida.
        # ─────────────────────────────────────────────────────────────────────
        while not usuario_autenticado:
            print("\n1. Iniciar sesión")
            print("2. Registrarse")
            print("3. Cerrar programa")
            
            # Pedimos al usuario que elija una opción y eliminamos espacios
            # accidentales con .strip().
            opcion_inicio = input("Seleccione una opción (1-3): ").strip()

            if opcion_inicio == "1":
                # Llamamos a la función de inicio de sesión de auth.py.
                # Esta función devuelve los datos del usuario si la contraseña
                # es correcta, o None si falla.
                # Guardamos lo que devuelve en 'usuario_autenticado'.
                # Si devuelve datos reales → el bucle 'while' se rompe y avanzamos.
                # Si devuelve None → el bucle continúa y vuelve a mostrar el menú.
                usuario_autenticado = auth.iniciar_sesion()
                
            elif opcion_inicio == "2":
                # El registro no inicia sesión automáticamente.
                # Después de registrarse, el bucle vuelve a empezar y el nuevo
                # usuario tendrá que iniciar sesión manualmente con la opción 1.
                auth.registrar_usuario()
                
            elif opcion_inicio == "3":
                # exit() es una función de Python que cierra el programa
                # completamente en ese mismo instante, sin ejecutar nada más.
                print("\nSaliendo del sistema de seguridad...")
                exit()
                
            else:
                # Si el usuario escribe algo que no es 1, 2 ni 3,
                # le avisamos y el bucle vuelve a mostrar las opciones.
                print("❌ Opción no válida. Intente de nuevo.")

        # ─────────────────────────────────────────────────────────────────────
        # PASO 5: La puerta se abre
        #
        # Si el programa llega a esta línea, significa que el bucle 'while'
        # terminó. Y sabemos que SOLO puede terminar si 'usuario_autenticado'
        # tiene datos reales de un usuario válido.
        # ─────────────────────────────────────────────────────────────────────
        print(f"\n✅ Acceso concedido.")
        
        # Creamos el objeto 'app' a partir de la plantilla InterfazPyClima.
        # Le pasamos los datos del usuario que acaba de iniciar sesión
        # (usuario_actual=usuario_autenticado) para que la interfaz sepa
        # quién está usando el sistema en todo momento (para registrar autoría,
        # permitir ediciones propias, etc.).
        app = InterfazPyClima(usuario_actual=usuario_autenticado)
        
        # Arrancamos el menú principal del programa.
        # A partir de aquí, el control pasa completamente a interfaz.py.
        app.menu_principal()

    # ─────────────────────────────────────────────────────────────────────────
    # MANEJO DE ERRORES DEL ARRANQUE
    # ─────────────────────────────────────────────────────────────────────────

    except KeyboardInterrupt:
        # KeyboardInterrupt se lanza cuando el usuario pulsa Ctrl+C en la terminal.
        # Es la forma que tiene el sistema operativo de decir "para el programa ya".
        # En lugar de que aparezca un error feo, mostramos un mensaje amable.
        print("\n\n❌ Aplicación interrumpida por el usuario")

    except Exception as e:
        # 'Exception' es el comodín de todos los errores de Python.
        # Si ocurre cualquier otro error inesperado que no sea un Ctrl+C,
        # llegará aquí. La variable 'e' contiene la descripción del error,
        # que imprimimos para ayudar a diagnosticar el problema.
        print(f"\n❌ Error crítico de inicio: {e}")
