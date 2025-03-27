import network
import uasyncio as asyncio
import socket
import time
import ujson
import ntptime
from machine import Pin
import neopixel

# ===================
# CONFIGURAÇÃO
# ===================
CONFIG = {
    "AP_SSID": "PicoZero_AP",       # Parâmetro mantido, mas não utilizado
    "AP_PASS": "12345678",          # Parâmetro mantido, mas não utilizado
    "EXTERNAL_SSID": "SMS-Home",
    "EXTERNAL_PASS": "@L@N231179",
    "MQTT_PORT": 1883,
    "NTP_HOST": "a.st1.ntp.br",
    "NTP_UPDATE_INTERVAL": 3600,    # em segundos
    "MAX_LOG_LINES": 100,
    "CYCLE_TIMES": {
        "green": 6,    # tempo em segundos para verde
        "yellow": 6,   # tempo em segundos para amarelo
        "red": 15      # tempo em segundos para vermelho
    }
}

# ===================
# CONFIGURAÇÃO DO WS2812B
# ===================
WS2812_PIN = 0  # Altere conforme o seu circuito
NUM_LEDS = 64
np = neopixel.NeoPixel(Pin(WS2812_PIN, Pin.OUT), NUM_LEDS)

def update_panel(state):
    if state == "green":
        color = (0, 255, 0)
    elif state == "yellow":
        color = (255, 255, 0)
    elif state == "red":
        color = (255, 0, 0)
    else:
        color = (0, 0, 0)
    np.fill(color)
    np.write()

# ===================
# VARIÁVEIS GLOBAIS
# ===================
semaforo_state = "green"      # Estado inicial
global_log = []               # Buffer circular de logs
active_connections = []
semaforo_running = False     # Flag do ciclo
last_cycle_trigger_time = 0

# ===================
# FUNÇÕES AUXILIARES: HORÁRIO E LOG
# ===================
def get_time_str():
    t = time.localtime()
    return f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

def log_event(msg):
    global global_log
    timestamp = get_time_str()
    entry = f"[{timestamp}] {msg}"
    global_log.append(entry)
    if len(global_log) > CONFIG["MAX_LOG_LINES"]:
        global_log.pop(0)
    print(entry)

# ===================
# ATUALIZAÇÃO NTP
# ===================
async def ntp_update_loop():
    while True:
        try:
            ntptime.host = CONFIG["NTP_HOST"]
            ntptime.settime()
            log_event("NTP: Horário atualizado")
        except Exception as e:
            log_event("Erro no NTP: " + str(e))
        await asyncio.sleep(CONFIG["NTP_UPDATE_INTERVAL"])

# ===================
# CONFIGURAÇÃO DE REDE: MODO STA (apenas estação)
# ===================
def config_network():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(CONFIG["EXTERNAL_SSID"], CONFIG["EXTERNAL_PASS"])
    while not sta.isconnected():
        time.sleep(0.1)
    log_event(f"Conectado à rede externa: {sta.ifconfig()}")
    return sta.ifconfig()[0]

ip_sta = config_network()

# ===================
# CICLO DO SEMÁFORO
# ===================
async def semaforo_sequence():
    global semaforo_state, semaforo_running
    if semaforo_running:
        log_event("Ciclo já em andamento; ignorando novo acionamento.")
        return
    semaforo_running = True
    log_event("Semáforo acionado via MQTT; iniciando ciclo.")

    semaforo_state = "green"
    log_event("Estado: verde")
    update_panel("green")
    await asyncio.sleep(CONFIG["CYCLE_TIMES"]["green"])

    semaforo_state = "yellow"
    log_event("Estado: amarelo")
    update_panel("yellow")
    await asyncio.sleep(CONFIG["CYCLE_TIMES"]["yellow"])

    semaforo_state = "red"
    log_event("Estado: vermelho")
    update_panel("red")
    await asyncio.sleep(CONFIG["CYCLE_TIMES"]["red"])

    semaforo_state = "green"
    log_event("Ciclo concluído; retornando ao estado verde")
    update_panel("green")
    semaforo_running = False

