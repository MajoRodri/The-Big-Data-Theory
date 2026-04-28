"""
Módulo de interfaz para The Big Data Theory.
Sistema de Monitoreo Climático del Ayuntamiento de Madrid.
"""

import logging
import os
import csv
import shutil
import validaciones
import alertas
import persistencia
import auth
import analitica
import api_history
import Api
import scheduler as sched_module
from datetime import datetime

logger = logging.getLogger(__name__)


class InterfazTBDT:

    def __init__(self, ruta_datos=persistencia.ARCHIVO_JSON, usuario_actual=None):
        self.ruta_datos = ruta_datos
        self.datos = self._cargar_datos()
        self.zonas_validas = self._obtener_zonas()
        self.usuario_actual = usuario_actual

    def _cargar_datos(self):
        return persistencia.leer_historico()

    def _obtener_zonas(self):
        zonas = set()
        for reg in self.datos:
            if "distrito" in reg:
                zonas.add(reg["distrito"])
        return sorted(list(zonas)) if zonas else []

    def _validar_duplicado(self, fecha, distrito, fuente="manual"):
        registros = [
            r for r in self.datos
            if r.get("fecha") == str(fecha)
            and r.get("distrito", "").lower() == distrito.lower()
        ]
        if len(registros) >= 2:
            return True
        return any(r.get("fuente", "manual") == fuente for r in registros)

    def _analizar_alertas(self, temperatura, humedad, viento, lluvia=0):
        umbrales = persistencia.obtener_umbrales_alerta()
        datos_registro = {
            "temperatura": temperatura,
            "humedad": humedad,
            "viento": viento,
            "lluvia": lluvia
        }
        return alertas.evaluar_alertas(datos_registro, umbrales)

    def _mostrar_encabezado(self, titulo):
        print("\n" + "="*50)
        print(f"  {titulo}")
        print("="*50)

    def _mostrar_separador(self):
        print("-" * 50)

    def _normalizar_distrito_oficial(self, distrito):
        distritos_oficiales = persistencia.obtener_distritos_permitidos()
        mapa_distritos = {item.lower(): item for item in distritos_oficiales}
        return mapa_distritos.get(distrito.strip().lower())

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

    def _imprimir_alertas(self, lista_alertas):
        print("\n" + "="*50)
        for item in lista_alertas:
            print(f"📍 ZONA: {item['zona']} | 📅 FECHA: {item['fecha']}")
            print("-" * 45)
            for alerta in item['alertas']:
                print(f"  → {alerta}")
        print("="*50)

    # ─── Menú Principal ───────────────────────────────────────────────────────

    def menu_principal(self):
        while True:
            self._verificar_notificacion_scheduler()
            self._mostrar_encabezado("THE BIG DATA THEORY")
            print("1. 📥 Carga de Datos")
            print("2. 🔍 Consultar Datos")
            print("3. 📊 Estadísticas")
            print("4. 🚨 Alertas")
            print("5. 🚪 Salir")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-5): ").strip()

            if opcion == "1":
                self.menu_ingesta_automatica()
            elif opcion == "2":
                self.consultar_datos()
            elif opcion == "3":
                self.menu_estadisticas()
            elif opcion == "4":
                self.mostrar_panel_alertas()
            elif opcion == "5":
                self.salir()
                break
            else:
                print("❌ Opción no válida.")
                input("Presione Enter para continuar...")

    # =========================================================================
    # 1. INGESTA AUTOMÁTICA / CARGA DE DATOS
    # =========================================================================

    def menu_ingesta_automatica(self):
        while True:
            self._verificar_notificacion_scheduler()
            activo = sched_module.esta_activo()
            estado_txt = "🟢 ACTIVO" if activo else "🔴 DETENIDO"
            self._mostrar_encabezado(f"📥 CARGA DE DATOS  [{estado_txt}] 📥")
            print("1. ⏱️  Encender/Detener")
            print("2. 🔄 Solicitar datos")
            print("3. 📅 Registro Retroactivo de Datos")
            print("4. ⬅️  Volver al menú principal")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-4): ").strip()

            if opcion == "1":
                self._menu_encender_detener_ingesta()
            elif opcion == "2":
                self._solicitar_datos()
            elif opcion == "3":
                self._solicitar_datos_fecha_todos_distritos()
            elif opcion == "4":
                break
            else:
                print("❌ Opción no válida.")
                input("Presione Enter para continuar...")

    def _solicitar_datos_fecha_todos_distritos(self):
        self._mostrar_encabezado("📅 REGISTRO RETROACTIVO DE DATOS 📅")
        self.datos = self._cargar_datos()

        usuario_id = self.usuario_actual["num_empleado"] if self.usuario_actual else "Sistema"
        nombre_usuario = (
            f"{self.usuario_actual.get('nombre', '')} {self.usuario_actual.get('apellidos', '')}".strip()
            if self.usuario_actual else "Sistema"
        )

        distritos = persistencia.obtener_distritos_permitidos()
        if not distritos:
            print("❌ No hay distritos configurados.")
            input("Presione Enter para volver...")
            return

        print(f"\n👤 Solicitado por: {nombre_usuario} ({usuario_id})")
        print(f"🏙️  Distritos a Registrar: {len(distritos)}")
        print("\n📅 Introduce la fecha pasada que deseas registrar.")
        print("   Formato: AAAA-MM-DD  |  Escribe 'c' para cancelar.")

        while True:
            entrada = input("Fecha: ").strip()
            if entrada.lower() == "c":
                return
            try:
                fecha_obj = datetime.strptime(entrada, "%Y-%m-%d")
                if fecha_obj >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                    print("❌ Solo se permiten fechas pasadas.")
                    continue
                fecha_buscada = entrada
                break
            except ValueError:
                print("❌ Formato incorrecto. Usa AAAA-MM-DD.")

        # ── 1. Verificar duplicados ────────────────────────────────────────────
        print(f"\n🔍 Verificando duplicados para {fecha_buscada}...")
        distritos_pendientes = []
        distritos_omitidos = []
        for d in distritos:
            if self._validar_duplicado(fecha_buscada, d, fuente="api"):
                distritos_omitidos.append(d)
            else:
                distritos_pendientes.append(d)

        if distritos_omitidos:
            print(f"⏭️  {len(distritos_omitidos)} distrito(s) ya registrados para esa fecha (se omitirán).")

        if not distritos_pendientes:
            print("\n✅ Todos los distritos ya tienen registro para esa fecha.")
            input("Presione Enter para volver...")
            return

        print(f"\n📋 {len(distritos_pendientes)} distrito(s) a consultar:")
        for d in distritos_pendientes:
            print(f"   • {d}")

        confirmar = input(f"\n¿Consultar la API para estos {len(distritos_pendientes)} distritos? (s/n): ").strip().lower()
        if confirmar != "s":
            print("❌ Operación cancelada.")
            input("Presione Enter para volver...")
            return

        # ── 2. Consultar API sin guardar aún ──────────────────────────────────
        print()
        registros_obtenidos = []
        errores_api = []

        for d in distritos_pendientes:
            print(f"  ⏳ {d}...", end=" ", flush=True)
            try:
                registro = Api.obtener_registro_climatico(
                    d, usuario_actual=self.usuario_actual, fecha=fecha_buscada
                )
                if registro is None:
                    print("❌")
                    errores_api.append(d)
                else:
                    registro["solicitado_por"] = usuario_id
                    registros_obtenidos.append(registro)
                    print("✅")
            except Exception as e:
                print(f"❌ ({e})")
                errores_api.append(d)

        if not registros_obtenidos:
            print("\n❌ No se pudo obtener ningún dato de la API.")
            input("Presione Enter para volver...")
            return

        # ── 3. Mostrar datos obtenidos ─────────────────────────────────────────
        print(f"\n{'='*55}")
        print(f"  📊 DATOS OBTENIDOS — {fecha_buscada}")
        print(f"{'='*55}")
        for reg in registros_obtenidos:
            alertas_reg = reg.get("alertas", [])
            alerta_tag = f"  🚨×{len(alertas_reg)}" if alertas_reg else ""
            print(
                f"  📍 {reg['distrito']:<22} "
                f"🌡️ {reg['temperatura']:>5.1f}°C | "
                f"💧{reg['humedad']:>3.0f}% | "
                f"💨{reg['viento']:>4.0f}km/h | "
                f"🌧️{reg['lluvia']:>4.1f}mm{alerta_tag}"
            )
        print(f"{'='*55}")
        print(f"  Total obtenidos: {len(registros_obtenidos)}  |  Errores API: {len(errores_api)}")

        # ── 4. Confirmar guardado ──────────────────────────────────────────────
        confirmar_guardar = input(
            f"\n¿Confirmar guardado de {len(registros_obtenidos)} registro(s) en el sistema? (s/n): "
        ).strip().lower()
        if confirmar_guardar != "s":
            print("❌ Datos descartados. No se guardó nada.")
            input("Presione Enter para volver...")
            return

        # ── 5. Guardar en JSON ─────────────────────────────────────────────────
        guardados = []
        errores_guardado = []
        for reg in registros_obtenidos:
            exito = persistencia.registrar_nuevo_dato(reg, forzar=True)
            if exito:
                guardados.append(reg["distrito"])
            else:
                errores_guardado.append(reg["distrito"])

        self.datos = self._cargar_datos()
        print(f"\n{'='*50}")
        print(
            f"  ✅ Guardados: {len(guardados)}  |  "
            f"⏭️  Omitidos: {len(distritos_omitidos)}  |  "
            f"❌ Errores: {len(errores_api) + len(errores_guardado)}"
        )
        if errores_api:
            print(f"\n  ⚠️  Sin datos de API:")
            for d in errores_api:
                print(f"     • {d}")
        if errores_guardado:
            print(f"\n  ⚠️  No se pudieron guardar:")
            for d in errores_guardado:
                print(f"     • {d}")
        input("\nPresione Enter para volver...")

    def _menu_encender_detener_ingesta(self):
        while True:
            activo = sched_module.esta_activo()
            resumen = sched_module.obtener_resumen()
            proximo = sched_module.obtener_proximo_disparo()

            self._mostrar_encabezado("⏱️ ENCENDER / DETENER ⏱️")
            estado_txt = "🟢 ACTIVO" if activo else "🔴 DETENIDO"
            print(f"\n  Estado actual: {estado_txt}")
            if proximo:
                print(f"  Próxima ejecución: {proximo.strftime('%H:%M:%S')}")
            if resumen["ultima_ejecucion"]:
                ue = resumen["ultima_ejecucion"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"  Último ciclo: {ue}  |  ✅ {resumen['guardados']}  ⏭️ {resumen['omitidos']}  ❌ {resumen['errores']}")

            print()
            if activo:
                print(" 🔴 → [Presione 1 para DETENER la ingesta] 🔴")
            else:
                print(" 🟢 → [Presione 1 para ENCENDER la ingesta] 🟢")

            print()
            print("1. ▶️/⏹️  Encender / Detener")
            print("NOTA: 🕐 Tiempo (Horario fijo 07:00h | 15:00h | 22:00h) 🕐")
            print("2. ⬅️  Volver")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-2): ").strip()

            if opcion == "1":
                if activo:
                    sched_module.detener()
                    print("✅ Ingesta automática detenida.")
                else:
                    sched_module.iniciar()
                    print("✅ Ingesta automática iniciada.")
                    print("   Horario: 07:00h | 15:00h | 22:00h")
                input("\nPresione Enter para continuar...")
            elif opcion == "2":
                break
            else:
                print("❌ Opción no válida.")

    # ─── Registro manual (fallback por error de API) ──────────────────────────

    def _registrar_datos_manual(self):
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
                    print(f"⚠️  Ya existe un registro para {distrito} en {fecha}.")
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
                datos_reg = {"temperatura": temperatura, "humedad": humedad, "viento": viento, "lluvia": lluvia}
                alertas_activas = alertas.evaluar_alertas(datos_reg, umbrales)

                if alertas_activas:
                    print("\n🚨 ALERTAS DETECTADAS 🚨 ")
                    for alerta in alertas_activas:
                        print(f"   {alerta}")
                else:
                    print("\n✅ Niveles climáticos normales.")
                print("-" * 50)

                nuevo_registro = {
                    "fecha": fecha,
                    "distrito": distrito,
                    "fuente": "manual",
                    "temperatura": temperatura,
                    "temp": temperatura,
                    "humedad": humedad,
                    "viento": viento,
                    "lluvia": lluvia,
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
                print("\n\n❌ Registro cancelado")
                return
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                if input("¿Desea ingresar los datos nuevamente? (s/n): ").lower() != 's':
                    return

    # ─── Notificaciones de ingesta automática ────────────────────────────────

    def _verificar_notificacion_scheduler(self):
        """Comprueba y muestra notificaciones pendientes del scheduler."""
        notif = sched_module.obtener_notificacion_pendiente()
        if notif:
            self._mostrar_notificacion_ingesta(notif)
            self.datos = self._cargar_datos()

    def _mostrar_notificacion_ingesta(self, notif):
        """Muestra el resultado de la autoingesta con formato visual limpio."""
        ts = notif["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        detalles = notif["detalles"]
        errores_lista = notif["errores_lista"]

        print("\n" + "=" * 60)
        print(f"  🔔 AUTOINGESTA AUTOMÁTICA — {ts}")
        print("=" * 60)

        if detalles:
            print("\n✅ Datos de clima cargados con éxito.\n")
            print("📊 REGISTROS POR DISTRITO:")
            print("-" * 60)
            for d in detalles:
                icono = "✅" if d["estado"] == "guardado" else "⏭️ "
                alerta_tag = f" 🚨×{len(d['alertas'])}" if d.get("alertas") else ""
                print(
                    f"  {icono} {d['distrito']:<22} "
                    f"🌡️ {d['temp']:>5.1f}°C | 💧{d['humedad']:>3.0f}% | "
                    f"💨{d['viento']:>4.0f}km/h | 🌧️{d['lluvia']:>4.1f}mm  "
                    f"[HTTP {d['http_code']}]{alerta_tag}"
                )

        if errores_lista:
            print(f"\n❌ ERRORES ENCONTRADOS ({len(errores_lista)}):")
            print("-" * 60)
            for err in errores_lista:
                codigo = err["codigo"]
                codigo_str = f"HTTP {codigo}" if isinstance(codigo, int) else str(codigo)
                print(f"  ⚠️  {err['distrito']}")
                print(f"     Error: {codigo_str} — {err['mensaje']}")
                print(f"     💡 Sugerencia: {err['sugerencia']}")

        print()
        print(f"  📅 Fecha/hora: {ts}")
        print(
            f"  📊 Guardados: {notif['guardados']} | "
            f"⏭️  Omitidos: {notif['omitidos']} | "
            f"❌ Errores: {notif['errores']}"
        )
        print("\n🚀 Sistema listo para consultas.")
        print("=" * 60)

        if errores_lista:
            self._manejar_errores_autoingesta(errores_lista)
        else:
            input("\nPresione Enter para continuar...")

    def _manejar_errores_autoingesta(self, errores_lista):
        """Sub-menú de gestión para cada distrito con error en la autoingesta."""
        print(f"\n⚠️  Hay {len(errores_lista)} distrito(s) con error. ¿Desea gestionarlos ahora?")
        print("   1. Sí, gestionar ahora")
        print("   2. No, continuar")
        respuesta = input("   Opción (1-2): ").strip()
        if respuesta != "1":
            return

        for err in errores_lista:
            distrito = err["distrito"]
            codigo = err["codigo"]
            codigo_str = f"HTTP {codigo}" if isinstance(codigo, int) else str(codigo)

            while True:
                print(f"\n{'─'*50}")
                print(f"  ⚠️  {distrito} — Error {codigo_str}")
                print(f"  💡 {err['sugerencia']}")
                print("─" * 50)
                print("  1. 🔄 Reintentar con API")
                print("  2. ✏️  Registrar manualmente")
                print("  3. ⏭️  Omitir este distrito")
                opcion = input("  Opción (1-3): ").strip()

                if opcion == "1":
                    print(f"  ⏳ Reintentando {distrito}...", end=" ", flush=True)
                    registro = Api.obtener_registro_climatico(distrito)
                    if registro:
                        exito = persistencia.registrar_nuevo_dato(registro, forzar=True)
                        if exito:
                            print("✅")
                            self.datos = self._cargar_datos()
                            break
                        else:
                            print("❌ No se pudo guardar.")
                    else:
                        nuevo_err = Api._ultimo_error.copy()
                        nuevo_cod = nuevo_err.get("codigo", "N/A")
                        nuevo_cod_str = f"HTTP {nuevo_cod}" if isinstance(nuevo_cod, int) else str(nuevo_cod)
                        print(f"❌ {nuevo_cod_str}")

                elif opcion == "2":
                    self._registrar_manual_por_error_api(distrito, err)
                    break

                elif opcion == "3":
                    print(f"  ⏭️  Omitido: {distrito}")
                    break

                else:
                    print("❌ Opción no válida.")

    def _registrar_manual_por_error_api(self, distrito, err_info):
        """Registro manual de un distrito cuando la API falla. Loguea el evento correctamente."""
        codigo = err_info.get("codigo", "N/A")
        codigo_str = f"http {codigo}" if isinstance(codigo, int) else str(codigo).lower()
        usuario_id = self.usuario_actual["num_empleado"] if self.usuario_actual else "Sistema"

        # Log: error http (código)
        logger.warning("error %s | %s", codigo_str, distrito)

        print(f"\n✏️  REGISTRO MANUAL — {distrito}")
        print(f"   Motivo: error {codigo_str.upper()}")

        try:
            print("\n[1/4] TEMPERATURA")
            temperatura = validaciones.validar_temperatura()
            print("\n[2/4] HUMEDAD")
            humedad = validaciones.validar_humedad()
            print("\n[3/4] VELOCIDAD DEL VIENTO")
            viento = validaciones.validar_viento()
            print("\n[4/4] PRECIPITACIONES")
            lluvia = validaciones.validar_lluvia()

            umbrales = persistencia.obtener_umbrales_alerta()
            datos_reg = {
                "temperatura": temperatura, "humedad": humedad,
                "viento": viento, "lluvia": lluvia,
            }
            alertas_activas = alertas.evaluar_alertas(datos_reg, umbrales)

            fecha = datetime.now().strftime("%Y-%m-%d")
            nuevo_registro = {
                "fecha": fecha,
                "distrito": distrito,
                "fuente": "manual",
                "temperatura": temperatura,
                "temp": temperatura,
                "humedad": humedad,
                "viento": viento,
                "lluvia": lluvia,
                "alertas": alertas_activas,
                "registrado_por": usuario_id,
                "editado": False,
            }

            exito = persistencia.registrar_nuevo_dato(nuevo_registro, forzar=True)
            if exito:
                # Log: usuario X ha registrado datos manualmente | carga de datos manual
                logger.info(
                    "usuario %s ha registrado datos manualmente | carga de datos manual",
                    usuario_id,
                )
                print(f"\n✅ {distrito} registrado manualmente (fuente: manual).")
                self.datos = self._cargar_datos()
            else:
                print(f"❌ No se pudo guardar el registro manual para {distrito}.")

        except KeyboardInterrupt:
            print(f"\n❌ Registro cancelado para {distrito}.")

    def _solicitar_datos(self):
        """Solicita datos desde la API para el distrito y fecha elegidos. Registra 'solicitado_por'."""
        self.datos = self._cargar_datos()

        usuario_id = self.usuario_actual["num_empleado"] if self.usuario_actual else "Sistema"
        nombre_usuario = (
            f"{self.usuario_actual.get('nombre', '')} {self.usuario_actual.get('apellidos', '')}".strip()
            if self.usuario_actual else "Sistema"
        )

        while True:
            try:
                self._mostrar_encabezado("🔄 SOLICITAR DATOS")
                print(f"\n👤 Solicitado por: {nombre_usuario} ({usuario_id})")

                # Selección de distrito
                distritos = persistencia.obtener_distritos_permitidos()
                if not distritos:
                    print("❌ No se encunetra los Distritos disponibles.")
                    input("Presione Enter para volver...")
                    return

                print("\n📍 Distritos disponibles 📍")
                for i, d in enumerate(distritos, 1):
                    print(f"   {i}. {d}")
                opcion_volver = len(distritos) + 1
                print(f"   {opcion_volver}. ⬅️  Volver")
                self._mostrar_separador()

                entrada = input(f"Seleccione un distrito (1-{opcion_volver}): ").strip()
                if entrada == str(opcion_volver):
                    return

                try:
                    seleccion = int(entrada) - 1
                    if not (0 <= seleccion < len(distritos)):
                        print("❌ Selección inválida.")
                        input("Presione Enter para continuar...")
                        continue
                    distrito = distritos[seleccion]
                except ValueError:
                    print("❌ Ingrese un número válido.")
                    input("Presione Enter para continuar...")
                    continue

                # Selección de fecha (Enter = hoy, o fecha pasada/actual)
                print(f"\n📅 FECHA DEL REGISTRO 📅")
                print("   Presione Enter para usar la fecha de hoy, o escriba AAAA-MM-DD.")
                print("   Escribe 'c' para cancelar.")

                fecha = None
                while True:
                    fecha_entrada = input("Fecha: ").strip()

                    if fecha_entrada.lower() == "c":
                        break

                    if not fecha_entrada:
                        fecha = datetime.now().strftime("%Y-%m-%d")
                        print(f"   → Usando fecha de hoy: {fecha}")
                        break

                    try:
                        fecha_obj = datetime.strptime(fecha_entrada, "%Y-%m-%d")
                        if fecha_obj > datetime.now():
                            print("❌ No se permiten fechas futuras.")
                            continue
                        fecha = fecha_entrada
                        break
                    except ValueError:
                        print("❌ Formato incorrecto. Usa AAAA-MM-DD.")
                        continue

                if fecha is None:
                    continue

                # Refrescar antes de verificar (el scheduler puede haber guardado en background)
                self.datos = self._cargar_datos()
                if self._validar_duplicado(fecha, distrito, fuente="api"):
                    print(f"\n⚠️  Ya existe un registro API para {distrito} en {fecha}.")
                    print("   (El scheduler automático pudo haberlo guardado en background)")
                    if input("¿Solicitar para otro distrito/fecha? (s/n): ").strip().lower() != "s":
                        return
                    continue

                # Llamar a la API
                print(f"\n⏳ Consultando datos para {distrito} ({fecha})...⏳")
                nuevo_registro = Api.obtener_registro_climatico(
                    distrito,
                    usuario_actual=self.usuario_actual,
                    fecha=fecha,
                )

                if nuevo_registro is None:
                    print("❌ No se pudo obtener datos desde la API.")
                    print("\n  1. Reintentar consulta a la API")
                    print("  2. Registrar manualmente")
                    print("  3. Cancelar")
                    opcion_fallo = input("Seleccione una opción (1-3): ").strip()
                    if opcion_fallo == "1":
                        continue
                    elif opcion_fallo == "2":
                        self._registrar_datos_manual()
                    return

                # Mostrar datos
                print("\n" + "=" * 50)
                print("✅ DATOS CARGADOS CORRECTAMENTE ✅")
                print("=" * 50)
                print(f"📍 Distrito: {nuevo_registro['distrito']}")
                print(f"📅 Fecha: {nuevo_registro['fecha']}")
                print(f"🌡️  Temperatura: {nuevo_registro['temperatura']}°C")
                print(f"💧 Humedad: {nuevo_registro['humedad']}%")
                print(f"💨 Viento: {nuevo_registro['viento']} km/h")
                print(f"🌧️  Lluvia: {nuevo_registro['lluvia']} mm")
                print(f"👤 Solicitado por: {nombre_usuario}")

                if nuevo_registro.get("alertas"):
                    print("\n🚨 ALERTAS DETECTADAS 🚨")
                    for alerta in nuevo_registro["alertas"]:
                        print(f"   {alerta}")
                else:
                    print("\n✅ Niveles climáticos normales ✅ ")
                nuevo_registro["solicitado_por"] = usuario_id

                self._mostrar_separador()
                exito = persistencia.registrar_nuevo_dato(nuevo_registro)

                if exito:
                    self.datos = self._cargar_datos()
                    if input("\n¿Solicitar otro dato? (s/n): ").strip().lower() != "s":
                        return
                else:
                    self.datos = self._cargar_datos()
                    if input("¿Intentar con otro distrito/fecha? (s/n): ").strip().lower() != "s":
                        return

            except KeyboardInterrupt:
                print("\n\n❌ Solicitud cancelada")
                return
            except Exception as e:
                print(f"❌ Error al obtener datos desde la API: {e}")
                if input("¿Desea intentarlo nuevamente? (s/n): ").strip().lower() != "s":
                    return

    # =========================================================================
    # 2. CONSULTAR DATOS
    # =========================================================================

    def consultar_datos(self):
        while True:
            self._verificar_notificacion_scheduler()
            self._mostrar_encabezado("🔍 CONSULTAR DATOS")
            self.datos = self._cargar_datos()

            if not self.datos:
                print("❌ No hay datos registrados en el sistema.")
                input("Presione Enter para continuar...")
                return

            print("1. 🔎 Búsqueda de Registros por...")
            print("2. 📤 Exportar CSV")
            print("3. 💾 Backup de datos")
            print("4. ⬅️  Volver al menú principal")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-4): ").strip()

            if opcion == "1":
                self._menu_filtros()
            elif opcion == "2":
                self.exportar_datos_csv()
            elif opcion == "3":
                self.backup_datos()
            elif opcion == "4":
                break
            else:
                print("❌ Opción no válida.")
                input("Presione Enter para continuar...")

    def _menu_filtros(self):
        while True:
            self._mostrar_encabezado("🔎 BÚSQUEDA DE REGISTROS POR...")
            print("1. 📅 Fecha")
            print("2. 👤 Usuario")
            print("3. 📍Distrito")
            print("4. ⬅️  Volver")
            self._mostrar_separador()

            opcion = input("Seleccione un filtro (1-4): ").strip()

            if opcion == "1":
                self._menu_consultar_fecha()
                input("\nPresione Enter para continuar...")
            elif opcion == "2":
                self._menu_filtrar_usuario_ultimos30()
            elif opcion == "3":
                self._menu_filtrar_distrito_ultimos30()
            elif opcion == "4":
                break
            else:
                print("❌ Opción no válida.")

    def _menu_consultar_fecha(self):
        print("\n📅 POR FECHA 📅")
        try:
            fecha_buscada = validaciones.validar_fecha()
        except KeyboardInterrupt:
            print("\n❌ Búsqueda cancelada.")
            return
        print(f"\n📊 Datos del día: {fecha_buscada} 📊")
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

    def _menu_filtrar_usuario_ultimos30(self):
        while True:
            self._mostrar_encabezado("👤 POR USUARIO 👤")
            self.datos = self._cargar_datos()

            todos_usuarios = auth.cargar_datos(persistencia.ARCHIVO_USUARIOS)
            if not todos_usuarios:
                print("❌ No hay usuarios registrados en el sistema.")
                input("Presione Enter para volver...")
                return

            print("\n📋 Directorio de usuarios 📋")
            for i, u in enumerate(todos_usuarios, 1):
                op_id = u.get("num_empleado", "")
                nombre_display = f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()
                if self.usuario_actual and op_id == self.usuario_actual.get("num_empleado"):
                    print(f"   {i}. {nombre_display}  (ID: {op_id})  ⬅️  (ESTE ERES TÚ)")
                else:
                    print(f"   {i}. {nombre_display}")
            opcion_volver = len(todos_usuarios) + 1
            print(f"   {opcion_volver}. ⬅️  Volver")
            self._mostrar_separador()

            entrada = input(f"Seleccione un usuario (1-{opcion_volver}): ").strip()
            if entrada == str(opcion_volver):
                break

            try:
                seleccion = int(entrada) - 1
                if not (0 <= seleccion < len(todos_usuarios)):
                    print("❌ Selección inválida")
                    continue

                usuario_sel = todos_usuarios[seleccion]
                op_seleccionado = usuario_sel.get("num_empleado", "")
                nombre_sel = f"{usuario_sel.get('nombre', '')} {usuario_sel.get('apellidos', '')}".strip()

                registros_usuario = [
                    (i, r) for i, r in enumerate(self.datos)
                    if r.get("registrado_por") == op_seleccionado
                ]
                ultimos_30 = sorted(
                    registros_usuario, key=lambda x: x[1].get("fecha", ""), reverse=True
                )[:30]

                print(f"\n📊 Últimos registros de: {nombre_sel}")
                self._mostrar_separador()

                if not ultimos_30:
                    print("ℹ️ Este usuario no tiene registros en el sistema.")
                else:
                    for num, (_, reg) in enumerate(ultimos_30, 1):
                        temp = reg.get('temp', reg.get('temperatura', 0))
                        fuente_reg = reg.get("fuente", "manual")
                        if fuente_reg == "api":
                            estado = " | 🤖 API (no editable)"
                        elif reg.get("editado"):
                            estado = " | 🔒 Ya editado"
                        else:
                            estado = " | ✏️ Editable"
                        print(f"{num}. 📅 {reg.get('fecha')} | 📍 {reg.get('distrito', 'Desconocida')}{estado}")
                        print(f"   🌡️  T: {temp}°C | 💧 H: {reg.get('humedad', 0)}% | 💨 V: {reg.get('viento', 0)} km/h")
                        print("-" * 30)

                    print(f"✅ Mostrando {len(ultimos_30)} de {len(registros_usuario)} registros.")

                    if self.usuario_actual and op_seleccionado == self.usuario_actual.get("num_empleado"):
                        hay_editables = any(
                            r.get("fuente", "manual") != "api" and not r.get("editado")
                            for _, r in ultimos_30
                        )
                        if hay_editables:
                            editar = input("\n¿Desea editar uno de sus registros? (s/n): ").strip().lower()
                            if editar == "s":
                                self._editar_registro_usuario([(i, r) for i, r in ultimos_30])
                        else:
                            print("\nℹ️ No tiene registros manuales editables.")
                    elif self.usuario_actual and op_seleccionado != self.usuario_actual.get("num_empleado"):
                        print("ℹ️ Solo el usuario que registró los datos puede editarlos.")

                input("\nPresione Enter para continuar...")

            except ValueError:
                print("❌ Ingrese un número válido")

    def _menu_filtrar_distrito_ultimos30(self):
        while True:
            self._mostrar_encabezado("📍 POR DISTRITO 📍")
            self.datos = self._cargar_datos()

            distritos = persistencia.obtener_distritos_permitidos()
            if not distritos:
                print("❌ No hay distritos configurados.")
                input("Presione Enter para volver...")
                return

            print("\n📍 Distritos disponibles:")
            for i, d in enumerate(distritos, 1):
                print(f"   {i}. {d}")
            opcion_volver = len(distritos) + 1
            print(f"   {opcion_volver}. ⬅️  Volver")
            self._mostrar_separador()

            entrada = input(f"Seleccione un distrito (1-{opcion_volver}): ").strip()
            if entrada == str(opcion_volver):
                break

            try:
                seleccion = int(entrada) - 1
                if not (0 <= seleccion < len(distritos)):
                    print("❌ Selección inválida.")
                    continue

                zona = distritos[seleccion]
                registros_zona = [r for r in self.datos if r.get("distrito", "").lower() == zona.lower()]
                ultimos_30 = sorted(registros_zona, key=lambda r: r.get("fecha", ""), reverse=True)[:30]

                print(f"\n📊 Últimos Registros de: {zona}")
                self._mostrar_separador()

                if not ultimos_30:
                    print(f"❌ No hay datos para {zona}")
                else:
                    for reg in ultimos_30:
                        temp = reg.get('temp', reg.get('temperatura', 0))
                        print(f"📅 {reg['fecha']} | 🤖 Fuente: {reg.get('fuente', 'manual')}")
                        print(f"   🌡️  T: {temp}°C | 💧 H: {reg.get('humedad', 0)}% | 💨 V: {reg.get('viento', 0)} km/h | 🌧️ {reg.get('lluvia', 0)} mm")
                        alertas_locales = self._analizar_alertas(
                            temp, reg.get('humedad', 0), reg.get('viento', 0), reg.get('lluvia', 0)
                        )
                        for alerta_txt in alertas_locales:
                            print(f"   {alerta_txt}")
                        print("-" * 30)
                    print(f"✅ Mostrando {len(ultimos_30)} de {len(registros_zona)} registros.")

                input("\nPresione Enter para continuar...")

            except ValueError:
                print("❌ Ingrese un número válido.")

    def _editar_registro_usuario(self, registros_operario):
        while True:
            try:
                seleccion = input("Seleccione el número del registro a editar (Enter para cancelar): ").strip()
                if not seleccion:
                    return
                indice_lista = int(seleccion) - 1
                if not (0 <= indice_lista < len(registros_operario)):
                    print("❌ Selección inválida. Introduce un número de la lista.")
                    continue
                break
            except ValueError:
                print("❌ Introduce un número válido.")
                continue

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
            print("❌ No se puede guardar la edición: ya existen registros para esa fecha y distrito.")
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

    def exportar_datos_csv(self):
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

            print(f"✅ Exportación completada!")
            print(f"📁 Archivo: {ruta_archivo}")
            print(f"📊 Registros exportados: {len(self.datos)}")

        except Exception as e:
            print(f"❌ Error al exportar datos: {e}")

        input("\nPresione Enter para volver...")

    def backup_datos(self):
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

        input("\nPresione Enter para volver...")

    # =========================================================================
    # 3. ESTADÍSTICAS
    # =========================================================================

    def menu_estadisticas(self):
        while True:
            self._verificar_notificacion_scheduler()
            self._mostrar_encabezado("📊 ESTADÍSTICAS")
            print("1. 📈 Estadísticas Generales")
            print("2. 📉 Gráficas")
            print("3. ⬅️  Volver al menú principal")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-3): ").strip()

            if opcion == "1":
                self._menu_estadisticas_generales()
            elif opcion == "2":
                self._menu_grafica_comparativas()
            elif opcion == "3":
                break
            else:
                print("❌ Opción no válida.")
                input("Presione Enter para continuar...")

    def _menu_estadisticas_generales(self):
        while True:
            self._mostrar_encabezado("📈 ESTADÍSTICAS GENERALES")
            self.ver_metricas_sistema()

            print("\n1. 📋 Generar Reporte")
            print("2. ⬅️  Volver")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-2): ").strip()

            if opcion == "1":
                self.generar_reporte_automatico()
            elif opcion == "2":
                break
            else:
                print("❌ Opción no válida.")

    def _menu_grafica_comparativas(self):
        while True:
            self._mostrar_encabezado("📉 GRÁFICAS 📉")
            print("1. 🏙️  Comparativa General por Distritos")
            print("2. 📊 Comparativa Mensual Interanual")
            print("3. 📅 Comparativa Anual")
            print("4. ⬅️  Volver")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-4): ").strip()

            if opcion == "1":
                self._grafica_comparativa_distritos()
            elif opcion == "2":
                self._grafica_comparativa_mensual_interanual()
            elif opcion == "3":
                self._grafica_comparativa_anual_api()
            elif opcion == "4":
                break
            else:
                print("❌ Opción no válida.")

    def _grafica_comparativa_distritos(self):
        """Gráfica de barras de temperatura para los 21 distritos en una fecha exacta."""
        self._mostrar_encabezado("🏙️  COMPARATIVA GENERAL POR DISTRITOS")

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        print(f"\n📅 Fecha a analizar (Enter = hoy [{fecha_hoy}], o AAAA-MM-DD, o 'c' para cancelar):")
        while True:
            entrada = input("Fecha: ").strip()
            if entrada.lower() == "c":
                return
            if not entrada:
                fecha = fecha_hoy
                break
            try:
                datetime.strptime(entrada, "%Y-%m-%d")
                fecha = entrada
                break
            except ValueError:
                print("❌ Formato incorrecto. Usa AAAA-MM-DD.")

        magnitud = "temperatura"
        distritos = persistencia.obtener_distritos_permitidos()
        historico_local = self._cargar_datos()
        presentes = {r.get("distrito", "") for r in historico_local if r.get("fecha") == fecha}
        pendientes = [d for d in distritos if d not in presentes]

        if pendientes:
            print(f"\n⏳ {len(pendientes)} distrito(s) sin datos locales consultando API...")
            fallidos = []
            for i, d in enumerate(pendientes, 1):
                print(f"   [{i}/{len(pendientes)}] {d}...", end=" ", flush=True)
                errores = api_history.asegurar_datos_rango(d, fecha, fecha)
                if errores:
                    print("❌")
                    fallidos.append(d)
                else:
                    print("✅")
            if fallidos:
                print(f"\n⚠️  Sin datos para {len(fallidos)} distrito(s), usaremos los disponibles.")
        else:
            print(f"\n✅ Datos en caché para {fecha}.")

        self.datos = self._cargar_datos()
        print("\n📊 Generando gráfica...")
        analitica.grafica_comparativa_distritos(self.datos, fecha, magnitud)
        input("\nPresione Enter para volver...")

    def _grafica_comparativa_mensual_interanual(self):
        """Gráfica que superpone los días de un mes de dos años distintos para un distrito."""
        self._mostrar_encabezado("📊 COMPARATIVA MENSUAL INTERANUAL")

        distritos = persistencia.obtener_distritos_permitidos()
        if not distritos:
            print("❌ No hay distritos configurados.")
            input("Presione Enter para volver...")
            return

        print("\n📍 Seleccione un distrito:")
        for i, d in enumerate(distritos, 1):
            print(f"   {i}. {d}")
        opcion_volver = len(distritos) + 1
        print(f"   {opcion_volver}. ⬅️  Volver")
        self._mostrar_separador()

        while True:
            try:
                entrada = input(f"Distrito (1-{opcion_volver}): ").strip()
                if entrada == str(opcion_volver):
                    return
                idx = int(entrada) - 1
                if 0 <= idx < len(distritos):
                    distrito = distritos[idx]
                    break
                print("❌ Selección inválida.")
            except ValueError:
                print("❌ Introduce un número válido.")

        anio_actual = datetime.now().year
        mes_actual = datetime.now().month

        while True:
            try:
                mes = int(input("\nMes a comparar (1-12): ").strip())
                if 1 <= mes <= 12:
                    break
                print("❌ El mes debe estar entre 1 y 12.")
            except ValueError:
                print("❌ Introduce un número válido.")

        def _anio_valido(anio):
            if anio < 1940 or anio > anio_actual:
                return False
            if anio == anio_actual and mes > mes_actual:
                return False
            return True

        while True:
            try:
                anio1 = int(input(f"Primer año (ej. {anio_actual - 4}): ").strip())
                if _anio_valido(anio1):
                    break
                print(f"❌ Año inválido o mes aún no disponible para {anio1}.")
            except ValueError:
                print("❌ Introduce un número válido.")

        while True:
            try:
                anio2 = int(input(f"Segundo año (ej. {anio_actual - 1}): ").strip())
                if anio2 == anio1:
                    print("❌ Los dos años deben ser distintos.")
                    continue
                if _anio_valido(anio2):
                    break
                print(f"❌ Año inválido o mes aún no disponible para {anio2}.")
            except ValueError:
                print("❌ Introduce un número válido.")

        nombre_mes = analitica.NOMBRES_MES.get(mes, str(mes))
        print(f"\n⏳ Consultando API para {nombre_mes} de {anio1} y {anio2} en {distrito}... ⏳")

        registros1 = api_history.consultar_datos_mes_sin_guardar(distrito, anio1, mes)
        print(f"   {'✅' if registros1 else '⚠️ Sin datos'} {nombre_mes} {anio1} — {len(registros1)} días")

        registros2 = api_history.consultar_datos_mes_sin_guardar(distrito, anio2, mes)
        print(f"   {'✅' if registros2 else '⚠️ Sin datos'} {nombre_mes} {anio2} — {len(registros2)} días")

        if not registros1 and not registros2:
            print("❌ No se pudieron obtener datos de la API.")
            input("Presione Enter para volver...")
            return

        datos_combinados = registros1 + registros2
        print(f"\n📊 Generando comparativa {anio1} vs {anio2}...")
        analitica.grafica_comparativa_mensual_interanual(datos_combinados, distrito, mes, anio1, anio2)
        input("\nPresione Enter para volver...")

    def _grafica_comparativa_anual_api(self):
        """Comparativa anual consultando API directamente"""
        self._mostrar_encabezado("📅 COMPARATIVA ANUAL")

        anio_actual = datetime.now().year
        anio_ini_default = anio_actual - 4

        print(f"\n📅 Rango de años a consultar")
        while True:
            entrada = input(f"   Año inicial [{anio_ini_default}]: ").strip()
            if not entrada:
                anio_inicio = anio_ini_default
                break
            try:
                anio_inicio = int(entrada)
                if anio_inicio < 1940 or anio_inicio > anio_actual:
                    print(f"❌ Año inválido. Debe estar entre 1940 y {anio_actual}.")
                    continue
                break
            except ValueError:
                print("❌ Introduce un año válido.")

        while True:
            entrada = input(f"   Año final [{anio_actual - 1}]: ").strip()
            if not entrada:
                anio_fin = anio_actual - 1
                break
            try:
                anio_fin = int(entrada)
                if anio_fin < anio_inicio or anio_fin > anio_actual:
                    print(f"❌ Año inválido. Debe estar entre {anio_inicio} y {anio_actual}.")
                    continue
                break
            except ValueError:
                print("❌ Introduce un año válido.")

        n_anios = anio_fin - anio_inicio + 1
        print(f"\n⏳ Consultando API para {n_anios} año(s)...")
        medias = api_history.consultar_medias_anuales_madrid(anio_inicio, anio_fin)

        if not medias:
            print("❌ No se pudieron obtener datos de la API.")
            input("Presione Enter para volver...")
            return

        print(f"✅ Datos obtenidos para {len(medias)} año(s).")
        print("\n📊 Generando gráfica...")
        analitica.grafica_comparativa_anual_api(medias)
        input("\nPresione Enter para volver...")

    def ver_metricas_sistema(self):
        self.datos = self._cargar_datos()

        if not self.datos:
            print("❌ No hay datos registrados en el sistema.")
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

    def generar_reporte_automatico(self):
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

            print("✅ Reporte generado y descargado exitosamente!")
            print(f"📁 Archivo: {ruta_archivo}")
            print(f"\n📋 RESUMEN:")
            print(f"   📊 Total registros: {total_registros}")
            print(f"   🏙️ Distritos: {len(distritos)}")
            print(f"   🚨 Alertas totales: {total_alertas}")

        except Exception as e:
            print(f"❌ Error al generar el reporte: {e}")

        input("\nPresione Enter para volver...")

    # =========================================================================
    # 4. ALERTAS
    # =========================================================================

    def mostrar_panel_alertas(self):
        while True:
            self._verificar_notificacion_scheduler()
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

            print(f"\n  📊 Total de registros con alertas: {len(alertas_encontradas)}")
            print("\n1. 📅 Ver alertas de hoy")
            print("2. 📋 Historial de alertas")
            print("3. ⬅️  Volver al menú principal")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-3): ").strip()

            if opcion == "1":
                self._ver_alertas_hoy(alertas_encontradas)
            elif opcion == "2":
                self._historial_alertas_ultimos30(alertas_encontradas)
            elif opcion == "3":
                break
            else:
                print("❌ Opción no válida.")

    def _ver_alertas_hoy(self, alertas_encontradas):
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        hoy_lista = [a for a in alertas_encontradas if a['fecha'] == fecha_hoy]

        self._mostrar_encabezado(f"📅 ALERTAS DE HOY ({fecha_hoy})")

        if not hoy_lista:
            print(f"\n✅ No hay alertas activas para hoy ({fecha_hoy}).")
        else:
            self._imprimir_alertas(hoy_lista)

        input("\nPresione Enter para volver...")

    def _historial_alertas_ultimos30(self, alertas_encontradas):
        ordenadas = sorted(alertas_encontradas, key=lambda x: x['fecha'], reverse=True)
        ultimas_30 = ordenadas[:30]

        self._mostrar_encabezado(f"📋 HISTORIAL DE ALERTAS — ÚLTIMAS {len(ultimas_30)}")
        self._imprimir_alertas(ultimas_30)

        while True:
            print("\n1. 🔍 Filtrar por tipo de alerta")
            print("2. ⬅️  Volver")
            self._mostrar_separador()

            opcion = input("Seleccione una opción (1-2): ").strip()

            if opcion == "1":
                self._filtrar_alertas_por_tipo_ultimos30(alertas_encontradas)
            elif opcion == "2":
                break
            else:
                print("❌ Opción no válida.")

    def _filtrar_alertas_por_tipo_ultimos30(self, alertas_encontradas):
        TIPOS = {
            "🔥 Calor":   ["calor"],
            "❄️  Frío":   ["frío", "frio", "helada"],
            "💨 Viento":  ["viento"],
            "🌧️  Lluvia":  ["lluvia"],
            "💧 Humedad": ["humedad"],
        }

        # Pool: últimas 30 alarmas, prefiriendo año 2026
        alarmas_2026 = sorted(
            [a for a in alertas_encontradas if a["fecha"].startswith("2026")],
            key=lambda x: x["fecha"], reverse=True,
        )
        otras = sorted(
            [a for a in alertas_encontradas if not a["fecha"].startswith("2026")],
            key=lambda x: x["fecha"], reverse=True,
        )
        pool = (alarmas_2026 + otras)[:30]

        tipos_lista = list(TIPOS.keys())

        while True:
            self._verificar_notificacion_scheduler()
            self._mostrar_encabezado("🔍 FILTRAR POR TIPO DE ALERTA")

            print(f"\n  (Últimas {len(pool)} alarmas — preferencia 2026)\n")
            for i, tipo in enumerate(tipos_lista, 1):
                palabras = TIPOS[tipo]
                count = sum(
                    1 for item in pool
                    if any(any(p in a.lower() for p in palabras) for a in item["alertas"])
                )
                print(f"   {i}. {tipo:<22}  {count:>3} registro(s)")

            opcion_volver = len(tipos_lista) + 1
            print(f"   {opcion_volver}. ⬅️  Volver")
            self._mostrar_separador()

            opcion = input(f"Seleccione un tipo (1-{opcion_volver}): ").strip()
            if opcion == str(opcion_volver):
                break

            try:
                idx = int(opcion) - 1
                if not (0 <= idx < len(tipos_lista)):
                    print("❌ Selección inválida.")
                    continue
            except ValueError:
                print("❌ Ingrese un número válido.")
                continue

            tipo_sel = tipos_lista[idx]
            palabras_clave = TIPOS[tipo_sel]

            filtradas = [
                item for item in pool
                if any(any(p in a.lower() for p in palabras_clave) for a in item["alertas"])
            ]

            self._mostrar_encabezado(f"🔍 {tipo_sel.strip()} — {len(filtradas)} registro(s)")

            if not filtradas:
                print(f"\n  ℹ️  No hay registros de tipo '{tipo_sel.strip()}' en el pool actual.")
            else:
                print("=" * 52)
                for item in filtradas:
                    # Buscar datos completos del registro
                    reg = next(
                        (r for r in self.datos
                         if r.get("fecha") == item["fecha"]
                         and r.get("distrito", "").lower() == item["zona"].lower()),
                        None,
                    )
                    print(f"\n📍 ZONA: {item['zona']} | 📅 FECHA: {item['fecha']}")
                    if reg:
                        temp = reg.get("temp", reg.get("temperatura", 0))
                        fuente = reg.get("fuente", "manual")
                        print(
                            f"   🌡️ {temp:.1f}°C | 💧 {reg.get('humedad', 0):.0f}% | "
                            f"💨 {reg.get('viento', 0):.0f} km/h | 🌧️ {reg.get('lluvia', 0):.1f} mm"
                            f" | Fuente: {fuente}"
                        )
                    print("   " + "─" * 45)
                    for alerta in item["alertas"]:
                        if any(p in alerta.lower() for p in palabras_clave):
                            print(f"   🚨 {alerta}")
                print("\n" + "=" * 52)
                print(f"✅ Total: {len(filtradas)} registro(s) con alerta '{tipo_sel.strip()}'.")

            input("\nPresione Enter para continuar...")

    # ─── Salida ───────────────────────────────────────────────────────────────

    def salir(self):
        if sched_module.esta_activo():
            sched_module.detener()
        self._mostrar_encabezado("🚪 CERRANDO SISTEMA")
        print("\n✅ Todos los datos han sido guardados correctamente")
        print("🌍 ¡Gracias por usar The Big Data Theory!")
        print("👋 ¡Hasta pronto!\n")
