# src/server.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import persistencia
import api
import api_history
import os

app = Flask(__name__)
CORS(app) # Permite que tu HTML hable con este Python desde otro servidor

# RUTA 1: Obtener el historial completo (GET)
@app.route('/api/historial', methods=['GET'])
def historial():
    datos = persistencia.leer_historico()
    return jsonify(datos)

# RUTA 2: Capturar clima actual (POST)
@app.route('/api/capturar', methods=['POST'])
def capturar():
    distrito = request.json.get('distrito')
    # Usamos tu lógica de api.py
    registro = api.obtener_registro_climatico(distrito)
    if registro:
        persistencia.registrar_nuevo_dato(registro, forzar=True)
        return jsonify({"status": "ok", "msg": f"Capturado {distrito}"}), 200
    return jsonify({"status": "error", "msg": "Fallo en API"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)