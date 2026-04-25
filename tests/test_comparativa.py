"""
Tests para src/comparativa.py

Ejecutar con:
    pytest tests/test_comparativa.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from comparativa import detectar_discrepancias, mostrar_tabla_comparativa


def _reg(distrito, fecha, temp, fuente="manual"):
    return {
        "distrito": distrito,
        "fecha": fecha,
        "temperatura": temp,
        "temp": temp,
        "fuente": fuente,
        "humedad": 50.0,
        "viento": 10.0,
        "lluvia": 0.0,
    }


class TestDetectarDiscrepancias:

    def test_sin_datos_retorna_lista_vacia(self):
        assert detectar_discrepancias([]) == []

    def test_solo_registros_manuales_sin_comparativa(self):
        historico = [_reg("Centro", "2026-01-01", 20.0, "manual")]
        assert detectar_discrepancias(historico) == []

    def test_solo_registros_api_sin_comparativa(self):
        historico = [_reg("Centro", "2026-01-01", 20.0, "api")]
        assert detectar_discrepancias(historico) == []

    def test_par_manual_api_sin_conflicto(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-01", 21.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 1
        assert resultado[0]["conflicto"] is False
        assert resultado[0]["diferencia"] == 1.0

    def test_par_manual_api_con_conflicto(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-01", 25.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 1
        assert resultado[0]["conflicto"] is True
        assert resultado[0]["diferencia"] == 5.0

    def test_umbral_personalizado(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-01", 21.5, "api"),
        ]
        # Con umbral 1.0 debería ser conflicto
        resultado_estricto = detectar_discrepancias(historico, umbral_diferencia=1.0)
        assert resultado_estricto[0]["conflicto"] is True

        # Con umbral 3.0 no debería ser conflicto
        resultado_laxo = detectar_discrepancias(historico, umbral_diferencia=3.0)
        assert resultado_laxo[0]["conflicto"] is False

    def test_distritos_distintos_no_se_mezclan(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Retiro", "2026-01-01", 25.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 0

    def test_fechas_distintas_no_se_mezclan(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-02", 25.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 0

    def test_multiples_pares_ordenados_por_fecha_descendente(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-01", 22.0, "api"),
            _reg("Retiro", "2026-01-05", 18.0, "manual"),
            _reg("Retiro", "2026-01-05", 19.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 2
        assert resultado[0]["fecha"] >= resultado[1]["fecha"]

    def test_insensible_a_mayusculas_en_distrito(self):
        historico = [
            _reg("centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-01", 25.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 1

    def test_estructura_retornada(self):
        historico = [
            _reg("Centro", "2026-01-01", 20.0, "manual"),
            _reg("Centro", "2026-01-01", 23.0, "api"),
        ]
        d = detectar_discrepancias(historico)[0]
        assert "zona" in d
        assert "fecha" in d
        assert "temp_manual" in d
        assert "temp_api" in d
        assert "diferencia" in d
        assert "conflicto" in d

    def test_campo_fuente_ausente_trata_como_manual(self):
        historico = [
            {"distrito": "Centro", "fecha": "2026-01-01", "temperatura": 20.0, "temp": 20.0},
            _reg("Centro", "2026-01-01", 23.0, "api"),
        ]
        resultado = detectar_discrepancias(historico)
        assert len(resultado) == 1


class TestMostrarTablaComparativa:

    def test_sin_discrepancias_no_lanza_excepcion(self, capsys):
        mostrar_tabla_comparativa([])
        out = capsys.readouterr().out
        assert "No se encontraron" in out

    def test_muestra_filas_con_datos(self, capsys):
        discrepancias = [
            {"zona": "Centro", "fecha": "2026-01-01", "temp_manual": 20.0,
             "temp_api": 25.0, "diferencia": 5.0, "conflicto": True},
        ]
        mostrar_tabla_comparativa(discrepancias)
        out = capsys.readouterr().out
        assert "Centro" in out
        assert "2026-01-01" in out
        assert "CONFLICTO" in out

    def test_muestra_ok_cuando_sin_conflicto(self, capsys):
        discrepancias = [
            {"zona": "Retiro", "fecha": "2026-01-02", "temp_manual": 20.0,
             "temp_api": 20.5, "diferencia": 0.5, "conflicto": False},
        ]
        mostrar_tabla_comparativa(discrepancias)
        out = capsys.readouterr().out
        assert "OK" in out
