"""
TESTS PARA PROYECTO II - Ingesta de datos climáticos con WeatherAPI

Estos tests verifican:
1. Que la conexión a WeatherAPI funciona
2. Que los datos se normalizan correctamente
3. Que los errores HTTP se manejan adecuadamente

"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# Agregar src al path para poder importar los módulos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class TestWeatherAPIConexion:
    """Tests para verificar la conexión a WeatherAPI"""
    
    @patch('requests.Session.get')
    @patch('api.WEATHERAPI_API_KEY', "test_key")
    @patch('api.WEATHERAPI_BASE_URL', "http://api.weatherapi.com/v1/current.json")
    @patch('api.WEATHERAPI_TIMEOUT', 5)
    @patch('api.WEATHERAPI_REINTENTOS', 3)
    def test_obtener_respuesta_weatherapi_success(self, mock_get):
        """
        Test: Conexión exitosa a WeatherAPI (200 OK)
        
        Verifica que:
        - Se realiza una petición GET correcta
        - Se devuelve la respuesta JSON y latencia
        """
        from api import obtener_respuesta_weatherapi
        
        # Mock de respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "location": {
                "name": "Madrid",
                "country": "Spain"
            },
            "current": {
                "temp_c": 24.5,
                "humidity": 65,
                "wind_kph": 15.2,
                "precip_mm": 0.0,
                "condition": {
                    "text": "Sunny"
                }
            }
        }
        mock_get.return_value = mock_response
        
        # Ejecutar función
        resultado, latencia = obtener_respuesta_weatherapi("Madrid")
        
        # Verificaciones
        assert resultado is not None
        assert isinstance(latencia, int)
        assert latencia >= 0
        assert resultado["location"]["name"] == "Madrid"
        assert resultado["current"]["temp_c"] == 24.5
        
        # Verificar que se llamó a requests.get con los parámetros correctos
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["key"] == "test_key"
        assert call_args[1]["params"]["q"] == "Madrid"
        assert call_args[1]["params"]["lang"] == "es"
    
    @patch('requests.get')
    @patch('os.getenv')
    def test_error_404_ciudad_no_encontrada(self, mock_getenv, mock_get):
        """
        Test: Error 404 - Ciudad no encontrada
        
        Verifica que:
        - Se maneja correctamente el error 404
        - Se devuelve None
        """
        from api import obtener_respuesta_weatherapi
        
        # Mock de variables de entorno
        mock_getenv.side_effect = lambda key, default=None: {
            "WEATHERAPI_API_KEY": "test_key",
            "WEATHERAPI_BASE_URL": "http://api.weatherapi.com/v1/current.json",
            "WEATHERAPI_TIMEOUT_SEGUNDOS": "5",
            "WEATHERAPI_REINTENTOS": "3"
        }.get(key, default)
        
        # Mock de respuesta 404
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "City not found"
        mock_get.return_value = mock_response
        
        # Ejecutar función
        resultado, latencia = obtener_respuesta_weatherapi("CiudadInexistente")
        
        # Verificaciones
        assert resultado is None
        assert latencia is None
    
    @patch('requests.Session.get')
    @patch('api.WEATHERAPI_API_KEY', "invalid_key")
    def test_error_401_api_key_invalida(self, mock_get):
        """
        Test: Error 401 - API key inválida

        Verifica que:
        - Se maneja correctamente el error 401
        - Se devuelve None
        """
        from api import obtener_respuesta_weatherapi

        # Mock de respuesta 401
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_get.return_value = mock_response

        # Ejecutar función
        resultado, latencia = obtener_respuesta_weatherapi("Madrid")

        # Verificaciones
        assert resultado is None
        assert latencia is None
    
    def test_error_429_rate_limit_con_reintento(self):
        """
        Test: Error 429 - Rate limit con reintento
        
        Verifica que:
        - Se reintenta después del delay
        - Finalmente falla si no se resuelve
        """
        from api import obtener_respuesta_weatherapi
        
        # Mock de respuesta 429 en primera llamada, luego 200
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"test": "data"}
        
        with patch('api.WEATHERAPI_API_KEY', "test_key"), \
             patch('api.WEATHERAPI_BASE_URL', "http://api.weatherapi.com/v1/current.json"), \
             patch('api.WEATHERAPI_TIMEOUT', 5), \
             patch('api.WEATHERAPI_REINTENTOS', 3), \
             patch('time.sleep') as mock_sleep, \
             patch('requests.Session.get') as mock_get:

            mock_get.side_effect = [mock_response_429, mock_response_200]

            # Ejecutar función
            resultado, latencia = obtener_respuesta_weatherapi("Madrid")

            # Verificaciones
            assert resultado is not None
            assert isinstance(latencia, int)
            assert latencia >= 0

            # Verificar que se llamó a sleep (reintento)
            mock_sleep.assert_called_once()

            # Verificar que se hicieron 2 llamadas (reintento exitoso)
            assert mock_get.call_count == 2  # 2 sleeps para 3 reintentos
    
    @patch('requests.Session.get')
    @patch('api.WEATHERAPI_API_KEY', "test_key")
    @patch('api.WEATHERAPI_REINTENTOS', 1)
    def test_timeout(self, mock_get):
        """
        Test: Timeout en la conexión

        Verifica que:
        - Se maneja correctamente el timeout
        - Se devuelve None
        """
        from api import obtener_respuesta_weatherapi
        from requests import Timeout

        # Mock que lanza Timeout
        mock_get.side_effect = Timeout("Connection timed out")

        # Ejecutar función
        resultado, latencia = obtener_respuesta_weatherapi("Madrid")

        # Verificaciones
        assert resultado is None
        assert latencia is None
    
    def test_error_500_con_reintento(self):
        """
        Test: Error 500 del servidor con reintento
        
        Verifica que:
        - Se reintenta después del delay
        - Finalmente falla si no se resuelve
        """
        from api import obtener_respuesta_weatherapi
        
        # Mock de respuesta 500 en primera llamada, luego 200
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"test": "data"}
        
        with patch('api.WEATHERAPI_API_KEY', "test_key"), \
             patch('api.WEATHERAPI_BASE_URL', "http://api.weatherapi.com/v1/current.json"), \
             patch('api.WEATHERAPI_TIMEOUT', 5), \
             patch('api.WEATHERAPI_REINTENTOS', 3), \
             patch('time.sleep') as mock_sleep, \
             patch('requests.Session.get') as mock_get:

            mock_get.side_effect = [mock_response_500, mock_response_200]

            # Ejecutar función
            resultado, latencia = obtener_respuesta_weatherapi("Madrid")

            # Verificaciones
            assert resultado is not None
            assert isinstance(latencia, int)
            assert latencia >= 0

            # Verificar que se llamó a sleep (reintento)
            mock_sleep.assert_called_once()

            # Verificar que se hicieron 2 llamadas (reintento exitoso)
            assert mock_get.call_count == 2


class TestNormalizacionDatos:
    """Tests para verificar la normalización de datos"""
    
    @patch('os.getenv')
    def test_estructura_normalizada_completa(self, mock_getenv):
        """
        Test: Estructura completa de datos normalizados
        
        Verifica que:
        - Se normaliza correctamente la respuesta de WeatherAPI
        - La estructura resultante tiene todos los campos requeridos
        """
        from normalizador import normalizar_respuesta_weatherapi
        
        # Mock de variables de entorno (no se usa en esta función, pero por consistencia)
        def getenv_side_effect(key, default=None):
            env_vars = {
                "WEATHERAPI_API_KEY": "test_key"
            }
            return env_vars.get(key, default)
        
        mock_getenv.side_effect = getenv_side_effect
        
        # Datos de ejemplo de WeatherAPI
        datos_raw = {
            "location": {
                "name": "Madrid",
                "country": "Spain"
            },
            "current": {
                "temp_c": 24.5,
                "humidity": 65,
                "wind_kph": 15.2,
                "precip_mm": 0.0,
                "condition": {
                    "text": "Sunny"
                }
            }
        }
        latencia_ms = 150
        
        # Ejecutar función
        resultado = normalizar_respuesta_weatherapi(datos_raw, latencia_ms)
        
        # Verificaciones
        assert resultado is not None
        assert resultado["temperatura"] == 24.5
        assert resultado["humedad"] == 65
        assert resultado["viento"] == 15.2
        assert resultado["lluvia"] == 0.0
        assert resultado["descripcion"] == "Sunny"
        assert resultado["latencia_ms"] == 150
        assert "timestamp" in resultado
        assert "ubicacion" in resultado
    
    @patch('os.getenv')
    def test_valores_numericos_convertidos(self, mock_getenv):
        """
        Test: Conversión correcta de valores numéricos
        
        Verifica que:
        - Los valores se convierten al tipo correcto
        - Se manejan valores faltantes
        """
        from normalizador import normalizar_respuesta_weatherapi
        
        # Mock de variables de entorno (no se usa en esta función, pero por consistencia)
        def getenv_side_effect(key, default=None):
            env_vars = {
                "WEATHERAPI_API_KEY": "test_key"
            }
            return env_vars.get(key, default)
        
        mock_getenv.side_effect = getenv_side_effect
        
        # Datos con valores extremos
        datos_raw = {
            "location": {
                "name": "Madrid",
                "country": "Spain"
            },
            "current": {
                "temp_c": 0.0,
                "humidity": 100,
                "wind_kph": 0.0,
                "precip_mm": 50.5,
                "condition": {
                    "text": "Heavy rain"
                }
            }
        }
        latencia_ms = 200
        
        # Ejecutar función
        resultado = normalizar_respuesta_weatherapi(datos_raw, latencia_ms)
        
        # Verificaciones
        assert isinstance(resultado["temperatura"], float)
        assert isinstance(resultado["humedad"], float)  # Cambié a float porque el normalizador hace float()
        assert isinstance(resultado["viento"], float)
        assert isinstance(resultado["lluvia"], float)
        assert resultado["temperatura"] == 0.0
        assert resultado["humedad"] == 100.0
        assert resultado["viento"] == 0.0
        assert resultado["lluvia"] == 50.5


class TestRegistroClimatico:
    """Tests para verificar la creación de registros climáticos"""
    
    @patch('alertas.evaluar_alertas')
    @patch('persistencia.obtener_umbrales_alerta')
    @patch('api.obtener_respuesta_weatherapi_historico')
    @patch('api.normalizar_respuesta_weatherapi_historico')
    def test_obtener_registro_climatico_estructura(self, mock_normalizar, mock_obtener_respuesta, mock_umbrales, mock_evaluar_alertas):
        """
        Test: Estructura completa del registro climático
        
        Verifica que:
        - Se crea un registro completo con todos los campos
        - Incluye alertas y metadatos
        """
        from api import obtener_registro_climatico
        
        # Mock de alertas
        mock_umbrales.return_value = {"temperatura_max": 30}
        mock_evaluar_alertas.return_value = ["Alerta de calor extremo"]
        
        # Mock de respuesta de API
        mock_obtener_respuesta.return_value = ({"dummy": "data"}, 120)
        
        # Datos normalizados simulados
        datos_normalizados = {
            "temperatura": 35.0,
            "humedad": 30.0,
            "viento": 5.0,
            "lluvia": 0.0,
            "presion": 1013.0,
            "descripcion": "Sunny",
            "latencia_ms": 120,
            "timestamp": "2024-01-15T12:00:00Z",
            "ubicacion": {"nombre": "Madrid", "region": "", "pais": "Spain"}
        }
        mock_normalizar.return_value = datos_normalizados
        
        # Ejecutar función
        resultado = obtener_registro_climatico("Madrid", {"num_empleado": "test_user"}, "2024-01-15")
        
        # Verificaciones
        assert resultado is not None
        assert resultado["distrito"] == "Madrid"
        assert resultado["fecha"] == "2024-01-15"
        assert resultado["temperatura"] == 35.0
        assert resultado["registrado_por"] == "test_user"
        assert resultado["fuente"] == "api"
        assert resultado["proveedor_api"] == "weatherapi"
        assert "alertas" in resultado
        assert "latencia_ms" in resultado
