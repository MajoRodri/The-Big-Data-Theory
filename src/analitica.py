import json
import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import mplcyberpunk
import persistencia

plt.style.use("cyberpunk")
sns.set_context("notebook", font_scale=1.1)

ARCHIVO_BASE = persistencia.ARCHIVO_JSON

_BG    = '#212946'
_MEDIA = '#e74c3c'
_FRIO  = '#3498db'
_CALOR = '#f39c12'


def generar_reporte_distrito_especifico(distrito_preseleccionado=None):
    if not os.path.exists(ARCHIVO_BASE):
        print("Archivo de datos no encontrado.")
        return

    try:
        with open(ARCHIVO_BASE, "r", encoding="utf-8") as f:
            datos = json.load(f)

        if not datos:
            print("No hay datos en la base de datos.")
            return

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error al cargar datos: {e}")
        return

    distritos_unicos = sorted(set(d.get("distrito", "Desconocido") for d in datos))

    if not distritos_unicos:
        print("No hay distritos registrados en la base de datos.")
        return

    if distrito_preseleccionado:
        distrito_seleccionado = distrito_preseleccionado
        if distrito_seleccionado not in distritos_unicos:
            print(f"No existe informacion para el distrito: {distrito_seleccionado}")
            return
    else:
        print("\n" + "=" * 50)
        print("DISTRITOS DISPONIBLES:")
        print("=" * 50)
        for i, distrito in enumerate(distritos_unicos, 1):
            print(f"   {i}. {distrito}")
        print("=" * 50)

        try:
            seleccion = int(input("\nSelecciona el numero del distrito (o 0 para cancelar): "))

            if seleccion == 0:
                print("Operacion cancelada.")
                return

            if seleccion < 1 or seleccion > len(distritos_unicos):
                print("Seleccion invalida. Introduce un numero de la lista.")
                return

            distrito_seleccionado = distritos_unicos[seleccion - 1]

        except ValueError:
            print("Introduce un numero valido.")
            return

    datos_distrito = [d for d in datos if d.get("distrito", "") == distrito_seleccionado]

    if not datos_distrito:
        print(f"No hay registros para {distrito_seleccionado}.")
        return

    fechas = [d.get("fecha", "N/A") for d in datos_distrito]
    temperaturas = [d.get("temp", d.get("temperatura", 0)) for d in datos_distrito]

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=_BG)
    ax.set_facecolor(_BG)

    ax.plot(
        range(len(fechas)), temperaturas,
        marker="o", linewidth=2, markersize=6,
        color=_MEDIA, label="Temperatura",
    )

    media_distrito = np.mean(temperaturas)
    ax.axhline(y=media_distrito, color=_FRIO, linestyle="--", linewidth=2,
               label=f"Media del distrito: {media_distrito:.2f} C")

    temps_frio = [t for t in temperaturas if t < media_distrito]
    temps_calor = [t for t in temperaturas if t > media_distrito]
    media_frio = np.mean(temps_frio) if temps_frio else media_distrito
    media_calor = np.mean(temps_calor) if temps_calor else media_distrito

    ax.axhline(y=media_frio, color='#2980b9', linestyle=":", linewidth=1.5, alpha=0.7,
               label=f"Media Frio: {media_frio:.2f} C")
    ax.axhline(y=media_calor, color=_CALOR, linestyle=":", linewidth=1.5, alpha=0.7,
               label=f"Media Calor: {media_calor:.2f} C")

    ax.fill_between(range(len(fechas)), temperaturas, alpha=0.3, color=_MEDIA)

    ax.set_title(f"EVOLUCION TERMICA - {distrito_seleccionado.upper()}", fontweight="bold", fontsize=14)
    ax.set_xlabel("Registros historicos (fechas)", fontweight="bold")
    ax.set_ylabel("Temperatura (C)", fontweight="bold")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)

    step = max(1, len(fechas) // 10)
    ax.set_xticks(range(0, len(fechas), step))
    ax.set_xticklabels([fechas[i] for i in range(0, len(fechas), step)], rotation=45, ha="right")

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 50)
    print(f"ESTADISTICAS DE {distrito_seleccionado}:")
    print("=" * 50)
    print(f"   Total de registros: {len(datos_distrito)}")
    print(f"   Temperatura media: {media_distrito:.2f} C")
    print(f"   Temperatura maxima: {max(temperaturas):.2f} C")
    print(f"   Temperatura minima: {min(temperaturas):.2f} C")

    temps_frio = [t for t in temperaturas if t < media_distrito]
    temps_calor = [t for t in temperaturas if t > media_distrito]
    media_frio = np.mean(temps_frio) if temps_frio else media_distrito
    media_calor = np.mean(temps_calor) if temps_calor else media_distrito

    print(f"   ---")
    print(f"   Media de Frio: {media_frio:.2f} C ({len(temps_frio)} registros)")
    print(f"   Media de Calor: {media_calor:.2f} C ({len(temps_calor)} registros)")
    print("=" * 50 + "\n")


