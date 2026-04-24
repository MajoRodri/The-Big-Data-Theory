"""
Tests para src/persistencia.py

Ejecutar con:
    pytest tests/test_persistencia.py -v
"""

import sys
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import persistencia


def _config_con_umbrales(umbrales: dict) -> dict:
    return {"distritos_oficiales": ["Centro", "Retiro"], "umbrales": umbrales}


class TestObtenerUmbralesAlerta:

    def test_devuelve_umbrales_existentes(self, tmp_path):
        config_path = tmp_path / "config.json"
        umbrales = {"temp_max_roja": 40.0, "temperatura_max": 40.0}
        config_path.write_text(json.dumps({"umbrales": umbrales}), encoding="utf-8")

        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            resultado = persistencia.obtener_umbrales_alerta()

        assert resultado["temp_max_roja"] == 40.0
        assert resultado["temperatura_max"] == 40.0

    def test_devuelve_dict_vacio_si_no_hay_archivo(self, tmp_path):
        ruta_inexistente = tmp_path / "no_existe.json"
        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", ruta_inexistente):
            resultado = persistencia.obtener_umbrales_alerta()
        assert resultado == {}

    def test_devuelve_dict_vacio_si_no_hay_clave_umbrales(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"distritos_oficiales": []}), encoding="utf-8")
        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            resultado = persistencia.obtener_umbrales_alerta()
        assert resultado == {}


class TestActualizarUmbralesAlerta:

    def test_actualiza_nuevo_esquema_y_deriva_viejo(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_inicial = _config_con_umbrales({
            "temp_max_roja": 40.0,
            "temp_max_naranja": 35.0,
            "temp_min_critica": -5.0,
            "temp_min_alerta": 2.0,
            "viento_max": 40,
            "lluvia_roja": 50.0,
            "lluvia_naranja": 20.0,
            "humedad_min": 15,
        })
        config_path.write_text(json.dumps(config_inicial), encoding="utf-8")

        nuevos = {
            "temperatura_max": 38.0,
            "temperatura_min": -3.0,
            "viento_max": 45,
            "humedad_max": 90.0,
            "lluvia_max": 60.0,
        }

        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            resultado = persistencia.actualizar_umbrales_alerta(nuevos)
            umbrales_guardados = persistencia.obtener_umbrales_alerta()

        assert resultado is True
        # Nuevas claves guardadas
        assert umbrales_guardados["temperatura_max"] == 38.0
        assert umbrales_guardados["lluvia_max"] == 60.0
        # Claves antiguas derivadas correctamente
        assert umbrales_guardados["temp_max_roja"] == 38.0
        assert umbrales_guardados["temp_max_naranja"] == 33.0
        assert umbrales_guardados["temp_min_critica"] == -3.0
        assert umbrales_guardados["lluvia_roja"] == 60.0

    def test_preserva_distritos_al_actualizar_umbrales(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_inicial = {
            "distritos_oficiales": ["Centro", "Retiro"],
            "umbrales": {"temp_max_roja": 40.0},
        }
        config_path.write_text(json.dumps(config_inicial), encoding="utf-8")

        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            persistencia.actualizar_umbrales_alerta({"temperatura_max": 38.0})
            config_final = json.loads(config_path.read_text(encoding="utf-8"))

        assert config_final["distritos_oficiales"] == ["Centro", "Retiro"]

    def test_crea_config_si_no_existe(self, tmp_path):
        config_path = tmp_path / "nuevo_config.json"

        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            resultado = persistencia.actualizar_umbrales_alerta({"temperatura_max": 38.0})
            assert resultado is True
            assert config_path.exists()

    def test_merge_preserva_clave_existente_no_incluida(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_inicial = _config_con_umbrales({"viento_max": 40, "humedad_min": 15})
        config_path.write_text(json.dumps(config_inicial), encoding="utf-8")

        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            persistencia.actualizar_umbrales_alerta({"temperatura_max": 38.0})
            umbrales = persistencia.obtener_umbrales_alerta()

        # humedad_min y viento_max no se tocan si no están en nuevos_umbrales
        assert umbrales["humedad_min"] == 15


class TestObtenerDistritosPermitidos:

    def test_devuelve_lista_de_distritos(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps({"distritos_oficiales": ["Centro", "Retiro"]}),
            encoding="utf-8",
        )
        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", config_path):
            distritos = persistencia.obtener_distritos_permitidos()
        assert "Centro" in distritos
        assert "Retiro" in distritos

    def test_devuelve_lista_vacia_si_no_hay_archivo(self, tmp_path):
        ruta_inexistente = tmp_path / "no_existe.json"
        with patch.object(persistencia, "CONFIGURACION_DE_ARCHIVO", ruta_inexistente):
            resultado = persistencia.obtener_distritos_permitidos()
        assert resultado == []
