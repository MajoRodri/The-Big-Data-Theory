# PyClima Resiliente 🌦️

**Sistema Avanzado de Monitoreo Climático con Detección Inteligente de Riesgos**

Aplicación de consola Python desarrollada como parte del Bootcamp AI4Inclusion para el Ayuntamiento de Madrid, con foco en la experiencia del usuario (UX) y la detección automática de situaciones de riesgo climático.

Aporta datos al Departamento de Resiliencia Urbana y Smart City del Ayuntamiento para activar protocolos de emergencia.

## 📋 Tabla de Contenidos

- [Características Principales](#características-principales)
- [Instalación](#instalación)
- [Cómo Usar](#cómo-usar)
- [Sistema de Alertas](#sistema-de-alertas)
- [Estructura del Proyecto](#estructura-del-proyecto)

## ✨ Características Principales ✨

### 1. **Interfaz Intuitiva**

- Menú principal claro y navegable
- Indicadores visuales para orientar al usuario
- Mensajes de error comprensibles sin crashes

### 2. **Registro Robusto de Datos**

- Captura validada de: Fecha, Zona, Temperatura, Humedad, Viento, Precipitación
- Validación automática contra distritos oficiales de Madrid
- Validación automática de rangos de vaidez de cada dato
- Confirmación antes de guardar
- Prevención de duplicados
- Prevención de fechas futuras

### 3. **Sistema de Alertas Inteligente** ⚠️

Detección automática de **5 tipos principales de riesgos**:

#### 🔴 **Calor Extremo**
- Nivel Crítico: > 45°C
- Nivel Alto: > 35°C

#### 🔴 **Frío Extremo**
- Nivel Crítico: > -2°C
- Nivel Alto: > 2°C

#### 🔴 **Viento Peligroso**
- Nivel Alto: > 40 km/h

#### 🟡 **Humedad Anómala**
- Humedad muy baja < 15% 

#### 🔴 **Precipitación**
- Lluvia intensa > 20 mm 
- Lluvia torrencial > 50 mm

### 4. **Consulta y Análisis**

- Filtrado por zona/distrito/usuario
- Visualización de histórico completo
- Visualización de alertas

## 🚀 Instalación (Rápida) 🚀 

Clonar o descargar el repositorio Si usas Git, ejecuta en una nueva terminal:
Bash git clone (https://github.com/Mary1922/PyClima_Resiliente.git)
cd PyClima_Resiliente

### 1. Crear entorno virtual
``` bash
python -m venv .venv
o bien: 
python3 -m venv .venv
```

### 2. Activar entorno
``` bash
source venv/bin/activate
```

En Windows PowerShell: 
``` bash
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias
``` bash
pip install -r requirements.txt
```

### 4. Ejecutar aplicación
```bash
python main.py
```

## 📖 Cómo Usar 📖

### Menú Principal
```
1. 📋 Registrar Datos Climáticos        
2. 🔍 Consultar Datos                    
3. 📚 Ver Histórico (Todas las Zonas)    
4. 📢 Alertas Activas                   
5. 🔙 Salir 
```

### Flujo de Registro
1. Ingresa fecha (DD/MM/AAAA)
2. Ingresa zona (21 distritos de Madrid)
3. Captura datos: temperatura, humedad, velocidad del viento, precipitaciones (lluvia)
4. Indica si los datos se han validado
5. Analiza alertas automáticamente y las muestra
6. Informa de los datos a guardar y solicita confirmación
7. Confirma o no guardado en JSON

El sistema **nunca falla** con inputs inválidos - solo pide reintentar.

## ⚠️ Sistema de Alertas ⚠️

### Análisis Inteligente
- Detecta automáticamente condiciones de riesgo
- Genera alertas visuales e informativas
- Sugiere acciones recomendadas

### Umbrales Configurables
Está en `alertas.py`:

``` bash
t_roja = umbrales.get("temp_max_roja", 40.0)
    t_naranja = umbrales.get("temp_max_naranja", 35.0)  #Evalúa condiciones climáticas, basadas en umbrales definidos en el sistema
    t_alerta_frio = umbrales.get("temp_min_alerta", 2.0)
    t_emergencia_frio = umbrales.get("temp_min_critica", -5.0)
    ll_roja = umbrales.get("lluvia_roja", 50.0)

UMBRAL_TEMP_CALOR_NARANJA = 35.0      # °C
UMBRAL_TEMP_FRIO_NARANJA = 2.0      # °C
UMBRAL_TEMP_FRIO_ROJA = -5.0      # °C
UMBRAL_VIENTO_ALTO = 40.0     # km/h
UMBRAL_HUMEDAD_BAJA = 15.0    # %
UMBRAL_LLUVIA_NARANJA = 20.0  # mm
UMBRAL_LLUVIA_ROJA = 50.0 # mm
```

## 📁 Estructura del Proyecto 📁

```
PyClima_Resiliente/
├── main.py              → Punto de entrada y autenticación
├── interfaz.py          → Menú principal y operaciones
├── auth.py              → Gestión de usuarios/sesiones
├── persistencia.py      → Lectura/escritura JSON
├── validaciones.py      → Validación de entrada
├── alertas.py           → Evaluación de riesgos climáticos
├── analitica.py         → Generación de gráficos
├── test_completo.py     → Test realizados
├── config.json          → Configuración (umbrales, distritos)
├── datos_clima.json     → Base de datos histórica
├── usuarios.json        → Usuarios registrados
└── empleados.json       → Empleados autorizados
├── requirements.txt    # Dependencias
└── README.md           # Este archivo
└── arquitectura.md     # Arquitectura y funciones 
└── .gitignore          # Especifica archivos o carpetas a ignorar en el repositorio remoto
└── .gittattributes     # Define atributos específicos para ciertos archivos 
└── REPORTE_TESTS.txt   # Resumen fina de pruebas
```

## 👥 Desarrollo

**SCRUM MASTER**
- Coordinación general
- Asignación de tareas y tiempos de desarrollo
- Readme.md y requirements.txt

**DEV 1: Lógica y Product Owner** 
- Lógica principal
- Relación con el cliente
- Interfaz visual (beta)

**DEV 2: Validaciones**
- Definir validación de datos
- Definir ayudas al usuario
- Integrar pasos que no corten el flujo en caso de error

**DEV 3: Persistencia JSON**
- Lectura/escritura base datos
- Validación de datos y evitar duplicados
- Nutrir bbdd

**DEV 4: Interfaz + Alertas**
- Interfaz de consola
- Experiencia del usuario
- Sistema de alertas

## 🧪 Testing

```bash
# Test completo
python test_completo.py
```
```bash
# Resultado de los test 
REPORTE_TESTS.txt
```

## 📝 Estado

- ✅ Interfaz completa
- ✅ Sistema de alertas (4 tipos de riesgos)
- ✅ Validación robusta
- ✅ Testing completo
- ⏳ Integración completa
- 🟡 Interfaz visual (Beta)

---

**Versión**: 1.0  
**Fecha**: 16 de Abril de 2026  
**Bootcamp**: AI4Inclusion - Los Guardianes del Dato
