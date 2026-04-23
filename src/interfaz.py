"""
Módulo de Interfaz para PyClima - Sistema de Monitoreo Climático
Interfaz intuitiva y robusta para interacción del usuario
"""

import json
import os
import validaciones
import alertas
import persistencia
import auth
import analitica
from datetime import datetime

class InterfazPyClima:
    
    # Constructor: Inicializa la interfaz cargando datos y configurando usuario actual
    def __init__(self, ruta_datos=persistencia.ARCHIVO_JSON, usuario_actual=None):
        self.ruta_datos = ruta_datos
        self.datos = self._cargar_datos()
        self.zonas_validas = self._obtener_zonas()
        self.usuario_actual = usuario_actual
        
    # Carga el histórico completo desde la persistencia
    def _cargar_datos(self):
        return persistencia.leer_historico()
    
    # Extrae lista única de distritos del histórico
    def _obtener_zonas(self):
        zonas = set()
        for reg in self.datos:
            if "distrito" in reg:
                zonas.add(reg["distrito"])
        return sorted(list(zonas)) if zonas else []
    
    # Verifica si ya existe un registro con la misma fecha y distrito
    def _validar_duplicado(self, fecha, distrito):
        for reg in self.datos:
            if reg.get("fecha") == str(fecha) and reg.get("distrito", "").lower() == distrito.lower():
                return True
        return False
    
    # Evalúa alertas climáticas usando los umbrales del sistema
    def _analizar_alertas(self, temperatura, humedad, viento, lluvia=0):
        umbrales = persistencia.obtener_umbrales_alerta()
        datos_registro = {
            "temperatura": temperatura,
            "humedad": humedad,
            "viento": viento,
            "lluvia": lluvia
        }
        return alertas.evaluar_alertas(datos_registro, umbrales)
    
    # Imprime encabezado con título formateado
    def _mostrar_encabezado(self, titulo):
        print("\n" + "="*50)
        print(f"  {titulo}")
        print("="*50)
    
    # Imprime línea separadora visual
    def _mostrar_separador(self):
        print("-" * 50)

    # Normaliza y valida nombre de distrito contra la lista oficial
    def _normalizar_distrito_oficial(self, distrito):
        distritos_oficiales = persistencia.obtener_distritos_permitidos()
        mapa_distritos = {item.lower(): item for item in distritos_oficiales}
        return mapa_distritos.get(distrito.strip().lower())

    # Solicita número editable con validación de rango (mín/máx)
    def _pedir_numero_editable(self, etiqueta, valor_actual, minimo=None, maximo=None):
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

    # Flujo completo: solicita datos climáticos, valida, evalúa alertas y guarda
    def registrar_datos(self):
        self._mostrar_encabezado("📝 REGISTRAR NUEVOS DATOS CLIMÁTICOS")
        self.datos = self._cargar_datos()
        
        while True:
            try:
                # Paso 1: Captura fecha del registro
                print("\n[1/6] FECHA DEL REGISTRO")
                fecha = validaciones.validar_fecha()
                
                # Paso 2: Captura zona/distrito
                print("\n[2/6] ZONA/DISTRITO")
                distrito = validaciones.validar_zona()
                if not distrito: return
                
                # Paso 3: Valida que no exista registro duplicado
                if self._validar_duplicado(fecha, distrito):
                    print(f"⚠️  Ya existe un registro para {distrito} en {fecha}. No se aceptan duplicados.")
                    if input("¿Desea ingresar datos nuevamente? (s/n): ").lower() != 's': return
                    continue
                
                # Paso 4: Captura temperatura
                print("\n[3/6] TEMPERATURA")
                temperatura = validaciones.validar_temperatura()
                
                # Paso 5: Captura humedad
                print("\n[4/6] HUMEDAD")
                humedad = validaciones.validar_humedad()
                
                # Paso 6: Captura velocidad del viento
                print("\n[5/6] VELOCIDAD DEL VIENTO")
                viento = validaciones.validar_viento()

                # Paso 7: Captura precipitaciones
                print("\n[6/6] PRECIPITACIONES (LLUVIA)")
                lluvia = validaciones.validar_lluvia()

                print("\n" + "="*50)
                print("✅ DATOS VALIDADOS EXITOSAMENTE")
                print("="*50)
                
                umbrales = persistencia.obtener_umbrales_alerta()
                datos_registro = {"temperatura": temperatura, "humedad": humedad, "viento": viento, "lluvia": lluvia}
                alertas_activas = alertas.evaluar_alertas(datos_registro, umbrales)
                
                # --- PASO 1: MOSTRAR ALERTAS ANTES DE GUARDAR ---
                if alertas_activas:
                    print("\n🚨 ALERTAS PRELIMINARES DETECTADAS:")
                    for alerta in alertas_activas: 
                        print(f"   {alerta}")
                else:
                    print("\n✅ Niveles climáticos normales (Sin alertas)")
                print("-" * 50)
                # ------------------------------------------------

                nuevo_registro = {
                    "fecha": fecha,
                    "distrito": distrito,
                    "temperatura": temperatura, 
                    "temp": temperatura,        
                    "humedad": humedad,
                    "viento": viento,
                    "lluvia": 0.0,
                    "alertas": alertas_activas,
                    "registrado_por": self.usuario_actual["num_empleado"] if self.usuario_actual else "Desconocido",
                    "editado": False
                }
                
                # Aquí el sistema saltará a persistencia.py y hará la pregunta de confirmación
                exito = persistencia.registrar_nuevo_dato(nuevo_registro)
                
                if exito:
                    self._mostrar_separador()
                    if input("\n¿Registrar otro dato? (s/n): ").strip().lower() != 's': return
                else:
                    return
                    
            except KeyboardInterrupt:
                print("\n\n❌ Registro cancelado por el usuario")
                return
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                if input("¿Desea ingresar los datos nuevamente? (s/n): ").lower() != 's': return
    
    def obtener_datos_api(self):
        """
        Obtiene datos climáticos desde WeatherAPI para un distrito seleccionado.
        
        Flujo:
        1. Muestra lista de distritos de Madrid desde config.json
        2. Usuario selecciona uno
        3. Consulta WeatherAPI
        4. Muestra datos en pantalla con alertas
        5. Pide confirmación antes de guardar
        """
        import Api  # Importamos el módulo de API aquí
        
        self._mostrar_encabezado("📡 OBTENER DATOS DESDE API METEOROLÓGICA")
        
        # PASO 1: Obtener lista de distritos desde config.json
        distritos = persistencia.obtener_distritos_permitidos()
        if not distritos:
            print("❌ No se encontraron distritos configurados en config.json")
            input("Presione Enter para volver...")
            return
        
        # PASO 2: Mostrar lista y pedir selección
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
        
        # PASO 3: Traer datos de la API
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
        
        # PASO 4: Mostrar datos en pantalla
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
        
        # Mostrar alertas si hay
        if registro_api['alertas']:
            print("\n🚨 ALERTAS DETECTADAS:")
            for alerta in registro_api['alertas']:
                print(f"   {alerta}")
        else:
            print("\n✅ No hay alertas")
        
        print("="*50)
        
        # PASO 5: Pedir confirmación
        confirmacion = input("\n¿Desea guardar estos datos? (s/n): ").strip().lower()
        
        if confirmacion == 's':
            # PASO 6: Guardar en JSON
            try:
                exito = persistencia.registrar_nuevo_dato(registro_api)
                if exito:
                    print("✅ ¡Datos guardados exitosamente!")
                    self.datos = self._cargar_datos()  # Refrescar datos
                else:
                    print("❌ No se pudieron guardar los datos")
            except Exception as error:
                print(f"❌ Error al guardar: {error}")
        else:
            print("❌ Operación cancelada. Los datos no se guardaron.")
        
        input("\nPresione Enter para volver al menú principal...")
    
    # Menú avanzado de consultas con filtros y opciones posteriores
    def consultar_datos(self):
        while True:
            self._mostrar_encabezado("📊 CONSULTAR DATOS 📊 ")
            self.datos = self._cargar_datos() # Refrescar datos
            
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
                break # Sale del bucle y vuelve al menú principal
            else:
                print("❌ Opción no válida.")
                continue # Vuelve a mostrar el menú de consultas
                
            # -----------------------------------------
            # OPCIONES POSTERIORES (Según el esquema)
            # -----------------------------------------
            if opcion in ["1", "2", "3"]:
                print("\n" + "="*50)
                self._mostrar_encabezado("OPCIONES POSTERIORES:")
                print("1. Hacer otra consulta")
                print("2. Volver al menú principal")
                print("3. Salir del sistema")
                
                post_opcion = input("¿Qué desea hacer ahora? (1-3): ").strip()
                
                if post_opcion == "2":
                    break # Rompe el bucle de consultas, vuelve al principal
                elif post_opcion == "3":
                    self.salir()
                    exit() # Cierra el programa por completo
                # Si elige "1", el bucle while True vuelve a empezar solo

    def _menu_consultar_fecha(self):
        """Lógica extraída para buscar por fecha exacta"""
        print("\n📅 BÚSQUEDA POR FECHA")
        # ¡Aquí usamos tu módulo DEV 2 para garantizar el formato AAAA-MM-DD!
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

                alertas_locales = self._analizar_alertas(temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0))
                for alerta in alertas_locales: 
                    print(f"   {alerta}")
                print("-" * 30)
                
        if encontrados == 0:
            print(f"❌ No hay datos registrados para la fecha {fecha_buscada}")
        else:
            print(f"✅ Total de registros encontrados: {encontrados}")
    
    def _menu_consultar_usuario(self):
        """Lógica extraída para buscar por operario usando el traductor"""
        print("\n👤 BÚSQUEDA POR OPERARIO")
        
        # 1. Escanear el JSON para ver quién ha participado
        operarios_ids = set()
        for reg in self.datos:
            if "registrado_por" in reg:
                operarios_ids.add(reg["registrado_por"])
                
        lista_operarios = list(operarios_ids)
        
        if not lista_operarios:
            print("❌ No hay registros asociados a ningún operario.")
            return

        # 2. Mostrar el directorio usando la función traductora de auth.py
        print("\n📋 Directorio de operarios con registros:")
        for i, op_id in enumerate(lista_operarios, 1):
            nombre_completo = auth.obtener_nombre_operario(op_id)
            
            # --- NUEVA LÓGICA DE RESALTADO ---
            # Verificamos si hay un usuario logueado y si su número coincide con el de la lista
            if self.usuario_actual and op_id == self.usuario_actual.get("num_empleado"):
                print(f"   {i}. {nombre_completo}  ⬅️  (ESTE ERES TÚ)")
            else:
                print(f"   {i}. {nombre_completo}")
            
        # 3. Selección y filtrado
        try:
            seleccion = int(input("\nSeleccione un operario (número): ")) - 1
            if 0 <= seleccion < len(lista_operarios):
                op_seleccionado = lista_operarios[seleccion]
                nombre_seleccionado = auth.obtener_nombre_operario(op_seleccionado)
                
                print(f"\n📊 Datos registrados por: {nombre_seleccionado}")
                self._mostrar_separador()
                
                encontrados = 0
                registros_operario = []
                for indice, reg in enumerate(self.datos):
                    if reg.get("registrado_por") == op_seleccionado:
                        encontrados += 1
                        registros_operario.append((indice, reg))
                        temp = reg.get('temp', reg.get('temperatura', 0))
                        estado_edicion = " | 🔒 Ya editado" if reg.get("editado") else " | ✏️ Editable"
                        print(f"{encontrados}. 📅 {reg.get('fecha')} | 📍 {reg.get('distrito', 'Desconocida')}{estado_edicion}")
                        print(f"   🌡️  T: {temp}°C | 💧 H: {reg.get('humedad', 0)}% | 💨 V: {reg.get('viento', 0)} km/h")
                        print("-" * 30)
                        
                print(f"✅ Total de registros de este operario: {encontrados}")

                if self.usuario_actual and op_seleccionado == self.usuario_actual.get("num_empleado") and registros_operario:
                    editar = input("\n¿Desea editar uno de sus registros? (s/n): ").strip().lower()
                    if editar == "s":
                        self._editar_registro_usuario(registros_operario)
                elif self.usuario_actual and op_seleccionado != self.usuario_actual.get("num_empleado"):
                    print("ℹ️ Solo el usuario que registró los datos puede editarlos.")
            else:
                print("❌ Selección inválida")
        except ValueError:
            print("❌ Ingrese un número válido")

    def _editar_registro_usuario(self, registros_operario):
        """Permite editar una sola vez un registro propio seleccionado desde la consulta por usuario."""
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

            for i, reg in enumerate(self.datos):
                if i != indice_real and reg.get("fecha") == registro.get("fecha") and reg.get("distrito", "").lower() == distrito_final.lower():
                    print("❌ No se puede guardar la edición porque crearía un registro duplicado para esa fecha y distrito.")
                    return

            umbrales = persistencia.obtener_umbrales_alerta()
            datos_registro = {"temperatura": temp_final, "humedad": humedad_final, "viento": viento_final, "lluvia": lluvia_final}
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
        """Muestra todos los datos de una zona iterando sobre la LISTA"""
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
                for alerta in alertas_locales: print(f"   {alerta}")
                print()
        
        if encontrados == 0: print(f"❌ No hay datos para {zona}")
        else: print(f"✅ Total de registros: {encontrados}")
    
    def ver_historico(self):
        """Muestra histórico completo con autoría detallada y opciones de filtrado"""
        while True:
            self._mostrar_encabezado("📈 HISTÓRICO COMPLETO DE TODAS LAS ZONAS")
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
                
                # --- TRADUCTOR DE IDENTIDADES EN ACCIÓN ---
                operario_id = reg.get("registrado_por", "Desconocido")
                nombre_operario = auth.obtener_nombre_operario(operario_id)
                
                print(f"📅 {reg['fecha']} | 📍 {reg.get('distrito', 'Desconocida')}")
                print(f"   🌡️  T: {temp}°C | 💧 H: {reg.get('humedad', 0)}% | 💨 V: {reg.get('viento', 0)} km/h")

                alertas_locales = self._analizar_alertas(temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0))
                for alerta in alertas_locales:
                    print(f"   {alerta}")

                # Imprimimos el autor
                print(f"   {nombre_operario}")
                # Avisamos si el registro sufrió una corrección
                if reg.get("editado"):
                    print("   ⚠️ (Este registro ha sido editado/corregido)")
                    
                self._mostrar_separador()
            
            print(f"✅ Total de registros en la base de datos: {len(self.datos)}")
            print(f"{'='*50}")
            
            # --- SUBMENÚ DE NAVEGACIÓN Y FILTROS (Punto 7) ---
            self._mostrar_encabezado("OPCIONES DE HISTÓRICO:")
            print("1. 🔍 Aplicar filtros de búsqueda (Zona / Fecha / Usuario)")
            print("2. 📊 Generar gráfica general")
            print("3. ⬅️  Volver al menú principal")
            
            opcion = input("¿Qué desea hacer ahora? (1-3): ").strip()
            
            if opcion == "1":
                self.consultar_datos()
                break # Al salir de las consultas, volvemos al menú principal para no imprimir el histórico gigante otra vez
            elif opcion == "2":
                self.generar_reporte_historico_visual()
            elif opcion == "3":
                break
            else:
                print("❌ Opción no válida. Por favor, seleccione 1, 2 o 3.")
                input("Presione Enter para intentarlo de nuevo...")

    def mostrar_panel_alertas(self):
        """Panel de alertas activas con filtros y navegación avanzada (Fase D)"""
        while True:
            self._mostrar_encabezado("🚨 PANEL DE ALERTAS 🚨")
            self.datos = self._cargar_datos() # Refrescar
            alertas_encontradas = []

            # 1. Recopilamos las alertas actuales
            for reg in self.datos:
                temp = reg.get('temp', reg.get('temperatura', 0))
                alertas_locales = self._analizar_alertas(temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0))
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

            # 2. Definimos las categorías fijas de alerta basadas en los umbrales
            lista_tipos = [
                "Alerta de calor",
                "Alerta de frío",
                "Alerta de viento",
                "Alerta de humedad",
                "Alerta de lluvia"
            ]

            # 3. Mostrar menú principal del panel de alertas
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
                # Mostramos menú posterior y comprobamos si quiere volver al menú principal
                if self._menu_post_alerta() == "menu_principal": break

            elif opcion == "2":
                self._imprimir_alertas(alertas_encontradas)
                # Mostramos menú posterior y comprobamos si quiere volver al menú principal
                if self._menu_post_alerta() == "menu_principal": break

            elif opcion == "3":
                accion = self._filtrar_y_mostrar_alertas(alertas_encontradas, lista_tipos)
                if accion == "menu_principal": break

            elif opcion == "4":
                break # Rompe el bucle y vuelve al menú principal

            elif opcion == "5":
                self.salir()
                exit()
            else:
                print("❌ Opción no válida.")

    def generar_reporte_distrito(self, distrito=None, pausa=True):
        """Intermediario que llama a la grafica por distrito."""
        self._mostrar_encabezado("REPORTE ANALÍTICO POR DISTRITO")
        if distrito:
            print(f"\nGenerando gráfica para el distrito: {distrito}")
        else:
            print("\nCargando datos y distritos disponibles...")

        analitica.generar_reporte_distrito_especifico(distrito)

        if pausa:
            input("\n\nPresione: Enter para volver al menú principal...")

    def _menu_consultar_zona(self):
        """Muestra zonas y luego deja elegir ver datos, grafica o ambas cosas."""
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
        """Submenu de acciones para el distrito ya seleccionado."""
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
        while True:
            self._mostrar_encabezado("SISTEMA PYCLIMA RESILIENTE v1.0")
            print("1. 📋 Registrar Datos Climáticos")
            print("2. 📡 Obtener Datos desde API")
            print("3. 🔍 Consultar Datos")
            print("4. 📚 Ver Histórico (Todas las Zonas)")
            print("5. 📢 Alertas Activas")
            print("6. 🔙 Salir")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-6): ").strip()

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
                self.salir()
                break
            else:
                print("Opción no válida. Intente de nuevo.")
                input("Presione Enter para continuar...")

    def generar_reporte_historico_visual(self):
        """Intermediario que llama a la gráfica general del histórico"""
        self._mostrar_encabezado("📊 GRÁFICA GENERAL DEL HISTÓRICO")
        analitica.generar_reporte_visual_pro()
        input("\n\nPresione Enter para volver al histórico...")

    def _imprimir_alertas(self, lista_alertas):
        """Función auxiliar para imprimir las alertas de forma estructurada"""
        print("\n" + "="*50)
        for item in lista_alertas:
            print(f"📍 ZONA: {item['zona']} | 📅 FECHA: {item['fecha']}")
            print("-" * 45)
            for alerta in item['alertas']:
                print(f"  → {alerta}")
        print("="*50)

    def _mostrar_alertas_hoy(self, lista_alertas):
        """Muestra solo las alertas del día en curso"""
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
        """Maneja el filtrado de alertas y lanza la navegación posterior"""
        self._mostrar_encabezado("🚨 TIPOS DE ALERTA 🚨")
        
        # 1. Subimos el diccionario de palabras clave aquí arriba
        palabras_clave = {
            "Alerta de calor": ["calor", "temperatura elevada"],
            "Alerta de frío": ["frío", "helada", "frio"],
            "Alerta de viento": ["viento"],
            "Alerta de humedad": ["humedad", "sequedad"],
            "Alerta de lluvia": ["lluvia"]
        }

        # 2. Imprimimos el menú calculando cuántas alertas hay de cada tipo
        for i, tipo in enumerate(lista_tipos, 1):
            claves = palabras_clave[tipo]
            contador = 0
            # Contamos cuántas alertas coinciden con este tipo
            for item in alertas_encontradas:
                for alerta in item['alertas']:
                    if any(clave in alerta.lower() for clave in claves):
                        contador += 1
                        break # Si encuentra una, suma 1 y pasa a la siguiente zona
            
            # Mostramos la opción con el contador
            print(f"   {i}. {tipo} ({contador} detectadas)")
            
        # --- AÑADIMOS LA OPCIÓN DE ESCAPE (Dinámica) ---
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
                
                # 3. Filtramos la lista buscando las coincidencias
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
        """Submenú de navegación posterior exigido por el esquema"""
        while True:
            self._mostrar_encabezado("OPCIONES POSTERIORES:")
            print("1. 🔙 Volver al panel de alertas")
            print("2. ⬅️  Volver al menú principal")
            print("3. 🚪 Salir del sistema")
            
            post_opcion = input("¿Qué desea hacer ahora? (1-3): ").strip()
            
            if post_opcion == "1":
                return "panel_alertas" # Hace que el bucle padre vuelva a empezar
            elif post_opcion == "2":
                return "menu_principal" # Avisa al bucle padre para que se rompa
            elif post_opcion == "3":
                self.salir()
                exit()
            else:
                print("❌ Opción no válida.")
    
    def salir(self):
        self._mostrar_encabezado("🚪 CERRANDO SISTEMA")
        print("\n✅ Todos los datos han sido guardados correctamente")
        print("🌍 ¡Gracias por usar PyClima Resiliente!")
        print("👋 ¡Hasta pronto!\n")

    def obtener_datos_api(self):
        """
        Obtiene datos climáticos desde WeatherAPI y los muestra 
        antes de guardar (opción de confirmación).
        
        Flujo:
        1. Muestra lista de distritos de Madrid
        2. Usuario selecciona uno
        3. Consulta WeatherAPI
        4. Muestra datos en pantalla
        5. Pregunta: ¿Guardar? (s/n)
        """
        import Api  # Importamos el módulo de API
    
        self._mostrar_encabezado("📡 OBTENER DATOS DESDE API METEOROLÓGICA")
        
        # PASO 1: Obtener lista de distritos
        distritos = persistencia.obtener_distritos_permitidos()
        if not distritos:
            print("❌ No se encontraron distritos configurados en config.json")
            input("Presione Enter para volver...")
            return
        
        # PASO 2: Mostrar lista y pedir selección
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
        
        # PASO 3: Traer datos de la API
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
        
        # PASO 4: Mostrar datos en pantalla
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
        
        # Mostrar alertas si hay
        if registro_api['alertas']:
            print("\n🚨 ALERTAS DETECTADAS:")
            for alerta in registro_api['alertas']:
                print(f"   {alerta}")
        else:
            print("\n✅ No hay alertas")
        
        print("="*50)
        
        # PASO 5: Pedir confirmación
        confirmacion = input("\n¿Desea guardar estos datos? (s/n): ").strip().lower()
        
        if confirmacion == 's':
            # PASO 6: Guardar en JSON
            try:
                exito = persistencia.registrar_nuevo_dato(registro_api)
                if exito:
                    print("✅ ¡Datos guardados exitosamente!")
                    self.datos = self._cargar_datos()  # Refrescar datos
                else:
                    print("❌ No se pudieron guardar los datos")
            except Exception as error:
                print(f"❌ Error al guardar: {error}")
        else:
            print("❌ Operación cancelada. Los datos no se guardaron.")
        
        input("\nPresione Enter para volver al menú principal...")
