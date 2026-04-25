"""
Punto de entrada principal para The Big Data Theory.
Sistema de Monitoreo Climático del Ayuntamiento de Madrid.
"""

import os
import sys

from dotenv import load_dotenv

_src_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_src_dir, '..', '.env'))

from interfaz import InterfazTBDT
import auth
import persistencia
from logger_config import setup_logging


if __name__ == "__main__":
    try:
        setup_logging()

        print("\n" + "=" * 50)
        print("  THE BIG DATA THEORY")
        print("  Sistema de Monitoreo Climático - Madrid")
        print("=" * 50)

        persistencia.inicializar_archivo_datos()
        auth.migrar_passwords_usuarios()

        usuario_autenticado = None

        while not usuario_autenticado:
            print("\n1. Iniciar sesión")
            print("2. Registrarse")
            print("3. Cerrar programa")

            opcion = input("Seleccione una opción (1-3): ").strip()

            if opcion == "1":
                usuario_autenticado = auth.iniciar_sesion()
            elif opcion == "2":
                auth.registrar_usuario()
            elif opcion == "3":
                print("\nSaliendo del sistema...")
                sys.exit(0)
            else:
                print("❌ Opción no válida. Intente de nuevo.")

        print("\n✅ Acceso concedido.")

        app = InterfazTBDT(usuario_actual=usuario_autenticado)
        app.menu_principal()

    except KeyboardInterrupt:
        print("\n\n❌ Aplicación interrumpida por el usuario")

    except Exception as e:
        print(f"\n❌ Error crítico de inicio: {e}")