NOMBRES_MES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def generar_comparativa_mensual_historica(datos_mes, mes):
    """Compara la media mensual por distrito a través de los años disponibles en el histórico."""
    from collections import defaultdict

    por_anio_distrito = defaultdict(lambda: defaultdict(list))
    for d in datos_mes:
        fecha = d.get("fecha", "")
        temp = d.get("temp", d.get("temperatura"))
        distrito = d.get("distrito", "Desconocido")
        if len(fecha) >= 4 and temp is not None:
            por_anio_distrito[fecha[:4]][distrito].append(float(temp))

    if not por_anio_distrito:
        print("❌ No hay temperaturas válidas para ese mes.")
        return

    anios = sorted(por_anio_distrito.keys())
    distritos = sorted(set(
        d for datos_anio in por_anio_distrito.values() for d in datos_anio
    ))

    nombre_mes = NOMBRES_MES.get(mes, str(mes))

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=_BG)
    ax.set_facecolor(_BG)

    colores = sns.color_palette("magma", len(distritos))

    for i, distrito in enumerate(distritos):
        anios_con_datos = []
        medias_distrito = []
        for anio in anios:
            temps = por_anio_distrito[anio].get(distrito, [])
            if temps:
                anios_con_datos.append(anio)
                medias_distrito.append(sum(temps) / len(temps))
        if medias_distrito:
            ax.plot(
                anios_con_datos, medias_distrito,
                marker="o", linewidth=2, markersize=6,
                color=colores[i], label=distrito,
            )

    ax.set_title(f"Comparativa histórica de {nombre_mes} — Media por distrito y año", fontweight="bold")
    ax.set_xlabel("Año")
    ax.set_ylabel("Temperatura media (C)")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    ancho_nombre = 26
    ancho_col = 10
    print(f"\n{'='*60}")
    print(f"ESTADÍSTICAS — {nombre_mes.upper()} POR DISTRITO Y AÑO:")
    print(f"{'='*60}")
    encabezado = f"{'Distrito':<{ancho_nombre}}" + "".join(f"{a:>{ancho_col}}" for a in anios)
    print(encabezado)
    print("-" * 60)
    for distrito in distritos:
        fila = f"   {distrito:<{ancho_nombre - 3}}"
        for anio in anios:
            temps = por_anio_distrito[anio].get(distrito, [])
            if temps:
                fila += f"{sum(temps)/len(temps):>{ancho_col}.2f}C"
            else:
                fila += f"{'—':>{ancho_col}}"
        print(fila)
    print(f"{'='*60}\n")


