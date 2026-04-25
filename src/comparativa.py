"""
Módulo de comparativa Manual vs. API para The Big Data Theory.
Detecta discrepancias entre registros manuales y datos obtenidos de la API
para el mismo distrito y fecha.
"""

import logging

logger = logging.getLogger(__name__)

UMBRAL_DIFERENCIA_DEFAULT = 2.0


def detectar_discrepancias(historico, umbral_diferencia=UMBRAL_DIFERENCIA_DEFAULT):
    """
    Compara registros manuales vs. API para el mismo distrito+fecha.

    Retorna lista de dicts ordenada por fecha descendente:
      {zona, fecha, temp_manual, temp_api, diferencia, conflicto}
    """
    grupos = {}
    for reg in historico:
        clave = (reg.get("distrito", "").strip().lower(), reg.get("fecha", ""))
        if clave not in grupos:
            grupos[clave] = {"manual": [], "api": []}
        fuente = reg.get("fuente", "manual")
        if fuente == "api":
            grupos[clave]["api"].append(reg)
        else:
            grupos[clave]["manual"].append(reg)

    comparativas = []
    for (distrito_lower, fecha), registros in grupos.items():
        if not registros["manual"] or not registros["api"]:
            continue

        reg_manual = registros["manual"][0]
        reg_api = registros["api"][0]
        temp_manual = float(reg_manual.get("temperatura", reg_manual.get("temp", 0)))
        temp_api = float(reg_api.get("temperatura", reg_api.get("temp", 0)))
        diferencia = round(abs(temp_manual - temp_api), 1)
        conflicto = diferencia >= umbral_diferencia

        comparativas.append({
            "zona": reg_manual.get("distrito", distrito_lower),
            "fecha": fecha,
            "temp_manual": temp_manual,
            "temp_api": temp_api,
            "diferencia": diferencia,
            "conflicto": conflicto,
        })

        if conflicto:
            logger.warning(
                "Discrepancia detectada | Zona: %s | Fecha: %s | "
                "Manual: %.1f°C | API: %.1f°C | Diff: %.1f°C",
                reg_manual.get("distrito", distrito_lower),
                fecha,
                temp_manual,
                temp_api,
                diferencia,
            )

    comparativas.sort(key=lambda x: x["fecha"], reverse=True)
    return comparativas


def mostrar_tabla_comparativa(comparativas):
    """Imprime la tabla Zona | Fecha | Temp Manual | Temp API | Diferencia en consola."""
    if not comparativas:
        print("\nℹ️  No se encontraron zonas con datos de ambas fuentes para comparar.")
        return

    col_zona = 26
    col_fecha = 12
    col_temp = 13
    col_diff = 9

    encabezado = (
        f"{'Zona':<{col_zona}}"
        f"{'Fecha':<{col_fecha}}"
        f"{'T.Manual(°C)':<{col_temp}}"
        f"{'T.API(°C)':<{col_temp}}"
        f"{'Diff(°C)':<{col_diff}}"
        f"Estado"
    )
    separador = "─" * (col_zona + col_fecha + col_temp * 2 + col_diff + 15)

    print(f"\n{encabezado}")
    print(separador)

    for d in comparativas:
        estado = "⚠️  CONFLICTO" if d["conflicto"] else "✅ OK"
        print(
            f"{d['zona']:<{col_zona}}"
            f"{d['fecha']:<{col_fecha}}"
            f"{d['temp_manual']:<{col_temp}.1f}"
            f"{d['temp_api']:<{col_temp}.1f}"
            f"{d['diferencia']:<{col_diff}.1f}"
            f"{estado}"
        )

    total = len(comparativas)
    conflictos = sum(1 for d in comparativas if d["conflicto"])
    print(separador)
    print(f"📊 Total comparativas: {total}  |  ⚠️  Conflictos detectados: {conflictos}")
