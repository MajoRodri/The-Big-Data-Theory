import json
import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import persistencia

ARCHIVO_BASE = persistencia.ARCHIVO_JSON       #Archivo JSON con los datos historicos de clima


def generar_reporte_visual_pro():    #Para generar la gráfica con temperaturas por distrito
    if not os.path.exists(ARCHIVO_BASE):  #Valida la existencia del archivo de datos
        return

    try:
        with open(ARCHIVO_BASE, "r", encoding="utf-8") as f:  #Carga los datos y filtrado
            datos = json.load(f)
        pares_validos = [
            (d.get("distrito", "Desconocido"), d.get("temp", d.get("temperatura")))
            for d in datos
            if d.get("temp", d.get("temperatura")) is not None
        ]
        distritos = [distrito for distrito, _ in pares_validos]
        temps = [temp for _, temp in pares_validos]

        if not temps:
            return

    except (json.JSONDecodeError, KeyError):
        return

    sns.set_theme(style="white")
    plt.figure(figsize=(10, 6))

    sns.barplot(
        x=distritos,
        y=temps,
        palette="magma",
        hue=distritos,
        legend=False,
        linewidth=0,
        errorbar=None,
    )

    media = np.mean(temps)
    plt.axhline(
        y=media,
        color="#e74c3c",
        linestyle="--",
        label=f"Media: {media:.2f} C",
    )

    temps_frio = [t for t in temps if t < media]
    temps_calor = [t for t in temps if t > media]
    media_frio = np.mean(temps_frio) if temps_frio else media
    media_calor = np.mean(temps_calor) if temps_calor else media

    plt.axhline(
        y=media_frio,
        color="#3498db",
        linestyle=":",
        alpha=0.7,
        label=f"Media Frio: {media_frio:.2f} C",
    )

    plt.axhline(
        y=media_calor,
        color="#f39c12",
        linestyle=":",
        alpha=0.7,
        label=f"Media Calor: {media_calor:.2f} C",
    )

    plt.title("Perfil termico por distrito (Media general)", fontweight="bold")
    plt.ylabel("Temperatura (C)")
    plt.legend()
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.show()


def generar_reporte_distrito_especifico(distrito_preseleccionado=None):   #Genera gráfica de evolución térmica para un distrito específico
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

    sns.set_theme(style="white")
    plt.figure(figsize=(12, 6))

    plt.plot(
        range(len(fechas)),
        temperaturas,
        marker="o",
        linewidth=2,
        markersize=6,
        color="#e74c3c",
        label="Temperatura",
    )

    media_distrito = np.mean(temperaturas)
    plt.axhline(
        y=media_distrito,
        color="#3498db",
        linestyle="--",
        linewidth=2,
        label=f"Media del distrito: {media_distrito:.2f} C",
    )

    temps_frio = [t for t in temperaturas if t < media_distrito]
    temps_calor = [t for t in temperaturas if t > media_distrito]
    media_frio = np.mean(temps_frio) if temps_frio else media_distrito
    media_calor = np.mean(temps_calor) if temps_calor else media_distrito

    plt.axhline(
        y=media_frio,
        color="#2980b9",
        linestyle=":",
        linewidth=1.5,
        alpha=0.7,
        label=f"Media Frio: {media_frio:.2f} C",
    )

    plt.axhline(
        y=media_calor,
        color="#e67e22",
        linestyle=":",
        linewidth=1.5,
        alpha=0.7,
        label=f"Media Calor: {media_calor:.2f} C",
    )

    plt.fill_between(range(len(fechas)), temperaturas, alpha=0.3, color="#e74c3c")

    plt.title(f"EVOLUCION TERMICA - {distrito_seleccionado.upper()}", fontweight="bold", fontsize=14)
    plt.xlabel("Registros historicos (fechas)", fontweight="bold")
    plt.ylabel("Temperatura (C)", fontweight="bold")
    plt.legend(loc="best", fontsize=10)
    plt.grid(True, alpha=0.3)

    step = max(1, len(fechas) // 10)
    plt.xticks(
        range(0, len(fechas), step),
        [fechas[i] for i in range(0, len(fechas), step)],
        rotation=45,
        ha="right",
    )

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


if __name__ == "__main__":
    generar_reporte_visual_pro()
