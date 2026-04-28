import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import mplcyberpunk

plt.style.use("cyberpunk")
sns.set_context("notebook", font_scale=1.1)

_BG    = '#212946'
_MEDIA = '#e74c3c'
_FRIO  = '#3498db'
_CALOR = '#f39c12'


NOMBRES_MES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


_CAMPO_MAGNITUD = {
    "temperatura": lambda r: r.get("temperatura", r.get("temp")),
    "humedad":     lambda r: r.get("humedad"),
    "viento":      lambda r: r.get("viento"),
    "lluvia":      lambda r: r.get("lluvia"),
}

_ETIQUETA_MAGNITUD = {
    "temperatura": "Temperatura (°C)",
    "humedad":     "Humedad (%)",
    "viento":      "Viento (km/h)",
    "lluvia":      "Lluvia (mm)",
}


def grafica_comparativa_distritos(datos, fecha, magnitud="temperatura"):
    """
    Gráfica de barras con la magnitud elegida para los 21 distritos de Madrid en una fecha exacta.

    Args:
        datos: Lista completa de registros climáticos.
        fecha: Fecha exacta en formato AAAA-MM-DD.
        magnitud: Campo a visualizar: 'temperatura', 'humedad', 'viento' o 'lluvia'.
    """
    extractor = _CAMPO_MAGNITUD.get(magnitud, _CAMPO_MAGNITUD["temperatura"])
    datos_fecha = [r for r in datos if r.get("fecha") == fecha]

    por_distrito: dict = {}
    for r in datos_fecha:
        dist = r.get("distrito", "")
        val = extractor(r)
        if dist and val is not None:
            por_distrito.setdefault(dist, []).append(float(val))

    if not por_distrito:
        print(f"❌ No hay datos disponibles para la fecha {fecha}.")
        return

    distritos = sorted(por_distrito.keys())
    valores = [sum(por_distrito[d]) / len(por_distrito[d]) for d in distritos]
    etiqueta = _ETIQUETA_MAGNITUD.get(magnitud, magnitud)

    fig, ax = plt.subplots(figsize=(14, 6), facecolor=_BG)
    ax.set_facecolor(_BG)

    media = np.mean(valores)
    vals_frio = [v for v in valores if v <= media]
    vals_calor = [v for v in valores if v > media]
    media_frio = np.mean(vals_frio) if vals_frio else media
    media_calor = np.mean(vals_calor) if vals_calor else media

    colores = sns.color_palette("magma", len(distritos))
    ax.bar(range(len(distritos)), valores, color=colores, zorder=2)

    ax.axhline(y=media, color=_MEDIA, linestyle="--", linewidth=2,
               label=f"Media general: {media:.1f}")
    ax.axhline(y=media_frio, color=_FRIO, linestyle=":", linewidth=1.5, alpha=0.85,
               label=f"Media frío: {media_frio:.1f}")
    ax.axhline(y=media_calor, color=_CALOR, linestyle=":", linewidth=1.5, alpha=0.85,
               label=f"Media calor: {media_calor:.1f}")

    ax.set_xticks(range(len(distritos)))
    ax.set_xticklabels(distritos, rotation=45, ha="right", fontsize=8)
    ax.set_title(
        f"Comparativa por Distritos — {etiqueta} | {fecha}",
        fontweight="bold", fontsize=13,
    )
    ax.set_xlabel("Distrito")
    ax.set_ylabel(etiqueta)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y", zorder=1)

    plt.tight_layout()
    plt.show()

    rango = max(valores) - min(valores)
    print(f"\n{'='*55}")
    print(f"COMPARATIVA {etiqueta.upper()} — {fecha}")
    print(f"{'='*55}")
    for d, v in zip(distritos, valores):
        barra = "█" * int((v - min(valores)) / max(rango, 1) * 20)
        print(f"   {d:<26} {v:6.1f}  {barra}")
    print(f"   {'─'*50}")
    print(f"   {'Media general':26} {media:6.1f}")
    print(f"   {'Media frío':26} {media_frio:6.1f}  ({len(vals_frio)} distritos)")
    print(f"   {'Media calor':26} {media_calor:6.1f}  ({len(vals_calor)} distritos)")
    print(f"{'='*55}\n")


