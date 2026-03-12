# Documentação dos Sensores

Esta integração cria **sensores dinamicamente** a partir dos dados retornados pela API da Solarman. Os sensores disponíveis dependem do modelo do inversor e do que a API retorna para seu dispositivo.

---

## Visão geral

Existem duas origens de sensores:

| Origem | Descrição | Opção |
|--------|-----------|-------|
| **Dispositivo (device)** | Dados do inversor em tempo real (`dataList`) | Sempre criados |
| **Planta (plant)** | Dados agregados da estação solar | `include_plant_sensors` (padrão: ativado) |

---

## 1. Sensores de potência instantânea (agora)

Exibem **quanta energia está sendo gerada neste momento**.

| Sensor | Chave típica | Unidade | Descrição |
|--------|--------------|---------|-----------|
| **Potência AC de saída** | `pac`, `generationpower`, `APo_t1` | W ou kW | Potência ativa total que o inversor está entregando à rede |
| **Potência de geração** | `generationpower` | W ou kW | Mesmo conceito, nome alternativo usado por alguns dispositivos |

**Uso:** Monitorar produção em tempo real, dashboards ao vivo, alertas de baixa geração.

---

## 2. Sensores de energia acumulada

Exibem **energia gerada em um período**. O valor aumenta ao longo do tempo e é útil para consultas futuras (histórico, estatísticas, relatórios).

### 2.1 Geração do dia (hoje)

| Sensor | Chave típica | Unidade | Descrição |
|--------|--------------|---------|-----------|
| **Energia gerada hoje** | `etoday`, `generationtoday`, `Etdy_ge1` | kWh | Energia acumulada desde a meia-noite até o momento atual |

**Uso:** Comparar dias, verificar se a meta diária foi atingida.

### 2.2 Geração total (lifetime)

| Sensor | Chave típica | Unidade | Descrição |
|--------|--------------|---------|-----------|
| **Energia total gerada** | `etotal`, `generationtotal`, `Et_ge0` | kWh | Energia acumulada desde a instalação do inversor |

**Uso:** ROI do sistema, estatísticas de longo prazo.

### 2.3 Outros períodos (semana, mês, ano)

A API da Solarman **não retorna** diretamente geração por minuto, hora, semana ou mês no endpoint de dados em tempo real. O que existe hoje:

| Período | Disponível via API? | Alternativa no Home Assistant |
|---------|---------------------|-------------------------------|
| **Minuto** | Não | Template/statistics a partir do sensor de potência |
| **Hora** | Não | `statistics` ou `utility_meter` |
| **Dia** | Sim (`etoday`) | Sensor nativo |
| **Semana** | Não | `utility_meter` com ciclo semanal |
| **Mês** | Não* | `utility_meter` com ciclo mensal |
| **Ano** | Não* | `utility_meter` com ciclo anual |

\* Alguns dispositivos ou endpoints de histórico podem expor dados mensais/anuais; a integração atual usa apenas o endpoint de dados em tempo real.

**Para consultas futuras por min/hora/semana/mês/ano**, use:

1. **`utility_meter`** – cria sensores de consumo/geração por período (hora, dia, semana, mês, ano)
2. **`statistics`** – integração de Estatísticas para médias e totais
3. **Histórico** – o sensor `etoday` e o de potência permitem que o Home Assistant armazene histórico para gráficos e relatórios

---

## 3. Outros sensores típicos do dispositivo

| Sensor | Chave típica | Unidade | Descrição |
|--------|--------------|---------|-----------|
| **Temperatura do inversor** | `temperature`, `INV_T0` | °C | Temperatura interna do equipamento |
| **Tensão AC** | `vac`, `AV1`, etc. | V | Tensão na saída AC |
| **Corrente AC** | `iac`, etc. | A | Corrente na saída AC |
| **Frequência** | `fac`, `freq` | Hz | Frequência da rede |
| **Fator de potência** | `pf`, `powerfactor` | % | Fator de potência |
| **Status** | `status`, `run_state` | — | Estado de operação do inversor |

Os nomes exatos das chaves variam conforme o fabricante e o modelo. A integração usa o `name` retornado pela API quando disponível.

---

## 4. Sensores da planta

Quando `include_plant_sensors` está ativado, a integração cria sensores para cada campo escalar retornado em `/station/v1.0/realTime`, por exemplo:

- Potência total da planta
- Energia do dia
- Energia total
- Outros dados agregados da estação

O prefixo do nome é **"Plant"** (ex.: "Plant Generation Power").

---

## 5. Mapeamento de unidades

A integração converte automaticamente:

| Unidade da API | Unidade no Home Assistant |
|----------------|---------------------------|
| W | W (potência) |
| kW | kW |
| V | V (tensão) |
| A | A (corrente) |
| °C / C | °C (temperatura) |
| kWh | kWh (energia) |
| % | % |
| Hz | Hz |

---

## 6. Device class e state class

Para melhor integração com o Home Assistant (gráficos, estatísticas, Energy Dashboard):

| Tipo de dado | device_class | state_class |
|---------------|--------------|-------------|
| Potência instantânea | `power` | `measurement` |
| Energia acumulada | — | `total_increasing` |
| Temperatura | `temperature` | `measurement` |

Chaves reconhecidas: `generationpower`, `pac`, `etoday`, `generationtoday`, `etotal`, `generationtotal`, `temperature`.

---

## 7. Atributos dos sensores

Todos os sensores expõem:

| Atributo | Descrição |
|----------|-----------|
| `device_sn` | Serial do dispositivo |
| `device_id` | ID do dispositivo na API |
| `plant_id` | ID da planta |
| `source` | `device` ou `plant` |
| `raw_key` | Chave original da API |

---

## 8. Exemplo de uso para períodos customizados

Para ter geração por **hora**, **mês** e **ano** para consultas futuras:

```yaml
# utility_meter para geração horária
utility_meter:
  hourly_solar_generation:
    source: sensor.solarman_device_pac  # ou o sensor de potência do seu inversor
    name: Geração Solar Horária
    cycle: hourly

# utility_meter para geração mensal
utility_meter:
  monthly_solar_generation:
    source: sensor.solarman_device_etoday  # resetado à meia-noite
    name: Geração Solar Mensal
    cycle: monthly

# Para ano, use cycle: yearly
```

**Nota:** Para períodos maiores (mês/ano), é mais preciso usar `etoday` como base e deixar o `utility_meter` acumular, ou usar a integração **Statistics** com o sensor de potência.