# ===================
# BROKER MQTT MINIMALISTA
# ===================
async def handle_mqtt_client(reader, writer):
    global last_cycle_trigger_time
    peer = writer.get_extra_info("peername")
    ip = peer[0] if peer else "desconhecido"
    active_connections.append(ip)
    log_event(f"MQTT Conectado: {ip}")
    msg_processed = False
    try:
        data = await reader.read(1024)
        if data:
            log_event(f"MQTT Dados recebidos de {ip}: {data}")
            if data[0] == 0x10:  # CONNECT
                writer.write(b'\x20\x02\x00\x00')
                await writer.drain()
            if data[0] & 0xF0 == 0x30:  # PUBLISH
                topic_length = (data[2] << 8) | data[3]
                topic = data[4:4+topic_length].decode()
                payload = data[4+topic_length:]
                log_event(f"Tópico recebido: '{topic}' com payload: '{payload.decode() if payload else ''}' (IP: {ip})")
                if topic in ["semaforo/acao", "acao/semaforo"]:
                    current_time = time.time()
                    if current_time - last_cycle_trigger_time < 10:
                        log_event(f"Ignorando comando duplicado de {ip}")
                    else:
                        last_cycle_trigger_time = current_time
                        log_event(f"Acionamento via MQTT recebido de {ip}")
                        msg_processed = True
                        asyncio.create_task(semaforo_sequence())
        while True:
            data = await reader.read(1024)
            if not data:
                break
            log_event(f"MQTT Dados adicionais de {ip}: {data}")
            if data[0] == 0xC0:  # PINGREQ
                writer.write(b'\xD0\x00')
                await writer.drain()
            elif not msg_processed and (data[0] & 0xF0 == 0x30):
                topic_length = (data[2] << 8) | data[3]
                topic = data[4:4+topic_length].decode()
                log_event(f"Tópico adicional recebido: '{topic}' (IP: {ip})")
                if topic in ["semaforo/acao", "acao/semaforo"]:
                    current_time = time.time()
                    if current_time - last_cycle_trigger_time < 10:
                        log_event(f"Ignorando comando duplicado de {ip}")
                    else:
                        last_cycle_trigger_time = current_time
                        log_event(f"Acionamento via MQTT recebido de {ip}")
                        msg_processed = True
                        asyncio.create_task(semaforo_sequence())
    except OSError as e:
        if e.args[0] == 104:
            log_event(f"Conexão resetada pelo cliente: {ip}")
        else:
            log_event(f"Erro no cliente MQTT {ip}: {e}")
    except Exception as e:
        log_event(f"Erro inesperado no cliente MQTT {ip}: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            log_event(f"Erro ao fechar conexão com {ip}: {e}")
        if ip in active_connections:
            active_connections.remove(ip)
        log_event(f"MQTT Desconectado: {ip}")

async def mqtt_server():
    server = await asyncio.start_server(handle_mqtt_client, "0.0.0.0", CONFIG["MQTT_PORT"])
    log_event(f"Servidor MQTT rodando na porta {CONFIG['MQTT_PORT']}")
    while True:
        await asyncio.sleep(3600)

# ===================
# SERVIDOR HTTP PARA INTERFACE WEB
# ===================
async def http_handler(reader, writer):
    req_line = await reader.readline()
    if not req_line:
        writer.close()
        return
    req = req_line.decode().split(" ")
    path = req[1] if len(req) > 1 else "/"
    while True:
        line = await reader.readline()
        if line == b'\r\n':
            break

    if path == "/status":
        data = {"semaforo": semaforo_state, "log": global_log}
        res = "HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n" + ujson.dumps(data)
        writer.write(res.encode())
    else:
        html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Semáforo inteligente</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      text-align: center;
      background: #f2f2f2;
      margin: 0;
      padding: 0;
    }
    h1 {
      margin-top: 20px;
    }
    #traffic-light {
      width: 150px;
      margin: 20px auto;
      padding: 20px;
      background: #333;
      border-radius: 20px;
      box-shadow: 0 0 20px rgba(0,0,0,0.8);
    }
    .light {
      width: 100px;
      height: 100px;
      border-radius: 50%;
      margin: 10px auto;
      background: #555;
      box-shadow: inset 0 0 10px rgba(0,0,0,0.7);
      transition: transform 0.3s ease, background 0.3s ease;
    }
    .red {
      background: radial-gradient(circle, #ff4d4d 40%, #b30000 90%);
    }
    .yellow {
      background: radial-gradient(circle, #ffff66 40%, #b3b300 90%);
    }
    .green {
      background: radial-gradient(circle, #66ff66 40%, #009900 90%);
    }
    #log-container {
      width: 90%;
      margin: 0 auto;
    }
    #log-title {
      margin-top: 30px;
      font-size: 1.2em;
      cursor: pointer;
      user-select: none;
    }
    #log {
      width: 100%;
      height: 150px;
      margin: 10px auto;
      border: 1px solid #ccc;
      overflow-y: auto;
      background: #1e1e1e;
      color: #d4d4d4;
      font-family: 'Courier New', monospace;
      font-size: 14px;
      padding: 10px;
      box-sizing: border-box;
      scroll-behavior: smooth;
    }
    #log div {
      padding: 4px;
      border-bottom: 1px solid #333;
    }
    #log div:last-child {
      border-bottom: none;
    }
    #controls {
      margin: 20px;
    }
    button {
      background: #007acc;
      border: none;
      border-radius: 4px;
      color: #fff;
      cursor: pointer;
      padding: 10px 20px;
      font-size: 16px;
      margin: 5px;
      transition: background 0.3s ease;
    }
    button:hover {
      background: #005f99;
    }
    input[type="text"] {
      padding: 10px 15px;
      width: 60%;
      font-size: 16px;
      margin-bottom: 10px;
      border: 2px solid #007acc;
      border-radius: 8px;
      background-color: #fff;
      transition: all 0.3s ease;
      outline: none;
      background-image: url('data:image/svg+xml;utf8,<svg fill="%23007acc" height="16" viewBox="0 0 24 24" width="16" xmlns="http://www.w3.org/2000/svg"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C8.01 14 6 11.99 6 9.5S8.01 5 10.5 5 15 7.01 15 9.5 12.99 14 10.5 14z"/></svg>');
      background-repeat: no-repeat;
      background-position: 10px center;
    }
    input[type="text"]:focus {
      border-color: #005f99;
      box-shadow: 0 0 5px rgba(0,95,153,0.5);
    }
    /* Painel de configuração */
    #config-panel {
      display: none;
      position: fixed;
      top: 20%;
      left: 50%;
      transform: translate(-50%, -20%);
      background: #fff;
      border: 2px solid #007acc;
      border-radius: 10px;
      padding: 20px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 1000;
      width: 80%;
      max-width: 400px;
    }
    #config-panel h2 {
      margin-top: 0;
    }
    #config-panel input[type="text"] {
      width: 90%;
      margin-bottom: 10px;
    }
    #config-panel button {
      margin-top: 10px;
    }
    /* Ícone de configuração */
    #config-icon {
      position: fixed;
      top: 10px;
      right: 10px;
      width: 40px;
      height: 40px;
      background: #007acc;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 1001;
      box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
    #config-icon svg {
      fill: #fff;
      width: 24px;
      height: 24px;
    }
  </style>
