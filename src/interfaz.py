"""
Módulo de interfaz para The Big Data Theory.
Sistema de Monitoreo Climático del Ayuntamiento de Madrid.
"""

import os
import csv
import shutil
import validaciones
import alertas
import persistencia
import auth
import analitica
import Api
import comparativa
import scheduler as sched_module
from datetime import datetime


class InterfazTBDT:

    def __init__(self, ruta_datos=persistencia.ARCHIVO_JSON, usuario_actual=None):
        """
        Inicializa la interfaz cargando el histórico de datos y configurando el usuario autenticado.

        Args:
            ruta_datos (str): Ruta al archivo JSON de datos históricos.
            usuario_actual (dict): Datos del usuario que ha iniciado sesión.
        """
        self.ruta_datos = ruta_datos
        self.datos = self._cargar_datos()
        self.zonas_validas = self._obtener_zonas()
        self.usuario_actual = usuario_actual

    def _cargar_datos(self):
        """
        Carga el histórico completo desde la capa de persistencia.

        Returns:
            list: Lista de registros climáticos almacenados.
        """
        return persistencia.leer_historico()

    def _obtener_zonas(self):
        """
        Extrae la lista única de distritos presentes en el histórico.

        Returns:
            list: Distritos ordenados alfabéticamente.
        """
        zonas = set()
        for reg in self.datos:
            if "distrito" in reg:
                zonas.add(reg["distrito"])
        return sorted(list(zonas)) if zonas else []

    def _validar_duplicado(self, fecha, distrito, fuente="manual"):
        """
        Verifica si ya existe un registro con la misma fecha, distrito y fuente.
        Permite un máximo de dos registros por clave (uno manual + uno API).

        Args:
            fecha (str): Fecha en formato AAAA-MM-DD.
            distrito (str): Nombre del distrito.
            fuente (str): Fuente del registro a añadir ("manual" o "api").

        Returns:
            bool: True si el registro debe ser bloqueado (ya existe misma fuente o hay 2 registros).
        """
        registros = [
            r for r in self.datos
            if r.get("fecha") == str(fecha)
            and r.get("distrito", "").lower() == distrito.lower()
        ]
        if len(registros) >= 2:
            return True
        return any(r.get("fuente", "manual") == fuente for r in registros)

    def _analizar_alertas(self, temperatura, humedad, viento, lluvia=0):
        """
        Evalúa alertas climáticas usando los umbrales configurados en el sistema.

        Args:
            temperatura (float): Temperatura en grados Celsius.
            humedad (float): Humedad relativa en porcentaje.
            viento (float): Velocidad del viento en km/h.
            lluvia (float): Precipitación en mm.

        Returns:
            list: Lista de mensajes de alerta activos.
        """
        umbrales = persistencia.obtener_umbrales_alerta()
        datos_registro = {
            "temperatura": temperatura,
            "humedad": humedad,
            "viento": viento,
            "lluvia": lluvia
        }
        return alertas.evaluar_alertas(datos_registro, umbrales)

    def _mostrar_encabezado(self, titulo):
        """
        Imprime un encabezado visual formateado con el título dado.

        Args:
            titulo (str): Texto a mostrar como encabezado.
        """
        print("\n" + "="*50)
        print(f"  {titulo}")
        print("="*50)

    def _mostrar_separador(self):
        """Imprime una línea separadora visual."""
        print("-" * 50)

    def _normalizar_distrito_oficial(self, distrito):
        """
        Normaliza y valida un nombre de distrito contra la lista oficial de Madrid.

        Args:
            distrito (str): Nombre del distrito a validar.

        Returns:
            str or None: Nombre oficial si es válido, None si no se encuentra.
        """
        distritos_oficiales = persistencia.obtener_distritos_permitidos()
        mapa_distritos = {item.lower(): item for item in distritos_oficiales}
        return mapa_distritos.get(distrito.strip().lower())

    def _pedir_numero_editable(self, etiqueta, valor_actual, minimo=None, maximo=None):
        """
        Solicita un valor numérico con validación de rango, permitiendo mantener el actual.

        Args:
            etiqueta (str): Texto descriptivo del campo.
            valor_actual (float): Valor actual del campo.
            minimo (float, optional): Límite mínimo permitido.
            maximo (float, optional): Límite máximo permitido.

        Returns:
            float: Valor introducido o valor actual si el usuario presiona Enter.
        """
        while True:
            entrada = input(f"{etiqueta} (actual: {valor_actual}) [Enter para mantener]: ").strip()
            if not entrada:
                return float(valor_actual)

            try:
                valor = float(entrada)
            except ValueError:
                print("❌ Introduce un valor numérico válido.")
                continue

            if minimo is not None and valor < minimo:
                print(f"❌ El valor no puede ser menor que {minimo}.")
                continue
            if maximo is not None and valor > maximo:
                print(f"❌ El valor no puede ser mayor que {maximo}.")
                continue

            return valor

    def registrar_datos(self):
        """
        Muestra el submenú de registro y delega en el flujo manual o desde API.
        """
        self._mostrar_encabezado("📝 REGISTRAR NUEVOS DATOS CLIMÁTICOS")
        print("1. Registro manual")
        print("2. Registro automático desde API")
        print("3. Volver al menú principal")
        self._mostrar_separador()

        opcion_registro = input("Seleccione una opción (1-3): ").strip()

        if opcion_registro == "1":
            self._registrar_datos_manual()
        elif opcion_registro == "2":
            self._registrar_datos_api()
        elif opcion_registro != "3":
            print("❌ Opción no válida.")
            input("Presione Enter para continuar...")

    def _registrar_datos_manual(self):
        """
        Solicita los datos climáticos al usuario paso a paso, los valida,
        evalúa alertas preliminares y los persiste en el histórico.
        """
        self.datos = self._cargar_datos()

        while True:
            try:
                print("\n[1/6] FECHA DEL REGISTRO")
                fecha = validaciones.validar_fecha()

                print("\n[2/6] ZONA/DISTRITO")
                distrito = validaciones.validar_zona()
                if not distrito:
                    return

                if self._validar_duplicado(fecha, distrito, fuente="manual"):
                    print(f"⚠️  Ya existe un registro manual para {distrito} en {fecha}.")
                    if input("¿Desea ingresar datos nuevamente? (s/n): ").lower() != 's':
                        return
                    continue

                print("\n[3/6] TEMPERATURA")
                temperatura = validaciones.validar_temperatura()

                print("\n[4/6] HUMEDAD")
                humedad = validaciones.validar_humedad()

                print("\n[5/6] VELOCIDAD DEL VIENTO")
                viento = validaciones.validar_viento()

                print("\n[6/6] PRECIPITACIONES (LLUVIA)")
                lluvia = validaciones.validar_lluvia()

                print("\n" + "="*50)
                print("✅ DATOS VALIDADOS EXITOSAMENTE")
                print("="*50)

                umbrales = persistencia.obtener_umbrales_alerta()
                datos_registro = {"temperatura": temperatura, "humedad": humedad, "viento": viento, "lluvia": lluvia}
                alertas_activas = alertas.evaluar_alertas(datos_registro, umbrales)

                if alertas_activas:
                    print("\n🚨 ALERTAS PRELIMINARES DETECTADAS:")
                    for alerta in alertas_activas:
                        print(f"   {alerta}")
                else:
                    print("\n✅ Niveles climáticos normales (Sin alertas)")
                print("-" * 50)

                nuevo_registro = {
                    "fecha": fecha,
                    "distrito": distrito,
                    "fuente": "manual",
                    "temperatura": temperatura,
                    "temp": temperatura,
                    "humedad": humedad,
                    "viento": viento,
                    "lluvia": 0.0,
                    "alertas": alertas_activas,
                    "registrado_por": self.usuario_actual["num_empleado"] if self.usuario_actual else "Desconocido",
                    "editado": False
                }

                exito = persistencia.registrar_nuevo_dato(nuevo_registro)

                if exito:
                    self._mostrar_separador()
                    if input("\n¿Registrar otro dato? (s/n): ").strip().lower() != 's':
                        return
                else:
                    return

            except KeyboardInterrupt:
                print("\n\n❌ Registro cancelado por el usuario")
                return
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                if input("¿Desea ingresar los datos nuevamente? (s/n): ").lower() != 's':
                    return

    def _registrar_datos_api(self):
        """
        Registra datos climáticos obteniendo la lectura directamente desde WeatherAPI.

        Solicita el distrito, consulta la API, muestra los datos y confirma el guardado.
        """
        self.datos = self._cargar_datos()

        while True:
            try:
                fecha = datetime.now().strftime("%Y-%m-%d")

                print(f"\n📅 Fecha automática del registro: {fecha}")
                print("\n[1/1] ZONA/DISTRITO")
                distrito = validaciones.validar_zona()
                if not distrito:
                    return

                if self._validar_duplicado(fecha, distrito, fuente="api"):
                    print(f"⚠️  Ya existe un registro de API para {distrito} en {fecha}.")
                    if input("¿Desea intentarlo de nuevo? (s/n): ").strip().lower() != "s":
                        return
                    continue

                nuevo_registro = Api.obtener_registro_climatico(
                    distrito,
                    usuario_actual=self.usuario_actual,
                    fecha=fecha,
                )

                if nuevo_registro is None:
                    print("❌ No se pudo obtener datos desde API.")
                    if input("¿Desea intentarlo nuevamente? (s/n): ").strip().lower() != "s":
                        return
                    continue

                print("\n" + "=" * 50)
                print("✅ DATOS OBTENIDOS DESDE LA API")
                print("=" * 50)
                print(f"📍 Distrito: {nuevo_registro['distrito']}")
                print(f"📅 Fecha: {nuevo_registro['fecha']}")
                print(f"🌡️  Temperatura: {nuevo_registro['temperatura']}°C")
                print(f"💧 Humedad: {nuevo_registro['humedad']}%")
                print(f"💨 Viento: {nuevo_registro['viento']} km/h")
                print(f"🌧️  Lluvia: {nuevo_registro['lluvia']} mm")

                if nuevo_registro["alertas"]:
                    print("\n🚨 ALERTAS PRELIMINARES DETECTADAS:")
                    for alerta in nuevo_registro["alertas"]:
                        print(f"   {alerta}")
                else:
                    print("\n✅ Niveles climáticos normales (Sin alertas)")

                self._mostrar_separador()
                exito = persistencia.registrar_nuevo_dato(nuevo_registro)

                if exito:
                    self._mostrar_separador()
                    if input("\n¿Registrar otro dato desde API? (s/n): ").strip().lower() != "s":
                        return
                    self.datos = self._cargar_datos()
                else:
                    return

            except KeyboardInterrupt:
                print("\n\n❌ Registro desde API cancelado por el usuario")
                return
            except Exception as e:
                print(f"❌ Error al obtener datos desde la API: {e}")
                if input("¿Desea intentarlo nuevamente? (s/n): ").strip().lower() != "s":
                    return

    def obtener_datos_api(self):
        """
        Obtiene datos climáticos desde WeatherAPI para un distrito seleccionado y
        ofrece al usuario la posibilidad de guardarlos.

        Args:
            Sin parámetros adicionales. Lee los distritos disponibles desde config.json.

        Returns:
            None. Los datos se muestran en pantalla y opcionalmente se guardan.
        """
        self._mostrar_encabezado("📡 OBTENER DATOS DESDE API METEOROLÓGICA")

        distritos = persistencia.obtener_distritos_permitidos()
        if not distritos:
            print("❌ No se encontraron distritos configurados en config.json")
            input("Presione Enter para volver...")
            return

        print("\n📍 Distritos disponibles:")
        for i, distrito in enumerate(distritos, 1):
            print(f"   {i}. {distrito}")

        try:
            seleccion = int(input("\nSeleccione un distrito (número): ")) - 1
            if not (0 <= seleccion < len(distritos)):
                print("❌ Selección inválida")
                return

            distrito_seleccionado = distritos[seleccion]
        except ValueError:
            print("❌ Ingrese un número válido")
            return

        print(f"\n⏳ Consultando WeatherAPI para {distrito_seleccionado}...")
        try:
            registro_api = Api.obtener_registro_climatico(
                ciudad=distrito_seleccionado,
                usuario_actual=self.usuario_actual
            )
        except Exception as error:
            print(f"❌ Error al consultar la API: {error}")
            input("Presione Enter para volver...")
            return

        if registro_api is None:
            print("❌ No se pudo obtener datos de WeatherAPI.")
            input("Presione Enter para volver...")
            return

        print("\n" + "="*50)
        print("✅ DATOS OBTENIDOS DE WEATHERAPI")
        print("="*50)
        print(f"📍 Distrito: {registro_api['distrito']}")
        print(f"📅 Fecha: {registro_api['fecha']}")
        print(f"🌡️  Temperatura: {registro_api['temperatura']}°C")
        print(f"💧 Humedad: {registro_api['humedad']}%")
        print(f"💨 Viento: {registro_api['viento']} km/h")
        print(f"🌧️  Lluvia: {registro_api['lluvia']} mm")
        print(f"🌤️  Condición: {registro_api['condicion']}")

        if registro_api['alertas']:
            print("\n🚨 ALERTAS DETECTADAS:")
            for alerta in registro_api['alertas']:
                print(f"   {alerta}")
        else:
            print("\n✅ No hay alertas")

        print("="*50)

        confirmacion = input("\n¿Desea guardar estos datos? (s/n): ").strip().lower()

        if confirmacion == 's':
            try:
                exito = persistencia.registrar_nuevo_dato(registro_api)
                if exito:
                    print("✅ ¡Datos guardados exitosamente!")
                    self.datos = self._cargar_datos()
                else:
                    print("❌ No se pudieron guardar los datos")
            except Exception as error:
                print(f"❌ Error al guardar: {error}")
        else:
            print("❌ Operación cancelada. Los datos no se guardaron.")

        input("\nPresione Enter para volver al menú principal...")

    def consultar_datos(self):
        """
        Muestra el menú avanzado de consultas con filtros por zona, fecha y usuario.
        """
        while True:
            self._mostrar_encabezado("📊 CONSULTAR DATOS 📊 ")
            self.datos = self._cargar_datos()

            if not self.datos:
                print("❌ No hay datos registrados en el sistema.")
                input("Presione Enter para continuar...")
                return

            print("1. 📍 Filtrar por Zona/Distrito")
            print("2. 📅 Filtrar por Fecha")
            print("3. 👤 Filtrar por Usuario (Mis registros / Editar)")
            print("4. ⬅️  Volver al menú principal")
            self._mostrar_separador()

            opcion = input("Seleccione un filtro (1-4): ").strip()

            if opcion == "1":
                self._menu_consultar_zona()
            elif opcion == "2":
                self._menu_consultar_fecha()
            elif opcion == "3":
                self._menu_consultar_usuario()
            elif opcion == "4":
                break
            else:
                print("❌ Opción no válida.")
                continue

            if opcion in ["1", "2", "3"]:
                print("\n" + "="*50)
                self._mostrar_encabezado("OPCIONES POSTERIORES:")
                print("1. Hacer otra consulta")
                print("2. Volver al menú principal")
                print("3. Salir del sistema")

                post_opcion = input("¿Qué desea hacer ahora? (1-3): ").strip()

                if post_opcion == "2":
                    break
                elif post_opcion == "3":
                    self.salir()
                    exit()

    def _menu_consultar_fecha(self):
        """
        Busca y muestra todos los registros correspondientes a una fecha exacta.
        """
        print("\n📅 BÚSQUEDA POR FECHA")
        fecha_buscada = validaciones.validar_fecha()

        print(f"\n📊 Datos del día: {fecha_buscada}")
        self._mostrar_separador()

        encontrados = 0
        for reg in self.datos:
            if reg.get("fecha") == fecha_buscada:
                encontrados += 1
                temp = reg.get('temp', reg.get('temperatura', 0))
                print(f"📍 Zona: {reg.get('distrito', 'Desconocida')}")
                print(f"   🌡️  Temperatura: {temp}°C")
                print(f"   💧 Humedad: {reg.get('humedad', 0)}%")
                print(f"   💨 Viento: {reg.get('viento', 0)} km/h")
                print(f"   🌧️  Lluvia: {reg.get('lluvia', 0)} mm")

                alertas_locales = self._analizar_alertas(
                    temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0)
                )
                for alerta in alertas_locales:
                    print(f"   {alerta}")
                print("-" * 30)

        if encontrados == 0:
            print(f"❌ No hay datos registrados para la fecha {fecha_buscada}")
        else:
            print(f"✅ Total de registros encontrados: {encontrados}")

    def _menu_consultar_usuario(self):
        """
        Muestra todos los usuarios registrados en el sistema. Cualquier operario puede
        consultar los registros de otro, pero solo el dueño puede editarlos.
        """
        print("\n👤 BÚSQUEDA POR OPERARIO")

        todos_usuarios = auth.cargar_datos(persistencia.ARCHIVO_USUARIOS)

        if not todos_usuarios:
            print("❌ No hay usuarios registrados en el sistema.")
            return

        print("\n📋 Directorio de operarios:")
        for i, u in enumerate(todos_usuarios, 1):
            op_id = u.get("num_empleado", "")
            nombre_display = f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()

            if self.usuario_actual and op_id == self.usuario_actual.get("num_empleado"):
                print(f"   {i}. {nombre_display}  (ID: {op_id})  ⬅️  (ESTE ERES TÚ)")
            else:
                print(f"   {i}. {nombre_display}")

        try:
            seleccion = int(input("\nSeleccione un operario (número): ")) - 1
            if not (0 <= seleccion < len(todos_usuarios)):
                print("❌ Selección inválida")
                return

            usuario_sel = todos_usuarios[seleccion]
            op_seleccionado = usuario_sel.get("num_empleado", "")
            nombre_seleccionado = f"{usuario_sel.get('nombre', '')} {usuario_sel.get('apellidos', '')}".strip()

            print(f"\n📊 Datos registrados por: {nombre_seleccionado}")
            self._mostrar_separador()

            encontrados = 0
            registros_operario = []
            for indice, reg in enumerate(self.datos):
                if reg.get("registrado_por") == op_seleccionado:
                    encontrados += 1
                    registros_operario.append((indice, reg))
                    temp = reg.get('temp', reg.get('temperatura', 0))
                    fuente_reg = reg.get("fuente", "manual")
                    if fuente_reg == "api":
                        estado_edicion = " | 🤖 API (no editable)"
                    elif reg.get("editado"):
                        estado_edicion = " | 🔒 Ya editado"
                    else:
                        estado_edicion = " | ✏️ Editable"
                    print(f"{encontrados}. 📅 {reg.get('fecha')} | 📍 {reg.get('distrito', 'Desconocida')}{estado_edicion}")
                    print(f"   🌡️  T: {temp}°C | 💧 H: {reg.get('humedad', 0)}% | 💨 V: {reg.get('viento', 0)} km/h")
                    print("-" * 30)

            if encontrados == 0:
                print("ℹ️ Este operario no tiene registros en el sistema.")
            else:
                print(f"✅ Total de registros: {encontrados}")

            if self.usuario_actual and op_seleccionado == self.usuario_actual.get("num_empleado") and registros_operario:
                hay_editables = any(
                    r.get("fuente", "manual") != "api" and not r.get("editado")
                    for _, r in registros_operario
                )
                if hay_editables:
                    editar = input("\n¿Desea editar uno de sus registros? (s/n): ").strip().lower()
                    if editar == "s":
                        self._editar_registro_usuario(registros_operario)
                else:
                    print("\nℹ️ No tiene registros manuales editables.")
            elif self.usuario_actual and op_seleccionado != self.usuario_actual.get("num_empleado"):
                print("ℹ️ Solo el usuario que registró los datos puede editarlos.")

        except ValueError:
            print("❌ Ingrese un número válido")

    def _editar_registro_usuario(self, registros_operario):
        """
        Permite editar una sola vez un registro propio seleccionado desde la consulta por usuario.

        Args:
            registros_operario (list): Lista de tuplas (índice_real, registro) del operario actual.
        """
        try:
            seleccion = input("Seleccione el número del registro a editar (Enter para cancelar): ").strip()
            if not seleccion:
                return

            indice_lista = int(seleccion) - 1
            if not (0 <= indice_lista < len(registros_operario)):
                print("❌ Selección inválida.")
                return

            indice_real, registro = registros_operario[indice_lista]

            if not self.usuario_actual or registro.get("registrado_por") != self.usuario_actual.get("num_empleado"):
                print("❌ Solo puedes editar registros creados por tu propio usuario.")
                return

            if registro.get("fuente", "manual") == "api":
                print("❌ Los registros obtenidos desde la API no pueden editarse.")
                return

            if registro.get("editado"):
                print("❌ Este registro ya fue editado anteriormente y está bloqueado.")
                return

            confirmar = input("¿Confirmas que deseas editar este registro? Solo podrás hacerlo una vez (s/n): ").strip().lower()
            if confirmar != "s":
                print("❌ Edición cancelada.")
                return

            distrito_actual = registro.get("distrito", "")
            temp_actual = registro.get("temp", registro.get("temperatura", 0))
            humedad_actual = registro.get("humedad", 0)
            viento_actual = registro.get("viento", 0)
            lluvia_actual = registro.get("lluvia", 0.0)

            nuevo_distrito = input(f"Nuevo distrito (actual: {distrito_actual}) [Enter para mantener]: ").strip()
            distrito_final = distrito_actual
            if nuevo_distrito:
                distrito_normalizado = self._normalizar_distrito_oficial(nuevo_distrito)
                if not distrito_normalizado:
                    print("❌ El distrito introducido no es un distrito oficial de Madrid.")
                    return
                distrito_final = distrito_normalizado

            temp_final = self._pedir_numero_editable("Nueva temperatura", temp_actual, -20, 50)
            humedad_final = self._pedir_numero_editable("Nueva humedad", humedad_actual, 0, 100)
            viento_final = self._pedir_numero_editable("Nuevo viento", viento_actual, 0, 150)
            lluvia_final = self._pedir_numero_editable("Nueva lluvia", lluvia_actual, 0)

            registros_misma_clave = [
                r for i, r in enumerate(self.datos)
                if i != indice_real
                and r.get("fecha") == registro.get("fecha")
                and r.get("distrito", "").lower() == distrito_final.lower()
            ]
            if len(registros_misma_clave) >= 2:
                print("❌ No se puede guardar la edición: ya existen 2 registros para esa fecha y distrito.")
                return
            if any(r.get("fuente", "manual") == "manual" for r in registros_misma_clave):
                print("❌ No se puede guardar la edición porque crearía un registro manual duplicado.")
                return

            umbrales = persistencia.obtener_umbrales_alerta()
            datos_registro = {
                "temperatura": temp_final, "humedad": humedad_final,
                "viento": viento_final, "lluvia": lluvia_final
            }
            alertas_activas = alertas.evaluar_alertas(datos_registro, umbrales)

            self.datos[indice_real]["distrito"] = distrito_final
            self.datos[indice_real]["temp"] = temp_final
            self.datos[indice_real]["temperatura"] = temp_final
            self.datos[indice_real]["humedad"] = humedad_final
            self.datos[indice_real]["viento"] = viento_final
            self.datos[indice_real]["lluvia"] = lluvia_final
            self.datos[indice_real]["alertas"] = alertas_activas
            self.datos[indice_real]["editado"] = True

            if persistencia.actualizar_base_de_datos(self.datos):
                self.datos = self._cargar_datos()
                print("✅ Registro editado correctamente. Ya no podrá modificarse de nuevo.")
            else:
                print("❌ No se pudieron guardar los cambios.")

        except ValueError:
            print("❌ Has introducido un valor numérico no válido. No se guardaron cambios.")

    def _mostrar_datos_zona(self, zona):
        """
        Muestra todos los registros de una zona con sus alertas calculadas.

        Args:
            zona (str): Nombre del distrito a mostrar.
        """
        print(f"\n📊 Datos de: {zona}")
        self._mostrar_separador()

        encontrados = 0
        for reg in self.datos:
            if reg.get("distrito", "").lower() == zona.lower():
                encontrados += 1
                temp = reg.get('temp', reg.get('temperatura', 0))
                print(f"📅 {reg['fecha']}")
                print(f"   🌡️  Temperatura: {temp}°C")
                print(f"   💧 Humedad: {reg['humedad']}%")
                print(f"   💨 Viento: {reg['viento']} km/h")

                alertas_locales = self._analizar_alertas(temp, reg['humedad'], reg['viento'], reg.get('lluvia', 0))
                for alerta in alertas_locales:
                    print(f"   {alerta}")
                print()

        if encontrados == 0:
            print(f"❌ No hay datos para {zona}")
        else:
            print(f"✅ Total de registros: {encontrados}")

    def ver_historico(self):
        """
        Muestra el histórico completo con autoría detallada y opciones de filtrado y gráficas.
        """
        while True:
            self._mostrar_encabezado("📈 HISTÓRICO COMPLETO DE TODOS LOS DISTRITOS")
            self.datos = self._cargar_datos()

            if not self.datos:
                print("❌ No hay datos registrados en el sistema.")
                input("Presione Enter para continuar...")
                return

            print("1.Ver histórico completo")
            print("2.Ver gráfica del histórico")
            print("3.Volver al menú principal")
            self._mostrar_separador()

            seleccion_historico = input("Seleccione una opción (1-3): ").strip()

            if seleccion_historico == "2":
                self.generar_reporte_historico_visual()
                continue
            elif seleccion_historico == "3":
                break
            elif seleccion_historico != "1":
                print("Opción no válida. Por favor, seleccione 1, 2 o 3.")
                input("Presione Enter para intentarlo de nuevo...")
                continue

            print(f"\n{'='*50}")
            for reg in self.datos:
                temp = reg.get('temp', reg.get('temperatura', 0))
                operario_id = reg.get("registrado_por", "Desconocido")
                nombre_operario = auth.obtener_nombre_operario(operario_id)

                print(f"📅 {reg['fecha']} | 📍 {reg.get('distrito', 'Desconocida')}")
                print(f"   🌡️  T: {temp}°C | 💧 H: {reg.get('humedad', 0)}% | 💨 V: {reg.get('viento', 0)} km/h")

                alertas_locales = self._analizar_alertas(
                    temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0)
                )
                for alerta in alertas_locales:
                    print(f"   {alerta}")

                print(f"   {nombre_operario}")
                if reg.get("editado"):
                    print("   ⚠️ (Este registro ha sido editado/corregido)")

                self._mostrar_separador()

            print(f"✅ Total de registros en la base de datos: {len(self.datos)}")
            print(f"{'='*50}")

            self._mostrar_encabezado("OPCIONES DE HISTÓRICO:")
            print("1. 📊 Generar gráfica general")
            print("2. ⬅️  Volver al menú principal")

            opcion = input("¿Qué desea hacer ahora? (1-2): ").strip()

            if opcion == "1":
                self.generar_reporte_historico_visual()
            elif opcion == "2":
                break
            else:
                print("❌ Opción no válida. Por favor, seleccione 1 o 2.")
                input("Presione Enter para intentarlo de nuevo...")

    def mostrar_panel_alertas(self):
        """
        Panel de alertas activas con filtros por tipo y navegación avanzada.
        """
        while True:
            self._mostrar_encabezado("🚨 PANEL DE ALERTAS 🚨")
            self.datos = self._cargar_datos()
            alertas_encontradas = []

            for reg in self.datos:
                temp = reg.get('temp', reg.get('temperatura', 0))
                alertas_locales = self._analizar_alertas(
                    temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0)
                )
                if alertas_locales:
                    alertas_encontradas.append({
                        'zona': reg.get('distrito', 'Desconocida'),
                        'fecha': reg['fecha'],
                        'alertas': alertas_locales
                    })

            if not alertas_encontradas:
                print("\n✅ No hay alertas activas en ningún distrito en este momento.")
                input("\nPresione Enter para volver al menú principal...")
                break

            lista_tipos = [
                "Alerta de calor",
                "Alerta de frío",
                "Alerta de viento",
                "Alerta de humedad",
                "Alerta de lluvia"
            ]

            print(f"\n⚠️  Se detectaron {len(alertas_encontradas)} alertas en el histórico.")
            self._mostrar_encabezado("OPCIONES DEL PANEL:")
            print("1. 📅 Ver alertas de hoy")
            print("2. 📋 Historial de alertas")
            print("3. 🔍 Filtrar por tipo de alerta")
            print("4. ⬅️  Volver al menú principal")
            print("5. 🚪 Salir del sistema")

            opcion = input("\nSeleccione una opción (1-5): ").strip()

            if opcion == "1":
                self._mostrar_alertas_hoy(alertas_encontradas)
                if self._menu_post_alerta() == "menu_principal":
                    break

            elif opcion == "2":
                self._imprimir_alertas(alertas_encontradas)
                if self._menu_post_alerta() == "menu_principal":
                    break

            elif opcion == "3":
                accion = self._filtrar_y_mostrar_alertas(alertas_encontradas, lista_tipos)
                if accion == "menu_principal":
                    break

            elif opcion == "4":
                break

            elif opcion == "5":
                self.salir()
                exit()
            else:
                print("❌ Opción no válida.")

    def generar_reporte_distrito(self, distrito=None, pausa=True):
        """
        Genera el reporte analítico por distrito delegando en el módulo de analítica.

        Args:
            distrito (str, optional): Distrito para el reporte. Si es None, se solicita al usuario.
            pausa (bool): Si True, espera Enter antes de volver al menú.
        """
        self._mostrar_encabezado("REPORTE ANALÍTICO POR DISTRITO")
        if distrito:
            print(f"\nGenerando gráfica para el distrito: {distrito}")
        else:
            print("\nCargando datos y distritos disponibles...")

        analitica.generar_reporte_distrito_especifico(distrito)

        if pausa:
            input("\n\nPresione: Enter para volver al menú principal...")

    def _menu_consultar_zona(self):
        """
        Muestra las zonas disponibles y delega en _ofrecer_grafica_zona para la seleccionada.
        """
        self.zonas_validas = self._obtener_zonas()
        print("\nZonas disponibles:")
        for i, zona in enumerate(self.zonas_validas, 1):
            print(f"   {i}. {zona}")

        try:
            seleccion = int(input("\nSeleccione una zona (número): ")) - 1
            if 0 <= seleccion < len(self.zonas_validas):
                zona_seleccionada = self.zonas_validas[seleccion]
                self._ofrecer_grafica_zona(zona_seleccionada)
            else:
                print("Selección inválida")
        except ValueError:
            print("Ingrese un número válido")

    def _ofrecer_grafica_zona(self, zona):
        """
        Submenú de acciones para el distrito ya seleccionado: ver datos, gráfica o ambos.

        Args:
            zona (str): Nombre del distrito seleccionado.
        """
        while True:
            self._mostrar_encabezado(f"ACCIONES PARA {zona.upper()}:")
            print("1. Ver datos de este distrito")
            print("2. Generar gráfica de este distrito")
            print("3. Ver ambas")
            print("4. Volver al menú de consultas")

            opcion = input("Seleccione una opción (1-4): ").strip()

            if opcion == "1":
                self._mostrar_datos_zona(zona)
                input("\nPresione Enter para continuar...")
                return
            if opcion == "2":
                self.generar_reporte_distrito(distrito=zona, pausa=False)
                input("\nPresione Enter para continuar...")
                return
            if opcion == "3":
                self._mostrar_datos_zona(zona)
                self.generar_reporte_distrito(distrito=zona, pausa=False)
                input("\nPresione Enter para continuar...")
                return
            if opcion == "4":
                return

            print("Opción no válida.")

    def menu_principal(self):
        """
        Bucle principal de la aplicación que dirige el flujo entre todos los módulos.
        """
        while True:
            self._mostrar_encabezado("THE BIG DATA THEORY v2.0")
            print("1. 📋 Registrar Datos Climáticos")
            print("2. 📡 Obtener Datos desde API")
            print("3. 🔍 Consultar Datos Guardados")
            print("4. 📚 Ver Histórico (Todos los Distritos)")
            print("5. 📢 Alertas Activas")
            print("6. 📊 Análisis Avanzado")
            print("7. 🔙 Salir")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-7): ").strip()

            if opcion == "1":
                self.registrar_datos()
            elif opcion == "2":
                self.obtener_datos_api()
            elif opcion == "3":
                self.consultar_datos()
            elif opcion == "4":
                self.ver_historico()
            elif opcion == "5":
                self.mostrar_panel_alertas()
            elif opcion == "6":
                self.menu_analisis_avanzado()
            elif opcion == "7":
                self.salir()
                break
            else:
                print("Opción no válida. Intente de nuevo.")
                input("Presione Enter para continuar...")

    def menu_analisis_avanzado(self):
        """
        Menú de análisis avanzado con exportación, configuración, métricas, comparativa y scheduler.
        """
        while True:
            activo = sched_module.esta_activo()
            estado_sched = "🟢 ACTIVO" if activo else "🔴 DETENIDO"

            self._mostrar_encabezado("📊 ANÁLISIS AVANZADO")
            print("1. 📤 Exportar Datos (CSV)")
            print("2. 📊 Estadísticas Generales")
            print("3. 📋 Generar Reporte Automático")
            print("4. 💾 Backup de Datos")
            print("5. 🔄 Comparativa Manual vs. API")
            print(f"6. ⏱️  Scheduler de Ingesta Automática  [{estado_sched}]")
            print("7. ⬅️  Volver al menú principal")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-7): ").strip()

            if opcion == "1":
                self.exportar_datos_csv()
            elif opcion == "2":
                self.ver_metricas_sistema()
            elif opcion == "3":
                self.generar_reporte_automatico()
            elif opcion == "4":
                self.backup_datos()
            elif opcion == "5":
                self.ver_comparativa_manual_vs_api()
            elif opcion == "6":
                self.menu_scheduler()
            elif opcion == "7":
                break
            else:
                print("❌ Opción no válida.")
                input("Presione Enter para continuar...")

    def exportar_datos_csv(self):
        """
        Exporta el histórico de datos climáticos a un archivo CSV en la carpeta exports/.

        Returns:
            None. Crea el archivo y muestra la ruta al usuario.
        """
        self._mostrar_encabezado("📤 EXPORTAR DATOS A CSV")

        if not self.datos:
            print("❌ No hay datos para exportar.")
            input("Presione Enter para volver...")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"export_datos_climaticos_{timestamp}.csv"
        ruta_archivo = os.path.join("exports", nombre_archivo)

        os.makedirs("exports", exist_ok=True)

        try:
            with open(ruta_archivo, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['fecha', 'distrito', 'temperatura', 'humedad', 'viento', 'lluvia',
                             'condicion', 'registrado_por', 'editado']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for registro in self.datos:
                    fila = {
                        'fecha': registro.get('fecha', ''),
                        'distrito': registro.get('distrito', ''),
                        'temperatura': registro.get('temperatura', registro.get('temp', 0)),
                        'humedad': registro.get('humedad', 0),
                        'viento': registro.get('viento', 0),
                        'lluvia': registro.get('lluvia', 0),
                        'condicion': registro.get('condicion', ''),
                        'registrado_por': registro.get('registrado_por', ''),
                        'editado': 'Sí' if registro.get('editado', False) else 'No'
                    }
                    writer.writerow(fila)

            print(f"✅ Exportación completada exitosamente!")
            print(f"📁 Archivo guardado en: {ruta_archivo}")
            print(f"📊 Total de registros exportados: {len(self.datos)}")

        except Exception as e:
            print(f"❌ Error al exportar datos: {e}")

        input("\nPresione Enter para volver al menú de análisis...")

    def configurar_umbrales_alerta(self):
        """
        Permite configurar interactivamente los umbrales de alerta climática del sistema.
        """
        self._mostrar_encabezado("⚙️ CONFIGURACIÓN DE UMBRALES DE ALERTA")

        try:
            u = persistencia.obtener_umbrales_alerta()
            t_max = u.get("temperatura_max", u.get("temp_max_roja", 40.0))
            t_min = u.get("temperatura_min", u.get("temp_min_critica", -5.0))
            v_max = u.get("viento_max", 40.0)
            h_max = u.get("humedad_max", 95.0)
            ll_max = u.get("lluvia_max", u.get("lluvia_roja", 50.0))

            print("Umbrales actuales:")
            print(f"  🌡️ Temperatura máxima: {t_max}°C")
            print(f"  🥶 Temperatura mínima: {t_min}°C")
            print(f"  💨 Velocidad del viento: {v_max} km/h")
            print(f"  💧 Humedad máxima: {h_max}%")
            print(f"  🌧️ Lluvia máxima: {ll_max} mm")
            print()

            nuevos_umbrales = {
                "temperatura_max": self._pedir_numero_editable("Temperatura máxima de alerta", t_max, 20, 50),
                "temperatura_min": self._pedir_numero_editable("Temperatura mínima de alerta", t_min, -20, 10),
                "viento_max": self._pedir_numero_editable("Velocidad máxima del viento", v_max, 10, 200),
                "humedad_max": self._pedir_numero_editable("Humedad máxima", h_max, 50, 100),
                "lluvia_max": self._pedir_numero_editable("Lluvia máxima", ll_max, 5, 500),
            }

            if persistencia.actualizar_umbrales_alerta(nuevos_umbrales):
                print("✅ Umbrales de alerta actualizados correctamente!")
                print("\nNuevos umbrales:")
                print(f"  🌡️ Temperatura máxima: {nuevos_umbrales['temperatura_max']}°C")
                print(f"  🥶 Temperatura mínima: {nuevos_umbrales['temperatura_min']}°C")
                print(f"  💨 Velocidad del viento: {nuevos_umbrales['viento_max']} km/h")
                print(f"  💧 Humedad máxima: {nuevos_umbrales['humedad_max']}%")
                print(f"  🌧️ Lluvia máxima: {nuevos_umbrales['lluvia_max']} mm")
            else:
                print("❌ Error al guardar los nuevos umbrales.")

        except Exception as e:
            print(f"❌ Error en la configuración: {e}")

        input("\nPresione Enter para volver al menú de análisis...")

    def ver_metricas_sistema(self):
        """
        Muestra métricas y estadísticas generales del sistema: registros, temperaturas y alertas.
        """
        self._mostrar_encabezado("📈 MÉTRICAS DEL SISTEMA")

        if not self.datos:
            print("❌ No hay datos registrados en el sistema.")
            input("Presione Enter para volver...")
            return

        total_registros = len(self.datos)
        distritos = set(reg.get('distrito', '') for reg in self.datos if reg.get('distrito'))
        fechas = set(reg.get('fecha', '') for reg in self.datos if reg.get('fecha'))
        usuarios = set(reg.get('registrado_por', '') for reg in self.datos if reg.get('registrado_por'))

        temperaturas = [
            reg.get('temperatura', reg.get('temp', 0))
            for reg in self.datos
            if reg.get('temperatura') or reg.get('temp')
        ]
        temp_promedio = sum(temperaturas) / len(temperaturas) if temperaturas else 0
        temp_max = max(temperaturas) if temperaturas else 0
        temp_min = min(temperaturas) if temperaturas else 0

        total_alertas = sum(len(reg.get('alertas', [])) for reg in self.datos)

        print("📊 ESTADÍSTICAS GENERALES")
        print("=" * 40)
        print(f"📝 Total de registros: {total_registros}")
        print(f"🏙️  Distritos registrados: {len(distritos)}")
        print(f"📅 Días con datos: {len(fechas)}")
        print(f"👥 Usuarios activos: {len(usuarios)}")
        print()

        print("🌡️ ESTADÍSTICAS TÉRMICAS")
        print("=" * 40)
        print(f"📊 Temperatura promedio: {temp_promedio:.1f}°C")
        print(f"🔥 Temperatura máxima: {temp_max:.1f}°C")
        print(f"❄️  Temperatura mínima: {temp_min:.1f}°C")
        print()

        print("🚨 ESTADÍSTICAS DE ALERTAS")
        print("=" * 40)
        print(f"⚠️  Total de alertas generadas: {total_alertas}")
        if total_registros > 0:
            print(f"📈 Promedio de alertas por registro: {total_alertas/total_registros:.2f}")
        else:
            print("📈 Promedio de alertas por registro: 0.00")
        print()

        if distritos:
            print("🏆 TOP DISTRITOS POR REGISTROS")
            print("=" * 40)
            distrito_counts = {}
            for reg in self.datos:
                d = reg.get('distrito', 'Sin distrito')
                distrito_counts[d] = distrito_counts.get(d, 0) + 1

            sorted_distritos = sorted(distrito_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (d, count) in enumerate(sorted_distritos[:5], 1):
                print(f"{i}. {d}: {count} registros")

        input("\nPresione Enter para volver al menú de análisis...")

    def generar_reporte_automatico(self):
        """
        Genera un archivo de texto con resumen estadístico del sistema y lo guarda en reports/.
        """
        self._mostrar_encabezado("📋 REPORTE AUTOMÁTICO DEL SISTEMA")

        if not self.datos:
            print("❌ No hay datos para generar el reporte.")
            input("Presione Enter para volver...")
            return

        os.makedirs("reports", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"reporte_sistema_{timestamp}.txt"
        ruta_archivo = os.path.join("reports", nombre_archivo)

        try:
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write("REPORTE AUTOMÁTICO - THE BIG DATA THEORY\n")
                f.write("=" * 60 + "\n")
                f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                usuario_nombre = self.usuario_actual.get('nombre', 'Desconocido') if self.usuario_actual else 'Sistema'
                f.write(f"Usuario: {usuario_nombre}\n\n")

                total_registros = len(self.datos)
                distritos = set(reg.get('distrito', '') for reg in self.datos if reg.get('distrito'))
                fechas = set(reg.get('fecha', '') for reg in self.datos if reg.get('fecha'))

                f.write("ESTADÍSTICAS GENERALES\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total de registros: {total_registros}\n")
                f.write(f"Distritos registrados: {len(distritos)}\n")
                f.write(f"Días con datos: {len(fechas)}\n\n")

                temperaturas = [
                    reg.get('temperatura', reg.get('temp', 0))
                    for reg in self.datos
                    if reg.get('temperatura') or reg.get('temp')
                ]
                if temperaturas:
                    f.write("ESTADÍSTICAS TÉRMICAS\n")
                    f.write("-" * 30 + "\n")
                    f.write(f"Temperatura promedio: {sum(temperaturas)/len(temperaturas):.1f}°C\n")
                    f.write(f"Temperatura máxima: {max(temperaturas):.1f}°C\n")
                    f.write(f"Temperatura mínima: {min(temperaturas):.1f}°C\n\n")

                total_alertas = sum(len(reg.get('alertas', [])) for reg in self.datos)
                f.write("ESTADÍSTICAS DE ALERTAS\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total de alertas generadas: {total_alertas}\n")
                if total_registros > 0:
                    f.write(f"Promedio de alertas por registro: {total_alertas/total_registros:.2f}\n\n")

                f.write("ÚLTIMOS 10 REGISTROS\n")
                f.write("-" * 30 + "\n")
                registros_ordenados = sorted(self.datos, key=lambda x: x.get('fecha', ''), reverse=True)
                for i, reg in enumerate(registros_ordenados[:10], 1):
                    temp = reg.get('temperatura', reg.get('temp', 0))
                    f.write(f"{i}. {reg.get('fecha', '')} - {reg.get('distrito', '')}: {temp:.1f}°C\n")

                f.write("\n" + "=" * 60 + "\n")
                f.write("Fin del reporte\n")

            print("✅ Reporte generado exitosamente!")
            print(f"📁 Archivo guardado en: {ruta_archivo}")
            print("\n📋 RESUMEN DEL REPORTE:")
            print(f"   📊 Total registros: {total_registros}")
            print(f"   🏙️ Distritos: {len(distritos)}")
            print(f"   🚨 Alertas totales: {total_alertas}")

        except Exception as e:
            print(f"❌ Error al generar el reporte: {e}")

        input("\nPresione Enter para volver al menú de análisis...")

    def backup_datos(self):
        """
        Crea una copia de seguridad del archivo de datos en la carpeta backups/.
        """
        self._mostrar_encabezado("💾 BACKUP DE DATOS")

        if not os.path.exists(persistencia.ARCHIVO_JSON):
            print("❌ No hay archivo de datos para hacer backup.")
            input("Presione Enter para volver...")
            return

        os.makedirs("backups", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_backup = f"backup_datos_climaticos_{timestamp}.json"
        ruta_backup = os.path.join("backups", nombre_backup)

        try:
            shutil.copy2(persistencia.ARCHIVO_JSON, ruta_backup)

            tamano_bytes = os.path.getsize(ruta_backup)
            tamano_mb = tamano_bytes / (1024 * 1024)

            print("✅ Backup creado exitosamente!")
            print(f"📁 Archivo: {ruta_backup}")
            print(f"📏 Tamaño: {tamano_mb:.2f} MB")
            print(f"📊 Registros: {len(self.datos)}")

            backups = [f for f in os.listdir("backups") if f.startswith("backup_") and f.endswith(".json")]
            print(f"\n📂 Total de backups: {len(backups)}")

        except Exception as e:
            print(f"❌ Error al crear el backup: {e}")

        input("\nPresione Enter para volver al menú de análisis...")

    def generar_reporte_historico_visual(self):
        """
        Genera la gráfica general del histórico delegando en el módulo de analítica.
        """
        self._mostrar_encabezado("📊 GRÁFICA GENERAL DEL HISTÓRICO")
        analitica.generar_reporte_visual_pro()
        input("\n\nPresione Enter para volver al histórico...")

    def _imprimir_alertas(self, lista_alertas):
        """
        Imprime las alertas de forma estructurada por zona y fecha.

        Args:
            lista_alertas (list): Lista de dicts con zona, fecha y alertas.
        """
        print("\n" + "="*50)
        for item in lista_alertas:
            print(f"📍 ZONA: {item['zona']} | 📅 FECHA: {item['fecha']}")
            print("-" * 45)
            for alerta in item['alertas']:
                print(f"  → {alerta}")
        print("="*50)

    def _mostrar_alertas_hoy(self, lista_alertas):
        """
        Muestra solo las alertas del día en curso.

        Args:
            lista_alertas (list): Lista de dicts con zona, fecha y alertas.
        """
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        alertas_hoy = [item for item in lista_alertas if item['fecha'] == fecha_hoy]

        print("\n" + "="*50)
        print(f"📅 ALERTAS DEL DIA: {fecha_hoy}")
        print("="*50)

        if not alertas_hoy:
            print(f"\n✅ No hay alertas registradas para hoy ({fecha_hoy})")
        else:
            for item in alertas_hoy:
                print(f"📍 ZONA: {item['zona']} | 📅 FECHA: {item['fecha']}")
                print("-" * 45)
                for alerta in item['alertas']:
                    print(f"  → {alerta}")
        print("="*50)

    def _filtrar_y_mostrar_alertas(self, alertas_encontradas, lista_tipos):
        """
        Muestra el submenú de tipos de alerta y filtra las alertas por el tipo seleccionado.

        Args:
            alertas_encontradas (list): Lista completa de alertas detectadas.
            lista_tipos (list): Tipos de alerta disponibles para filtrar.

        Returns:
            str: "panel_alertas" o "menu_principal" según la navegación posterior.
        """
        self._mostrar_encabezado("🚨 TIPOS DE ALERTA 🚨")

        palabras_clave = {
            "Alerta de calor": ["calor", "temperatura elevada"],
            "Alerta de frío": ["frío", "helada", "frio"],
            "Alerta de viento": ["viento"],
            "Alerta de humedad": ["humedad", "sequedad"],
            "Alerta de lluvia": ["lluvia"]
        }

        for i, tipo in enumerate(lista_tipos, 1):
            claves = palabras_clave[tipo]
            contador = 0
            for item in alertas_encontradas:
                for alerta in item['alertas']:
                    if any(clave in alerta.lower() for clave in claves):
                        contador += 1
                        break

            print(f"   {i}. {tipo} ({contador} detectadas)")

        opcion_volver = len(lista_tipos) + 1
        print(f"   {opcion_volver}. 🔙 Volver al panel de alertas")

        try:
            entrada = input(f"\nSeleccione la alerta que desea investigar (1-{opcion_volver}) [o 'c' para cancelar]: ").strip()

            if entrada.lower() == 'c':
                return "panel_alertas"

            seleccion = int(entrada)

            if seleccion == opcion_volver:
                return "panel_alertas"

            elif 1 <= seleccion <= len(lista_tipos):
                alerta_buscada = lista_tipos[seleccion - 1]
                claves = palabras_clave[alerta_buscada]

                filtradas = []
                for item in alertas_encontradas:
                    for alerta in item['alertas']:
                        if any(clave in alerta.lower() for clave in claves):
                            filtradas.append(item)
                            break

                print(f"\n📊 Resultados filtrados para: {alerta_buscada}")
                self._imprimir_alertas(filtradas)

                return self._menu_post_alerta()
            else:
                print("❌ Selección inválida.")
                return "panel_alertas"

        except ValueError:
            print("❌ Ingrese un número válido.")
            return "panel_alertas"

    def _menu_post_alerta(self):
        """
        Submenú de navegación posterior al mostrar alertas.

        Returns:
            str: "panel_alertas" para volver al panel, "menu_principal" para salir.
        """
        while True:
            self._mostrar_encabezado("OPCIONES POSTERIORES:")
            print("1. 🔙 Volver al panel de alertas")
            print("2. ⬅️  Volver al menú principal")
            print("3. 🚪 Salir del sistema")

            post_opcion = input("¿Qué desea hacer ahora? (1-3): ").strip()

            if post_opcion == "1":
                return "panel_alertas"
            elif post_opcion == "2":
                return "menu_principal"
            elif post_opcion == "3":
                self.salir()
                exit()
            else:
                print("❌ Opción no válida.")

    def ver_comparativa_manual_vs_api(self):
        """
        Muestra la tabla comparativa de temperaturas entre registros manuales y de API
        para el mismo distrito y fecha, marcando discrepancias significativas.
        """
        self._mostrar_encabezado("🔄 COMPARATIVA MANUAL vs. API")
        self.datos = self._cargar_datos()

        if not self.datos:
            print("❌ No hay datos registrados en el sistema.")
            input("Presione Enter para volver...")
            return

        discrepancias = comparativa.detectar_discrepancias(self.datos)

        if not discrepancias:
            print("\nℹ️  No hay zonas con registros de ambas fuentes (manual + API) para comparar.")
            print("    Registre datos de forma manual y también desde la API en el mismo distrito y fecha.")
            input("\nPresione Enter para volver...")
            return

        comparativa.mostrar_tabla_comparativa(discrepancias)

        conflictos = [d for d in discrepancias if d["conflicto"]]
        if conflictos:
            print(f"\n⚠️  Se encontraron {len(conflictos)} discrepancia(s) con diferencia ≥ 2°C.")
            print("   Revisa los registros marcados como CONFLICTO para verificar la fuente más fiable.")

        input("\nPresione Enter para volver al menú de análisis...")

    def menu_scheduler(self):
        """
        Panel de control del scheduler de ingesta automática: iniciar, detener y configurar intervalo.
        """
        while True:
            activo = sched_module.esta_activo()
            intervalo = sched_module.obtener_intervalo()
            proximo = sched_module.obtener_proximo_disparo()
            resumen = sched_module.obtener_resumen()

            self._mostrar_encabezado("⏱️ SCHEDULER DE INGESTA AUTOMÁTICA")

            estado_txt = "🟢 ACTIVO" if activo else "🔴 DETENIDO"
            print(f"\n  Estado:    {estado_txt}")
            print(f"  Intervalo: cada {intervalo} minutos")
            print(f"  Horario activo: {sched_module._hora_inicio}h – {sched_module._hora_fin}h")
            if proximo:
                print(f"  Próxima ejecución: {proximo.strftime('%H:%M:%S')}")

            if resumen["ultima_ejecucion"]:
                ue = resumen["ultima_ejecucion"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n  Último ciclo: {ue}")
                print(f"  ✅ Guardados : {resumen['guardados']}")
                print(f"  ⏭️  Omitidos  : {resumen['omitidos']}  (ya existían)")
                print(f"  ❌ Errores   : {resumen['errores']}")
                print(f"  🏙️  Distritos : {resumen['total_distritos']}")
            else:
                print("\n  (Sin ejecuciones registradas en esta sesión)")

            print()
            print("1. ▶️  Iniciar ingesta automática")
            print("2. ⏹️  Detener ingesta automática")
            print("3. ⚙️  Cambiar intervalo")
            print("4. 🔍 Ver detalle de errores")
            print("5. ⬅️  Volver al menú de análisis")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-5): ").strip()

            if opcion == "1":
                if activo:
                    print("⚠️  El scheduler ya está activo.")
                else:
                    try:
                        entrada = input(f"Intervalo en minutos (5-120) [Enter para {intervalo}]: ").strip()
                        mins = int(entrada) if entrada else intervalo
                        sched_module.iniciar(mins)
                        print(f"\n✅ Scheduler iniciado. Primera ingesta arrancando ahora.")
                        print(f"   Siguiente ciclo en {sched_module.obtener_intervalo()} minutos.")
                    except ValueError:
                        print("❌ Introduce un número válido.")
                input("\nPresione Enter para continuar...")

            elif opcion == "2":
                if not activo:
                    print("⚠️  El scheduler ya está detenido.")
                else:
                    sched_module.detener()
                    print("✅ Scheduler detenido. La ingesta automática se ha pausado.")
                input("\nPresione Enter para continuar...")

            elif opcion == "3":
                try:
                    entrada = input(f"Nuevo intervalo en minutos (5-120) [actual: {intervalo}]: ").strip()
                    if entrada:
                        mins = int(entrada)
                        if activo:
                            sched_module.iniciar(mins)
                            print(f"✅ Intervalo cambiado a {sched_module.obtener_intervalo()} min (scheduler reiniciado).")
                        else:
                            sched_module.configurar_intervalo(mins)
                            print(f"✅ Intervalo configurado a {sched_module.obtener_intervalo()} min para el próximo inicio.")
                except ValueError:
                    print("❌ Introduce un número válido.")
                input("\nPresione Enter para continuar...")

            elif opcion == "4":
                self._ver_detalle_errores_scheduler()

            elif opcion == "5":
                break
            else:
                print("❌ Opción no válida.")

    def _ver_detalle_errores_scheduler(self):
        """
        Muestra los errores de conexión recientes del scheduler con sugerencias de solución.
        """
        self._mostrar_encabezado("🔍 DETALLE DE ERRORES RECIENTES")
        errores = sched_module.obtener_errores_recientes()

        if not errores:
            print("\n✅ No hay errores recientes registrados.")
            print("   (Los errores se registran durante la ingesta automática)")
        else:
            print(f"\n⚠️  {len(errores)} error(es) reciente(s):\n")
            for i, err in enumerate(errores, 1):
                print(f"  {i}. [{err['timestamp']}]  Distrito: {err['distrito']}")
                print(f"     🔴 Código: {err['codigo']}  —  {err['mensaje']}")
                print(f"     💡 Sugerencia: {err['sugerencia']}")
                print()

        input("Presione Enter para volver al scheduler...")

    def salir(self):
        """
        Detiene el scheduler si está activo y muestra el mensaje de cierre del sistema.
        """
        if sched_module.esta_activo():
            sched_module.detener()
        self._mostrar_encabezado("🚪 CERRANDO SISTEMA")
        print("\n✅ Todos los datos han sido guardados correctamente")
        print("🌍 ¡Gracias por usar The Big Data Theory!")
        print("👋 ¡Hasta pronto!\n")
