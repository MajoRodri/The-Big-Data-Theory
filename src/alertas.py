def evaluar_alertas(datos_registro, umbrales): #Creamos función
    alertas_activas = []
    
    temp = float(datos_registro.get("temperatura", 0))
    viento = float(datos_registro.get("viento", 0))
    humedad = float(datos_registro.get("humedad", 0))
    lluvia = float(datos_registro.get("lluvia", 0)) 

    t_roja = umbrales.get("temp_max_roja", 40.0)
    t_naranja = umbrales.get("temp_max_naranja", 35.0)  #Evalúa condiciones climáticas, basadas en umbrales definidos en el sistema
    t_alerta_frio = umbrales.get("temp_min_alerta", 2.0)
    t_emergencia_frio = umbrales.get("temp_min_critica", -5.0)
    v_max = umbrales.get("viento_max", 40)
    h_min = umbrales.get("humedad_min", 15)
    ll_naranja = umbrales.get("lluvia_naranja", 20.0)
    ll_roja = umbrales.get("lluvia_roja", 50.0)

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