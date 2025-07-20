from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
import json
import os

app = Flask(__name__)
CORS(app)

ultimo_registro = None
historico_registros = []
lock = threading.Lock()

def salvar_historico():
    try:
        with open("registos.json", "w", encoding="utf-8") as f:
            json.dump(historico_registros, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar registos.json: {e}")

def rodar_scraper():
    global ultimo_registro, historico_registros
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="estado_logado.json")
        page = context.new_page()
        page.goto("https://www.vemabet4.com/pt/game/football-studio/play-for-real", timeout=60000)
        try:
            page.wait_for_selector('div[class*="historyItem"]', timeout=15000)
        except:
            print("Timeout esperando itens.")
        ultimo_itens = []
        while True:
            registro = None
            for frame in page.frames:
                try:
                    items = frame.query_selector_all('div[class*="historyStatistic"] div[class*="historyItem"]')
                    if items:
                        itens_atual = []
                        for i, item in enumerate(items, start=1):
                            texto = item.inner_text().strip()
                            itens_atual.append({"indice": i, "texto": texto})
                        if itens_atual != ultimo_itens:
                            registro = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "itens": itens_atual
                            }
                        break
                except Exception as e:
                    print(f"Erro ao verificar frame: {e}")

            if registro:
                with lock:
                    ultimo_registro = registro
                    historico_registros.append(registro)
                    salvar_historico()
                ultimo_itens = registro["itens"]
            time.sleep(7)  # clique simulado abaixo
            page.mouse.click(500, 400)
        browser.close()

@app.route("/dados")
def dados():
    with lock:
        if ultimo_registro is None:
            return jsonify({"erro": "Dados ainda não disponíveis, aguarde..."}), 503
        return jsonify(ultimo_registro)

if __name__ == "__main__":
    modo = os.environ.get("MODO", "web")
    if modo == "web":
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    elif modo == "worker":
        rodar_scraper()