</head>
<body>
  <div id="config-icon" title="Configurações">
    <svg viewBox="0 0 24 24">
      <path d="M12 8a4 4 0 100 8 4 4 0 000-8zm8.94 4a7.937 7.937 0 00-.17-1.69l2.12-1.65a.5.5 0 00.12-.64l-2-3.46a.5.5 0 00-.61-.22l-2.49 1a7.936 7.936 0 00-1.45-.85l-.38-2.65A.5.5 0 0014.5 2h-5a.5.5 0 00-.5.43l-.38 2.65a7.936 7.936 0 00-1.45.85l-2.49-1a.5.5 0 00-.61.22l-2 3.46a.5.5 0 00.12.64l2.12 1.65a7.937 7.937 0 000 3.38L2.5 14.34a.5.5 0 00-.12.64l2 3.46a.5.5 0 00.61.22l2.49-1c.45.34.94.62 1.45.85l.38 2.65a.5.5 0 00.5.43h5a.5.5 0 00.5-.43l.38-2.65c.51-.23 1-.51 1.45-.85l2.49 1a.5.5 0 00.61-.22l2-3.46a.5.5 0 00-.12-.64l-2.12-1.65c.11-.55.17-1.13.17-1.69z"/>
    </svg>
  </div>
  <div id="config-panel">
    <h2>Configurações de Rede</h2>
    <form id="config-form">
      <input type="text" id="new-ssid" placeholder="Novo SSID"><br>
      <input type="text" id="new-pass" placeholder="Nova Senha WiFi"><br>
      <input type="text" id="new-ip" placeholder="IP Fixo (ex: 192.168.4.100)"><br>
      <button type="button" id="save-config-btn">Salvar Configurações</button>
      <button type="button" id="close-config-btn">Fechar</button>
    </form>
  </div>
  <h1>Monitoramento do Semáforo</h1>
  <div id="traffic-light">
    <div class="light" id="red-light"></div>
    <div class="light" id="yellow-light"></div>
    <div class="light" id="green-light"></div>
  </div>
  <div id="controls">
    <input type="text" id="search" placeholder="Pesquisar no log...">
    <button id="search-btn">Pesquisar</button>
    <button id="clear-btn">Limpar Log</button>
    <button id="save-csv-btn">Salvar CSV</button>
  </div>
  <div id="log-container">
    <div id="log-title">Log de Eventos</div>
    <div id="log"></div>
  </div>
  <script>
    async function fetchStatus() {
      try {
        let res = await fetch('/status');
        let data = await res.json();

        let redLight = document.getElementById("red-light");
        let yellowLight = document.getElementById("yellow-light");
        let greenLight = document.getElementById("green-light");

        redLight.className = "light";
        yellowLight.className = "light";
        greenLight.className = "light";

        if (data.semaforo === "red") {
          redLight.classList.add("red");
        } else if (data.semaforo === "yellow") {
          yellowLight.classList.add("yellow");
        } else if (data.semaforo === "green") {
          greenLight.classList.add("green");
        }

        let logDiv = document.getElementById("log");
        let logHtml = "";
        for (let entry of data.log) {
          logHtml += "<div>" + entry + "</div>";
        }
        logDiv.innerHTML = logHtml;
        logDiv.scrollTop = logDiv.scrollHeight;
      } catch (e) {
        console.error("Erro ao buscar status:", e);
      }
    }

    function filterLog() {
      let filter = document.getElementById("search").value.toLowerCase();
      let logEntries = document.querySelectorAll("#log div");
      logEntries.forEach(entry => {
        entry.style.display = entry.textContent.toLowerCase().includes(filter) ? "" : "none";
      });
    }

    function downloadCSV() {
      let logDiv = document.getElementById("log");
      let lines = [];
      logDiv.querySelectorAll("div").forEach(div => {
        lines.push(div.textContent);
      });
      let csvContent = lines.join("\\n");
      let blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      let link = document.createElement("a");
      let url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", "logs.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    document.getElementById("search-btn").addEventListener("click", filterLog);
    document.getElementById("clear-btn").addEventListener("click", () => {
      document.getElementById("log").innerHTML = "";
    });
    document.getElementById("save-csv-btn").addEventListener("click", downloadCSV);

    document.getElementById("log-title").addEventListener("click", () => {
      let logDiv = document.getElementById("log");
      logDiv.style.display = (logDiv.style.display === "none") ? "block" : "none";
    });

    document.getElementById("config-icon").addEventListener("click", () => {
      let panel = document.getElementById("config-panel");
      panel.style.display = (panel.style.display === "block") ? "none" : "block";
    });

    document.getElementById("close-config-btn").addEventListener("click", () => {
      document.getElementById("config-panel").style.display = "none";
    });

    document.getElementById("save-config-btn").addEventListener("click", () => {
      let newSsid = document.getElementById("new-ssid").value;
      let newPass = document.getElementById("new-pass").value;
      let newIp = document.getElementById("new-ip").value;
      alert("Configurações salvas (simulação):\\nSSID: " + newSsid + "\\nSenha: " + newPass + "\\nIP Fixo: " + newIp);
      document.getElementById("config-panel").style.display = "none";
    });

    setInterval(fetchStatus, 2000);
    fetchStatus();
  </script>
</body>
</html>"""
        res = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + html
        writer.write(res.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def http_server():
    server = await asyncio.start_server(http_handler, "0.0.0.0", 80)
    log_event("Servidor HTTP rodando na porta 80")
    while True:
        await asyncio.sleep(3600)

async def main():
    asyncio.create_task(mqtt_server())
    asyncio.create_task(http_server())
    asyncio.create_task(ntp_update_loop())
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
