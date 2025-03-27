# Projeto Semáforo Inteligente com Raspberry Pi Pico W

Este projeto implementa um semáforo inteligente, com controle remoto via MQTT e interface web para monitoramento em tempo real. Além disso, há sincronização de horário via NTP e animações de LEDs WS2812B para representar os estados do semáforo (verde, amarelo e vermelho).

---

## Recursos Principais

1. **Wi-Fi (STA)**  
   - O Raspberry Pi Pico W conecta-se a uma rede Wi-Fi configurada em `CONFIG["EXTERNAL_SSID"]` e `CONFIG["EXTERNAL_PASS"]`.

2. **MQTT Broker Minimalista**  
   - O dispositivo atua como um servidor MQTT na porta definida em `CONFIG["MQTT_PORT"]`.
   - Quando recebe mensagens no tópico `semaforo/acao` (ou `acao/semaforo`), inicia o ciclo do semáforo (verde → amarelo → vermelho).

3. **Interface Web com Painel de Configurações**  
   - Exibe o estado do semáforo e um log de eventos.
   - Permite baixar o log em CSV e possui um painel de configurações de rede (simulado).

4. **NTP para Sincronização de Horário**  
   - Periodicamente, o código atualiza o relógio do sistema via NTP.

5. **Logs de Eventos**  
   - Mantém um buffer circular de registros (tamanho máximo em `CONFIG["MAX_LOG_LINES"]`).
   - Os registros são exibidos no console e pela interface web.

6. **LEDs WS2812B (NeoPixel)**  
   - Mostram visualmente o estado do semáforo.
   - Pin definido em `WS2812_PIN` e número de LEDs em `NUM_LEDS`.

---

## Estrutura do Código

- **`CONFIG`**: Dicionário com parâmetros de rede, MQTT, NTP e tempos do semáforo.
- **`semaforo_state`**: Estado global do semáforo (`"green"`, `"yellow"`, `"red"`).
- **`log_event()`**: Função de log que imprime no console e guarda registros no buffer `global_log`.
- **`ntp_update_loop()`**: Tarefa assíncrona para atualização de hora via NTP.
- **`config_network()`**: Conecta o Pico W em modo estação (`STA`) à rede Wi-Fi externa.
- **`semaforo_sequence()`**: Corrotina (async) que realiza o ciclo do semáforo quando acionado via MQTT.
- **`handle_mqtt_client()`**: Lida com novas conexões MQTT, interpretando mensagens de `PUBLISH`.
- **`mqtt_server()`**: Tarefa assíncrona que inicia o servidor MQTT.
- **`update_panel(state)`**: Define a cor dos LEDs WS2812B (verde, amarelo, vermelho).
- **`http_handler()`**: Atende requisições HTTP, exibindo a interface e status do semáforo em JSON.
- **`http_server()`**: Tarefa assíncrona que inicia o servidor HTTP na porta 80.
- **`main()`**: Cria e inicia as corrotinas (MQTT, HTTP, NTP) e mantém o loop principal.

---

## Como Usar

1. **Gravar Firmware Adequado**  
   - Baixe e grave no Pico W o firmware MicroPython compatível (ex.: `rp2-pico-w-v1.22.x.uf2` ou superior).

2. **Editar Parâmetros**  
   - Ajuste `CONFIG["EXTERNAL_SSID"]` e `CONFIG["EXTERNAL_PASS"]` para sua rede Wi-Fi.
   - Ajuste `WS2812_PIN` e `NUM_LEDS` para corresponder ao hardware de LEDs.

3. **Carregar no Thonny**  
   - Conecte o Pico W e abra o Thonny.
   - Copie o arquivo `.py` para o Pico W.

4. **Executar**  
   - Selecione `Run current script` no Thonny ou `import semaforo_script`.
   - Observe no console os logs de conexão à rede, de inicialização do MQTT e do semáforo.

5. **Testar via MQTT**  
   - Use um cliente MQTT (e.g. MQTT Explorer), conecte ao IP do Pico W na porta `1883`.
   - Publique em `semaforo/acao` (payload vazio ou qualquer texto).  
   - O semáforo inicia o ciclo: verde → amarelo → vermelho → volta a verde.

6. **Interface Web**  
   - Acesse `http://<ip_do_pico>` pelo navegador.
   - A página exibe o estado do semáforo e um painel de logs em tempo real.

---

## Resolvendo Problemas

- **Falha ao iniciar Wi-Fi** (`[CYW43] Failed to start CYW43`):  
  - Reinstale o firmware MicroPython específico para o Pico W.
  - Verifique se está alimentado por uma porta USB confiável.

- **MQTT não recebe mensagens**:  
  - Confirme o IP do Pico W (exibido no console).
  - Verifique se a porta `1883` está acessível na rede.

- **NTP não funciona**:  
  - Ajuste `CONFIG["NTP_HOST"]` para outro servidor ou verifique se há acesso à internet.

- **Semáforo não muda cor**:  
  - Confira se os LEDs WS2812B estão alimentados e conectados ao pino configurado.
  - Altere `update_panel(state)` conforme seu hardware.

---

## Licença

Este projeto é disponibilizado sob a [Licença MIT](LICENSE). Use livremente em fins acadêmicos ou comerciais, mantendo os devidos créditos.

---
