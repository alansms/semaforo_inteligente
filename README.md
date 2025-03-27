# Projeto Semáforo Inteligente em MicroPython (ESP32)

Este projeto implementa um semáforo inteligente rodando em **MicroPython** diretamente em uma placa **ESP32**, oferecendo:

1. **Conexão Wi-Fi** em modo estação, permitindo integração com internet e redes locais.  
2. **Servidor MQTT** embutido, recebendo comandos para acionar transições do semáforo.  
3. **Animações do semáforo** (verde, amarelo, vermelho) com controle de LEDs WS2812B (Neopixel).  
4. **Interface Web** para visualização em tempo real do estado do semáforo, logs e painel de configurações.  
5. **Sincronização de horário via NTP** para manter o relógio do dispositivo alinhado.

---
## Principais Funcionalidades

1. **MicroPython no ESP32**  
   - O código roda inteiramente em **MicroPython** gravado na memória flash do **ESP32**.  
   - Aproveita as bibliotecas nativas (e.g. `network`, `uasyncio`) para lidar com Wi-Fi, sockets, e corrotinas.

2. **Conexão Wi-Fi (estação)**  
   - Após iniciar, o ESP32 conecta-se à rede configurada em `CONFIG["EXTERNAL_SSID"]` e `CONFIG["EXTERNAL_PASS"]`.  
   - Possível adaptar para modo AP ou AP+STA se o firmware ESP32 suportar.

3. **Servidor MQTT minimalista**  
   - O dispositivo atua como **broker** e escuta em `CONFIG["MQTT_PORT"]`.  
   - Mensagens no tópico `semaforo/acao` (ou `acao/semaforo`) disparam o ciclo do semáforo.  
   - Log detalhado de cada conexão e publicação.

4. **Ciclo do Semáforo**  
   - `semaforo_sequence()` executa (verde → amarelo → vermelho) com durações definidas em `CONFIG["CYCLE_TIMES"]`.  
   - LEDs WS2812B são atualizados a cada transição.

5. **Interface Web (HTTP)**  
   - Apresenta um painel HTML com o estado do semáforo e log de eventos em tempo real.  
   - Permite baixar o log em CSV e exibir/ocultar o painel de configurações (SSID e senha de rede).  
   - Responde no IP do ESP32 na porta 80 (exemplo: `http://192.168.1.123/`).

6. **Sincronização de Horário (NTP)**  
   - `ntp_update_loop()` roda em paralelo usando `uasyncio`, atualizando o relógio do dispositivo com o host `CONFIG["NTP_HOST"]`.

---
## Estrutura do Código

- **`CONFIG`**: Armazena SSIDs, senhas, porta MQTT, configurações NTP e tempos do semáforo.
- **`update_panel()`** (ou similar): Ativa os LEDs WS2812B, definindo cores conforme estado (`green`, `yellow`, `red`).
- **`log_event()`**: Função de log que imprime no console e armazena histórico em `global_log`.
- **`semaforo_sequence()`**: Ciclo completo do semáforo, usando `uasyncio` para `sleep` entre estados.
- **`handle_mqtt_client()`**: Trata conexões e mensagens MQTT, disparando o semáforo quando apropriado.
- **`http_handler()`**: Lida com requisições HTTP, oferecendo JSON (`/status`) e uma página HTML com o painel de controle.
- **`main()`**: Tarefa principal que inicia MQTT, HTTP e o loop de NTP em corrotinas (`uasyncio.create_task()`).

---
## Como Executar no ESP32

1. **Instale MicroPython** no ESP32  
   - Use `esptool.py` ou o plugin de firmware no IDE (ex: Thonny) para gravar um binário MicroPython compatível com ESP32.

2. **Carregue o Script**  
   - Conecte via USB, abra o Thonny ou ampy e envie o arquivo `.py` para o ESP32.

3. **Configure Wi-Fi**  
   - Edite `CONFIG["EXTERNAL_SSID"]` e `CONFIG["EXTERNAL_PASS"]` com as credenciais da sua rede.

4. **Rode o Código**  
   - Importe o script no REPL (`import semaforo`) ou defina-o como `main.py`.  
   - O ESP32 tentará conectar à rede Wi-Fi e iniciará o servidor MQTT e HTTP.

5. **Teste MQTT**  
   - Use um cliente MQTT (p. ex. MQTT Explorer) para publicar em `semaforo/acao`.  
   - Observe no console (log) o ciclo do semáforo, e a cor dos LEDs WS2812B mudando no hardware.

6. **Acesse a Interface Web**  
   - No navegador, digite `http://<ip_esp32>` para abrir o painel do semáforo, logs e configurações.

---
## Resolvendo Erros Comuns

- **`OSError: [Errno 2] ENOMEM`** ou falhas de memória:  
  - Reduza o uso de buffers e logs, ou use firmware ESP32 com partição “psRAM” (se disponível em seu módulo).
- **Sem Wi-Fi** (`network.WLAN()` não funciona):  
  - Verifique se o firmware MicroPython corresponde ao chip ESP32.  
  - Alguns firmwares de terceiros desabilitam Wi-Fi.
- **Falha ao acionar semáforo**:  
  - Confira logs no console para ver se o MQTT recebeu mensagem no tópico correto.  
  - Verifique se o script se refere ao pino correto para controlar os LEDs.

---
## Licença

Licenciado sob a [Licença MIT](LICENSE). Use e modifique livremente, lembrando de manter o crédito aos colaboradores.
