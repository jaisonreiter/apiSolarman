# Documentação do Código-fonte

## Estrutura de arquivos

```
custom_components/solarman_cloud_custom/
├── __init__.py      # Entry point
├── api.py           # Cliente da API Solarman
├── config_flow.py   # Configuração via UI
├── const.py         # Constantes
├── coordinator.py   # DataUpdateCoordinator
├── sensor.py        # Sensores dinâmicos
├── manifest.json    # Metadados da integração
├── strings.json     # Strings de UI (pt-BR)
└── translations/
    └── en.json      # Strings em inglês
```

---

## `const.py`

Define constantes usadas em toda a integração.

| Constante | Tipo | Descrição |
|-----------|------|-----------|
| `DOMAIN` | str | `"solarman_cloud_custom"` |
| `PLATFORMS` | list | `["sensor"]` |
| `CONF_BASE_URL` | str | URL base da API |
| `CONF_APP_ID` | str | App ID / API ID |
| `CONF_APP_SECRET` | str | App Secret / API Secret |
| `CONF_LOGIN_TYPE` | str | `email`, `username` ou `mobile` |
| `CONF_USERNAME` | str | Email/usuário/celular |
| `CONF_PASSWORD` | str | Senha |
| `CONF_ORG_ID` | str | Org ID (opcional) |
| `CONF_PLANT_ID` | str | ID da planta (opcional) |
| `CONF_DEVICE_SN` | str | Serial do dispositivo (opcional) |
| `CONF_DEVICE_TYPE` | str | INVERTER, MICRO_INVERTER, COLLECTOR |
| `CONF_POLL_INTERVAL` | int | Intervalo de polling em segundos |
| `CONF_INCLUDE_PLANT_SENSORS` | bool | Incluir sensores da planta |
| `CONF_PASSWORD_ALREADY_SHA256` | bool | Senha já em SHA256 |

**Endpoints:**
- `TOKEN_ENDPOINT`: `/account/v1.0/token`
- `PLANT_LIST_ENDPOINT`: `/station/v1.0/list`
- `PLANT_REALTIME_ENDPOINT`: `/station/v1.0/realTime`
- `STATION_DEVICE_LIST_ENDPOINT`: `/station/v1.0/device`
- `DEVICE_REALTIME_ENDPOINT`: `/device/v1.0/currentData`

---

## `api.py`

### `SolarmanApiError`

Exceção lançada quando a API retorna erro (`success: false` ou código inválido).

### `SolarmanCloudApi`

Classe principal de comunicação com a OpenAPI da Solarman.

#### Construtor

```python
def __init__(self, session: aiohttp.ClientSession, config: dict[str, Any]) -> None
```

- `session`: sessão aiohttp compartilhada
- `config`: dicionário com credenciais e opções (merge de `entry.data` e `entry.options`)

#### Propriedades

| Propriedade | Retorno | Descrição |
|-------------|---------|-----------|
| `selected_plant_id` | int \| None | ID da planta selecionada |
| `selected_device_sn` | str \| None | Serial do dispositivo selecionado |
| `selected_device_id` | int \| None | ID do dispositivo |

#### Métodos privados

| Método | Descrição |
|--------|-----------|
| `_base_url()` | Retorna URL base sem barra final |
| `_build_url(path, include_app_id)` | Monta URL com query e opcional appId |
| `_hashed_password()` | Retorna senha em SHA256 (ou senha se já hash) |
| `_login_payload()` | Monta payload para `POST /token` |
| `_request(method, path, payload, ...)` | Requisição HTTP com retry em 401 |

#### Métodos públicos

| Método | Descrição |
|--------|-----------|
| `ensure_token(force_refresh)` | Obtém token OAuth; usa lock para evitar concorrência |
| `plant_list()` | Lista plantas (POST /station/v1.0/list) |
| `plant_realtime(plant_id)` | Dados em tempo real da planta |
| `station_devices(plant_id)` | Lista dispositivos da planta |
| `device_realtime(device_sn, device_id)` | Dados em tempo real do dispositivo |
| `discover()` | Seleciona planta e dispositivo (config ou primeiro) |
| `fetch_all()` | Obtém plant + device data; retorna `{ plant, device, selected }` |
| `async_validate()` | Valida credenciais e retorna dados descobertos |

