"""
Tests para src/alertas.py

Ejecutar con:
    pytest tests/test_alertas.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from alertas import evaluar_alertas


UMBRALES_OLD = {
    "temp_max_roja": 40.0,
    "temp_max_naranja": 35.0,
    "temp_min_critica": -5.0,
    "temp_min_alerta": 2.0,
    "viento_max": 40,
    "humedad_min": 15,
    "lluvia_roja": 50.0,
    "lluvia_naranja": 20.0,
}

UMBRALES_NEW = {
    "temperatura_max": 40.0,
    "temperatura_min": -5.0,
    "viento_max": 40,
    "humedad_max": 95.0,
    "lluvia_max": 50.0,
}

UMBRALES_BOTH = {**UMBRALES_OLD, **UMBRALES_NEW}


class TestEvaluarAlertasEsquemaAntiguo:

    def test_sin_alertas_condiciones_normales(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 15.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert resultado == []

    def test_alerta_calor_roja(self):
        datos = {"temperatura": 41.0, "humedad": 40.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("CALOR EXTREMO" in a or "calor" in a.lower() for a in resultado)

    def test_alerta_calor_naranja(self):
        datos = {"temperatura": 36.0, "humedad": 40.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("NARANJA" in a or "elevada" in a.lower() for a in resultado)

    def test_alerta_helada_critica(self):
        datos = {"temperatura": -6.0, "humedad": 60.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("HELADA" in a or "helada" in a.lower() or "frio" in a.lower() for a in resultado)

    def test_alerta_frio_preventivo(self):
        datos = {"temperatura": 1.0, "humedad": 60.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("helada preventiva" in a.lower() or "helada" in a.lower() for a in resultado)

    def test_alerta_viento(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 50.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("VIENTO" in a or "viento" in a.lower() for a in resultado)

    def test_alerta_lluvia_roja(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 10.0, "lluvia": 55.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("TORRENCIAL" in a or "tormenta" in a.lower() for a in resultado)

    def test_alerta_lluvia_naranja(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 10.0, "lluvia": 25.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("LLUVIA" in a or "lluvia intensa" in a.lower() for a in resultado)

    def test_alerta_humedad_baja(self):
        datos = {"temperatura": 25.0, "humedad": 10.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("humedad" in a.lower() or "incendio" in a.lower() for a in resultado)

    def test_multiples_alertas(self):
        datos = {"temperatura": 42.0, "humedad": 10.0, "viento": 50.0, "lluvia": 55.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert len(resultado) >= 3


class TestEvaluarAlertasEsquemaNewSchemaCompatibilidad:

    def test_nuevo_esquema_sin_alertas(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 15.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_NEW)
        assert resultado == []

    def test_nuevo_esquema_alerta_calor(self):
        datos = {"temperatura": 41.0, "humedad": 40.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_NEW)
        assert len(resultado) >= 1

    def test_nuevo_esquema_alerta_lluvia(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 10.0, "lluvia": 55.0}
        resultado = evaluar_alertas(datos, UMBRALES_NEW)
        assert len(resultado) >= 1

    def test_esquema_combinado(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 15.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_BOTH)
        assert resultado == []

    def test_umbrales_vacios_usa_defaults(self):
        datos = {"temperatura": 20.0, "humedad": 60.0, "viento": 15.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, {})
        assert resultado == []


class TestEvaluarAlertasValoresLimite:

    def test_exactamente_en_umbral_rojo_calor(self):
        datos = {"temperatura": 40.0, "humedad": 50.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert any("CALOR EXTREMO" in a or "calor" in a.lower() for a in resultado)

    def test_justo_por_debajo_umbral_naranja(self):
        datos = {"temperatura": 34.9, "humedad": 50.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert not any("NARANJA" in a or "elevada" in a.lower() for a in resultado)

    def test_retorna_lista(self):
        datos = {"temperatura": 20.0, "humedad": 50.0, "viento": 10.0, "lluvia": 0.0}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert isinstance(resultado, list)

    def test_campos_faltantes_en_datos_no_crashea(self):
        datos = {}
        resultado = evaluar_alertas(datos, UMBRALES_OLD)
        assert isinstance(resultado, list)
