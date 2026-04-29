"""
Módulo de evaluación de alertas climáticas para The Big Data Theory.
Evalúa umbrales de temperatura, viento, lluvia y humedad sobre un registro.
"""


def evaluar_alertas(datos_registro: dict, umbrales: dict) -> list:
    """
    Evalúa un registro climático contra los umbrales configurados.

    Args:
        datos_registro (dict): Registro con temperatura, humedad, viento y lluvia.
        umbrales (dict): Umbrales leídos desde config.json (compatible con esquema
                         antiguo y nuevo).

    Returns:
        list: Lista de strings con las alertas activas. Vacía si no hay alertas.
    """
    alertas_activas = []

    temp = float(datos_registro.get("temperatura", 0))
    viento = float(datos_registro.get("viento", 0))
    humedad = float(datos_registro.get("humedad", 0))
    lluvia = float(datos_registro.get("lluvia", 0))

    # Compatibilidad: acepta esquema antiguo (temp_max_roja) y nuevo (temperatura_max)
    t_roja = umbrales.get("temp_max_roja", umbrales.get("temperatura_max", 40.0))
    t_naranja = umbrales.get("temp_max_naranja", round(t_roja - 5.0, 1))
    t_alerta_frio = umbrales.get("temp_min_alerta", umbrales.get("temperatura_min", -5.0) + 5.0)
    t_emergencia_frio = umbrales.get("temp_min_critica", umbrales.get("temperatura_min", -5.0))
    v_max = umbrales.get("viento_max", 40)
    h_min = umbrales.get("humedad_min", 15)
    ll_naranja = umbrales.get("lluvia_naranja", umbrales.get("lluvia_max", 50.0) * 0.4)
    ll_roja = umbrales.get("lluvia_roja", umbrales.get("lluvia_max", 50.0))

    if temp >= t_roja:
        alertas_activas.append(f"🔴 PELIGRO DE CALOR EXTREMO: Alerta Roja. Ola de calor ({temp}°C).")
    elif temp >= t_naranja:
        alertas_activas.append(f"🟠 RIESGO IMPORTANTE: Alerta Naranja. Temperatura elevada ({temp}°C).")

    if temp <= t_emergencia_frio:
        alertas_activas.append(f"🔴 PELIGRO DE HELADA: Alerta Roja. Frío extremo ({temp}°C). Riesgo infraestructuras.")
    elif temp <= t_alerta_frio:
        alertas_activas.append(f"🟠 RIESGO IMPORTANTE: Riesgo de helada preventiva ({temp}°C).")

    if viento >= v_max:
        alertas_activas.append(f"🟠 VIENTO: Rachas de {viento} km/h. Riesgo en parques.")

    if lluvia >= ll_roja:
        alertas_activas.append(f"🔴 PELIGRO DE LLUVIA TORRENCIAL: Alerta Roja. Tormenta ({lluvia} mm).")
    elif lluvia >= ll_naranja:
        alertas_activas.append(f"🟠 RIESGO IMPORTANTE: Alerta Naranja. Lluvia intensa ({lluvia} mm).")

    if humedad <= h_min:
        alertas_activas.append(f"🔴 RIESGO MUY ALTO: Humedad muy baja ({humedad}%). Peligro de incendio.")

    return alertas_activas