---

## `config_flow.py`

### `_user_schema(defaults)`

Schema Voluptuous para o formulário de configuração inicial.

### `_options_schema(config, options)`

Schema para opções pós-instalação (poll_interval, plant_id, device_sn, device_type, include_plant_sensors).

### `_validate_input(hass, data)`

- Cria `SolarmanCloudApi` com `data`
- Chama `api.async_validate()`
- Retorna `{ title, plant_id, device_sn }` para uso no entry

### `SolarmanCloudConfigFlow`

- **VERSION**: 2
- **async_step_user**: exibe formulário e valida; cria entry com `unique_id = f"{app_id}::{device_sn}"`
- **async_get_options_flow**: retorna `SolarmanCloudOptionsFlow`

### `SolarmanCloudOptionsFlow`

- **async_step_init**: exibe formulário de opções e salva em `entry.options`

---

## `coordinator.py`

### `SolarmanCloudCoordinator`

Subclasse de `DataUpdateCoordinator[dict]`.

- **Construtor**: recebe `hass`, `api`, `interval` (segundos)
- **update_interval**: `timedelta(seconds=interval)`
- **name**: `DOMAIN`
- **`_async_update_data()`**: chama `api.fetch_all()`; em caso de erro lança `UpdateFailed`

---

## `sensor.py`

### Mapeamentos

**UNIT_MAP**: mapeia unidades da API para unidades do Home Assistant (W, kW, V, A, °C, kWh, %, Hz).

**KEY_HINTS**: mapeia chaves normalizadas para `device_class` e `state_class`:
- `generationpower`, `pac` → power, measurement
- `etoday`, `generationtoday` → total_increasing
- `etotal`, `generationtotal` → total_increasing
- `temperature` → temperature, measurement

### Funções auxiliares

| Função | Descrição |
|--------|-----------|
| `_normalize(key)` | Remove caracteres não alfanuméricos e lower |
| `_friendly_name(raw_key)` | Substitui underscores/hífens por espaços e title |
| `_parse_number(value)` | Converte string para int/float; retorna None em falha |
| `_description_from_item(item, source)` | Cria `DynamicSensorDescription` a partir de item do dataList |
| `_description_from_scalar(key, source)` | Cria descrição para chave escalar da planta |

### `DynamicSensorDescription`

Dataclass que estende `SensorEntityDescription` com `raw_key` e `source`.

### `SolarmanBaseSensor`

- Base para `SolarmanDynamicSensor` e `SolarmanScalarSensor`
- `_attr_has_entity_name = True`
- `device_info`: identifica dispositivo Solarman
- `extra_state_attributes`: device_sn, device_id, plant_id, source, raw_key

### `SolarmanDynamicSensor`

- Sensores criados a partir de `device.dataList`
- `native_value`: busca valor em `dataList` por `key` ou `name`

### `SolarmanScalarSensor`

- Sensores criados a partir de chaves escalares de `plant`
- `native_value`: lê `plant[raw_key]`

### `async_setup_entry`

1. Obtém coordinator de `hass.data[DOMAIN][entry.entry_id]`
2. Para cada item em `device.dataList`: cria `SolarmanDynamicSensor`
3. Se `include_plant_sensors`: para cada chave escalar em `plant`: cria `SolarmanScalarSensor`
4. Chama `async_add_entities(entities)`

---

## `__init__.py`

### `async_setup_entry`

1. Cria `SolarmanCloudApi` com `config` (data + options)
2. Cria `SolarmanCloudCoordinator` com `poll_interval`
3. Executa primeiro refresh
4. Armazena coordinator em `hass.data[DOMAIN][entry.entry_id]`
5. Registra plataformas (sensor)
6. Adiciona listener para reload em alteração de opções

### `async_unload_entry`

Unload das plataformas e remoção do coordinator

### `async_reload_entry`

Unload + setup novamente (usado em alteração de opções)