def generar_comparativa_anual(datos, por_distrito=True):
    """Compara medias anuales de temperatura por distrito o globales, para todos los años disponibles."""
    from collections import defaultdict

    if por_distrito:
        por_anio_distrito = defaultdict(lambda: defaultdict(list))
        for d in datos:
            fecha = d.get("fecha", "")
            temp = d.get("temp", d.get("temperatura"))
            distrito = d.get("distrito", "Desconocido")
            if len(fecha) >= 4 and temp is not None:
                por_anio_distrito[fecha[:4]][distrito].append(float(temp))

        if not por_anio_distrito:
            print("❌ No hay temperaturas válidas en el histórico.")
            return

        anios = sorted(por_anio_distrito.keys())
        distritos = sorted(set(
            d for datos_anio in por_anio_distrito.values() for d in datos_anio
        ))

        fig, ax = plt.subplots(figsize=(12, 6), facecolor=_BG)
        ax.set_facecolor(_BG)

        colores = sns.color_palette("magma", len(distritos))

        for i, distrito in enumerate(distritos):
            anios_con_datos = []
            medias_distrito = []
            for anio in anios:
                temps = por_anio_distrito[anio].get(distrito, [])
                if temps:
                    anios_con_datos.append(anio)
                    medias_distrito.append(sum(temps) / len(temps))
            if medias_distrito:
                ax.plot(
                    anios_con_datos, medias_distrito,
                    marker="o", linewidth=2, markersize=6,
                    color=colores[i], label=distrito,
                )

        ax.set_title("Comparativa anual — Media de temperatura por distrito", fontweight="bold")
        ax.set_xlabel("Año")
        ax.set_ylabel("Temperatura media (C)")
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

        ancho_nombre = 26
        ancho_col = 10
        print(f"\n{'='*60}")
        print("ESTADÍSTICAS ANUALES POR DISTRITO:")
        print(f"{'='*60}")
        encabezado = f"{'Distrito':<{ancho_nombre}}" + "".join(f"{a:>{ancho_col}}" for a in anios)
        print(encabezado)
        print("-" * 60)
        for distrito in distritos:
            fila = f"   {distrito:<{ancho_nombre - 3}}"
            for anio in anios:
                temps = por_anio_distrito[anio].get(distrito, [])
                if temps:
                    fila += f"{sum(temps)/len(temps):>{ancho_col}.2f}C"
                else:
                    fila += f"{'—':>{ancho_col}}"
            print(fila)
        print(f"{'='*60}\n")

    else:
        por_anio = defaultdict(list)
        for d in datos:
            fecha = d.get("fecha", "")
            temp = d.get("temp", d.get("temperatura"))
            if len(fecha) >= 4 and temp is not None:
                por_anio[fecha[:4]].append(float(temp))

        if not por_anio:
            print("❌ No hay temperaturas válidas en el histórico.")
            return

        anios = sorted(por_anio.keys())
        medias = [sum(por_anio[a]) / len(por_anio[a]) for a in anios]

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
                   label=f"Media histórica: {media_historica:.2f} C")
        ax.axhline(y=media_frio, color=_FRIO, linestyle=":", alpha=0.7,
                   label=f"Media Frío: {media_frio:.2f} C")
        ax.axhline(y=media_calor, color=_CALOR, linestyle=":", alpha=0.7,
                   label=f"Media Calor: {media_calor:.2f} C")

        ax.set_title("Media general de temperatura por año", fontweight="bold")
        ax.set_xlabel("Año")
        ax.set_ylabel("Temperatura media (C)")
        ax.legend()
        plt.tight_layout()
        plt.show()

        print(f"\n{'='*50}")
        print("ESTADÍSTICAS — MEDIA GENERAL ANUAL:")
        print(f"{'='*50}")
        for a, m in zip(anios, medias):
            print(f"   {a}: {m:.2f} C  ({len(por_anio[a])} registros)")
        print(f"   ---")
        print(f"   Media histórica: {media_historica:.2f} C")
        print(f"   Media Frío:      {media_frio:.2f} C")
        print(f"   Media Calor:     {media_calor:.2f} C")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    generar_reporte_distrito_especifico()
