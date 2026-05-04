<div align="center">

# 🛡️ The Big Data Theory: Weather Innovators 🛡️

![Logo del Proyecto](docs/logo.png)

<br>

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-Scheduler-FF6B35?style=for-the-badge&logo=clockify&logoColor=white)
![Open-Meteo](https://img.shields.io/badge/Open--Meteo-00B4D8?style=for-the-badge&logo=cloudfoundry&logoColor=white)
![WeatherAPI](https://img.shields.io/badge/WeatherAPI-F5A623?style=for-the-badge&logo=icloud&logoColor=white)
![matplotlib](https://img.shields.io/badge/matplotlib-11557C?style=for-the-badge&logo=plotly&logoColor=white)
![seaborn](https://img.shields.io/badge/seaborn-4C72B0?style=for-the-badge&logo=databricks&logoColor=white)

<br>

![Madrid](https://img.shields.io/badge/🏙️_Madrid-21_Distritos-8338EC?style=for-the-badge)
![Status](https://img.shields.io/badge/Estado-🟢_Activo-2DC653?style=for-the-badge)

<br>

</div>

---

## 🚀 Descripción General

**The Big Data Theory** es un ecosistema diseñado para la gestión, análisis y visualización de datos meteorológicos. El sistema se inicia mediante el comando `python src/main.py`, lo que dispara un flujo de arranque que incluye la configuración de logs, creación de archivos de datos y migración de seguridad legacy.

---

## 🛠️ Instalación y Configuración

<div align="center">

| | Paso | Descripción |
|:---:|:---:|:---|
| 📋 | **Requisitos** | Python 3.8+ instalado en tu sistema |
| 1️⃣ | **Clonar** | Descarga el repositorio en tu máquina |
| 2️⃣ | **Entorno virtual** | Aísla las dependencias del proyecto |
| 3️⃣ | **Dependencias** | Instala las librerías con pip |
| 4️⃣ | **Variables de entorno** | Configura tu API key de WeatherAPI |
| 5️⃣ | **Ejecutar** | Lanza la aplicación principal |
| 6️⃣ | **Tests** | Verifica que todo funciona correctamente |

</div>

<br>

<details>
<summary>📋 &nbsp;<strong>Requisitos Previos</strong></summary>
<br>

Antes de comenzar, asegúrate de tener instalado lo siguiente en tu sistema:

| Herramienta | Versión mínima | Descarga |
|:---:|:---:|:---:|
| **Python** | 3.8+ | [python.org](https://www.python.org/downloads/) |

</details>

<details>
<summary>1️⃣ &nbsp;<strong>Clonar el Repositorio</strong></summary>
<br>

Abre una terminal y ejecuta el siguiente comando para clonar el proyecto en tu máquina local:

```bash
git clone https://github.com/MajoRodri/The-Big-Data-Theory.git
```

Luego, entra en la carpeta del proyecto:

```bash
cd The-Big-Data-Theory
```

</details>

<details>
<summary>2️⃣ &nbsp;<strong>Crear un Entorno Virtual</strong></summary>
<br>

Se recomienda usar un entorno virtual para aislar las dependencias del proyecto:

```bash
# Crear el entorno virtual
python -m venv venv
```

Activa el entorno virtual según tu sistema operativo:

**Windows:**
```bash
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

> Sabrás que el entorno está activo cuando veas `(venv)` al inicio de tu terminal.

</details>

<details>
<summary>3️⃣ &nbsp;<strong>Instalar las Dependencias</strong></summary>
<br>

Con el entorno virtual activo, instala todas las librerías necesarias:

```bash
pip install -r requirements.txt
```

</details>

<details>
<summary>4️⃣ &nbsp;<strong>Configurar las Variables de Entorno</strong></summary>
<br>

El proyecto incluye un archivo `.env.example` en la raíz del repositorio con el ejemplo exacto a seguir. Ábrelo para ver todas las variables disponibles y sus valores por defecto antes de continuar.

**Pasos:**

1. Copia el archivo de ejemplo como `.env`:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

2. Abre el `.env` recién creado y reemplaza los valores de ejemplo con tus credenciales reales. La variable obligatoria es:

```env
WEATHERAPI_API_KEY=tu_api_key_aqui
```

> Puedes obtener una clave gratuita registrándote en [weatherapi.com](https://www.weatherapi.com/).

> **Importante:** el archivo `.env` nunca debe subirse a Git (ya está en `.gitignore`). El archivo `.env.example` sí se versiona porque no contiene secrets.

</details>

<details>
<summary>5️⃣ &nbsp;<strong>Ejecutar la Aplicación</strong></summary>
<br>

Una vez completados los pasos anteriores, lanza el programa con:

```bash
python src/main.py
```

El sistema iniciará el flujo de arranque, configurará los logs y presentará el menú principal.

</details>

<details>
<summary>6️⃣ &nbsp;<strong>Ejecutar los Tests</strong></summary>
<br>

El proyecto incluye una suite de tests automatizados con **pytest** que cubre los módulos principales. Con el entorno virtual activo, ejecútalos desde la raíz del proyecto.

**Ejecutar todos los tests a la vez:**

```bash
pytest tests/ -v
```

**Ejecutar cada módulo de forma individual:**

```bash
# Sistema de alertas meteorológicas
pytest tests/test_alertas.py -v

# Conexión a WeatherAPI y normalización de datos
pytest tests/test_api.py -v

# Persistencia de datos y umbrales
pytest tests/test_persistencia.py -v
```

**¿Qué cubre cada archivo de test?**

| Archivo | Módulo que verifica |
|:---|:---|
| `test_alertas.py` | Evaluación de alertas por calor, frío, viento, lluvia y humedad. Compatibilidad entre esquemas de umbrales. |
| `test_api.py` | Conexión a WeatherAPI, manejo de errores HTTP (404, 401, 429, 500, timeout) y normalización de respuestas. |
| `test_persistencia.py` | Lectura/escritura de umbrales en el archivo de configuración y obtención de distritos permitidos. |

> Si todos los tests pasan correctamente verás una línea final con `X passed` en verde. Si alguno falla, pytest indicará exactamente qué función falló y el motivo.

</details>

---

## ✨ Características Principales

<details>
<summary>🔐 <strong>Seguridad y Autenticación</strong></summary>
<br>

Sistema de inicio de sesión y registro con migración automática de hashes de contraseñas antiguos.

</details>

<details>
<summary>⏲️ <strong>Ingesta de Datos Multimodal</strong></summary>
<br>

| Modo | 📝 Descripción |
| :---: | :--- |
| 🤖 **Automática** | Un programador (`APScheduler`) en segundo plano captura datos en tres horarios configurables. |
| 🖱️ **Manual** | Ingreso de datos por distrito y fecha cuando la API no está disponible. |
| ⏪ **Retroactiva** | Recuperación masiva de datos para todos los distritos en fechas pasadas usando `api_history.py`. |

</details>

<details>
<summary>📊 <strong>Analítica Visual</strong></summary>
<br>

Generación de reportes y gráficas avanzadas (barras, comparativas interanuales y medias anuales) con `matplotlib` y `seaborn`.

</details>

<details>
<summary>⚠️ <strong>Sistema de Alertas</strong></summary>
<br>

Monitoreo en tiempo real de umbrales para calor, frío, viento, lluvia y humedad.

</details>

<details>
<summary>💾 <strong>Persistencia Robusta</strong></summary>
<br>

Gestión de datos en `datos_clima.json` con capacidades de exportación a CSV y creación de backups.

</details>

---

## 🏗️ Arquitectura del Sistema (Capas)

| 🗂️ Módulo | ⚙️ Responsabilidad |
| :---: | :--- |
| 🚪 **`main.py`** | Punto de entrada, configuración de `logger` y presentación visual inicial. |
| 🖥️ **`interfaz.py`** | Implementa `InterfazTBDT`, manejando toda la lógica de navegación y menús. |
| 🌐 **`api.py` / `api_history.py`** | Gestión de datos en tiempo real y consultas al archivo histórico de Open-Meteo. |
| 📈 **`analitica.py`** | Motor de procesamiento estadístico y visualización de datos. |
| 💽 **`persistencia.py`** | Manejo de lectura/escritura de archivos JSON y gestión de umbrales. |
| 🔑 **`auth.py`** | Gestión de usuarios, validaciones y cifrado de credenciales. |

---

## 📜 Reglas de Negocio "Golden Rules"

<details>
<summary>🏅 <strong>Ver las Golden Rules</strong> — Para garantizar la calidad de la información (Data Integrity)</summary>
<br>

| # | 📏 Regla | 📝 Descripción |
|:---:|:---|:---|
| 1️⃣ | **Control de Duplicados** | Se admite un único registro de fuente API por combinación de fecha y distrito. |
| 2️⃣ | **Política de Edición** | Los registros solo pueden ser editados una vez, únicamente si son de origen manual y por el usuario que los creó. |
| 3️⃣ | **Smart Cache** | El sistema detecta fuentes de tipo "historico" para optimizar las llamadas a la API y evitar redundancias. |
| 4️⃣ | **Escritura Eficiente** | El guardado en lote (`batch`) asegura que se realice una sola operación de escritura por cada ciclo del sistema. |

</details>

---

## 🖥️ Flujo de Usuario (`InterfazTBDT`)

El sistema guía al usuario a través de un árbol de menús intuitivo:

| Paso | 📌 Acción |
|:---:|:---|
| 1️⃣ | 📥 **Carga de Datos**: Encendido del scheduler, configuración de horarios e ingestas manuales. |
| 2️⃣ | 🔍 **Consulta y Edición**: Búsqueda por fecha/distrito y gestión de registros propios. |
| 3️⃣ | 🛠️ **Utilidades**: Exportación a CSV y generación de backups de seguridad. |
| 4️⃣ | 📊 **Estadísticas**: Visualización de métricas generales y paneles gráficos comparativos. |
| 5️⃣ | 🚨 **Alertas**: Revisión del historial reciente de alertas meteorológicas configuradas. |

---

<div align="center">

Desarrollado con pasión por el equipo de **The Big Data Theory**. ⛈️📈

<br>

![Made with love](https://img.shields.io/badge/Hecho_con-❤️_y_☕-E63946?style=for-the-badge)
![Team](https://img.shields.io/badge/Team-The_Big_Data_Theory-1D3557?style=for-the-badge&logo=github&logoColor=white)

</div>