def grafica_comparativa_mensual_interanual(datos, distrito, mes, anio1, anio2):
    """
    Gráfica de líneas que superpone las temperaturas diarias de un mismo mes en dos años distintos.
    Permite detectar anomalías interanuales para un distrito concreto.

    Args:
        datos: Lista completa de registros climáticos.
        distrito: Nombre oficial del distrito a analizar.
        mes: Mes como entero 1-12.
        anio1: Primer año a comparar (entero).
        anio2: Segundo año a comparar (entero).
    """
    nombre_mes_str = NOMBRES_MES.get(mes, str(mes))
    mes_str = f"{mes:02d}"

    def filtrar(anio):
        return sorted(
            [
                r for r in datos
                if r.get("distrito", "").lower() == distrito.lower()
                and r.get("fecha", "")[:4] == str(anio)
                and r.get("fecha", "")[5:7] == mes_str
            ],
            key=lambda r: r.get("fecha", ""),
        )

    datos1 = filtrar(anio1)
    datos2 = filtrar(anio2)

    if not datos1 and not datos2:
        print(
            f"❌ No hay datos para {distrito} en {nombre_mes_str} "
            f"de {anio1} ni {anio2}."
        )
        return

    dias1 = [int(r.get("fecha", "0000-00-00")[-2:]) for r in datos1]
    temps1 = [r.get("temp", r.get("temperatura", 0)) for r in datos1]
    dias2 = [int(r.get("fecha", "0000-00-00")[-2:]) for r in datos2]
    temps2 = [r.get("temp", r.get("temperatura", 0)) for r in datos2]

    todos_temps = temps1 + temps2
    media_general = np.mean(todos_temps) if todos_temps else 0
    temps_frio = [t for t in todos_temps if t <= media_general]
    temps_calor = [t for t in todos_temps if t > media_general]
    media_frio = np.mean(temps_frio) if temps_frio else media_general
    media_calor = np.mean(temps_calor) if temps_calor else media_general

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=_BG)
    ax.set_facecolor(_BG)

    if datos1:
        ax.plot(
            dias1, temps1,
            marker="o", linewidth=2, markersize=5,
            color=_FRIO, label=f"{nombre_mes_str} {anio1}",
        )
        ax.fill_between(dias1, temps1, alpha=0.15, color=_FRIO)

    if datos2:
        ax.plot(
            dias2, temps2,
            marker="s", linewidth=2, markersize=5,
            color=_CALOR, label=f"{nombre_mes_str} {anio2}",
        )
        ax.fill_between(dias2, temps2, alpha=0.15, color=_CALOR)

    ax.axhline(y=media_general, color=_MEDIA, linestyle="--", linewidth=1.5,
               label=f"Media general: {media_general:.2f}°C")
    ax.axhline(y=media_frio, color=_FRIO, linestyle=":", linewidth=1.2, alpha=0.6,
               label=f"Media Frío: {media_frio:.2f}°C")
    ax.axhline(y=media_calor, color=_CALOR, linestyle=":", linewidth=1.2, alpha=0.6,
               label=f"Media Calor: {media_calor:.2f}°C")

    ax.set_title(
        f"Comparativa Mensual Interanual — {nombre_mes_str} | {distrito}\n"
        f"{anio1} vs {anio2}",
        fontweight="bold", fontsize=13,
    )
    ax.set_xlabel(f"Día de {nombre_mes_str}")
    ax.set_ylabel("Temperatura (°C)")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    max_dia = max(
        max(dias1, default=1),
        max(dias2, default=1),
    )
    ax.set_xlim(0.5, max_dia + 0.5)

    plt.tight_layout()
    plt.show()

    print(f"\n{'='*55}")
    print(f"COMPARATIVA {nombre_mes_str.upper()} — {distrito.upper()}")
    print(f"{'='*55}")
    if datos1:
        med1 = sum(temps1) / len(temps1)
        print(f"   {anio1}: media {med1:.2f}°C  ({len(temps1)} días con datos)")
    else:
        print(f"   {anio1}: sin datos")
    if datos2:
        med2 = sum(temps2) / len(temps2)
        print(f"   {anio2}: media {med2:.2f}°C  ({len(temps2)} días con datos)")
    else:
        print(f"   {anio2}: sin datos")
    if datos1 and datos2:
        print(f"   Diferencia: {med2 - med1:+.2f}°C")
    print(f"   ---")
    print(f"   Media general:  {media_general:.2f}°C")
    print(f"   Media Frío:     {media_frio:.2f}°C")
    print(f"   Media Calor:    {media_calor:.2f}°C")
    print(f"{'='*55}\n")


def grafica_comparativa_anual_api(medias_por_anio: dict):
    """
    Bar chart con la media anual de temperatura de Madrid consultada directamente
    desde la API (sin guardar en la BD). Muestra media general, frío y calor.

    Args:
        medias_por_anio: Diccionario {str(anio): float(media_temp)}.
    """
    if not medias_por_anio:
        print("❌ No hay datos para generar la gráfica.")
        return

    anios = sorted(medias_por_anio.keys())
    medias = [medias_por_anio[a] for a in anios]

    media_historica = np.mean(medias)
    temps_frio = [t for t in medias if t <= media_historica]
    temps_calor = [t for t in medias if t > media_historica]
    media_frio = np.mean(temps_frio) if temps_frio else media_historica
    media_calor = np.mean(temps_calor) if temps_calor else media_historica

    fig, ax = plt.subplots(figsize=(max(8, len(anios) * 2), 6), facecolor=_BG)
    ax.set_facecolor(_BG)

    sns.barplot(
        x=anios, y=medias, palette="magma",
        hue=anios, legend=False, linewidth=0, errorbar=None, ax=ax,
    )

    ax.axhline(y=media_historica, color=_MEDIA, linestyle="--",
               label=f"Media general: {media_historica:.2f}°C")
    ax.axhline(y=media_frio, color=_FRIO, linestyle=":", alpha=0.7,
               label=f"Media Frío: {media_frio:.2f}°C")
    ax.axhline(y=media_calor, color=_CALOR, linestyle=":", alpha=0.7,
               label=f"Media Calor: {media_calor:.2f}°C")

    ax.set_title("Comparativa Anual — Media de temperatura de Madrid", fontweight="bold")
    ax.set_xlabel("Año")
    ax.set_ylabel("Temperatura media (°C)")
    ax.legend()
    plt.tight_layout()
    plt.show()

    print(f"\n{'='*50}")
    print("ESTADÍSTICAS — COMPARATIVA ANUAL MADRID:")
    print(f"{'='*50}")
    for a, m in zip(anios, medias):
        print(f"   {a}: {m:.2f}°C")
    print(f"   ---")
    print(f"   Media general:  {media_historica:.2f}°C")
    print(f"   Media Frío:     {media_frio:.2f}°C")
    print(f"   Media Calor:    {media_calor:.2f}°C")
    print(f"{'='*50}\n")


