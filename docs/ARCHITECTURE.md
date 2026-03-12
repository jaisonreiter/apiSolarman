# Arquitetura

## Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Home Assistant Core                               │
├─────────────────────────────────────────────────────────────────────────┤
│  Config Flow          │  __init__.py           │  Sensor Platform       │
│  (config_flow.py)     │  (entry point)         │  (sensor.py)            │
│  - Validação          │  - Setup/Unload        │  - SolarmanDynamicSensor│
│  - Options Flow       │  - Forward platforms   │  - SolarmanScalarSensor │
└──────────┬────────────┴──────────┬─────────────┴────────────┬────────────┘
           │                      │                           │
           ▼                      ▼                           │
┌──────────────────────────────────────────────────────────────┴──────────┐
│                    SolarmanCloudCoordinator (coordinator.py)             │
│  - DataUpdateCoordinator                                                │
│  - Polling periódico (poll_interval)                                    │
│  - Chama api.fetch_all()                                                │
└────────────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SolarmanCloudApi (api.py)                              │
│  - Autenticação OAuth (token)                                            │
│  - plant_list, plant_realtime, station_devices, device_realtime          │
│  - discover() - seleção automática de planta/dispositivo                 │
└────────────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Solarman OpenAPI (cloud)                              │
│  https://globalapi.solarmanpv.com                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Fluxo de dados

### 1. Configuração inicial

1. Usuário adiciona integração via **Configurações > Dispositivos e Serviços**
2. `SolarmanCloudConfigFlow.async_step_user()` exibe formulário
3. `_validate_input()` chama `api.async_validate()`:
   - Autentica (token)
   - Lista plantas
   - Lista dispositivos da planta
   - Obtém dados em tempo real do dispositivo
4. Se sucesso: cria `ConfigEntry` com dados do usuário

### 2. Setup da integração

1. `async_setup_entry()` em `__init__.py`
2. Cria `SolarmanCloudApi` com `config` (data + options)
3. Cria `SolarmanCloudCoordinator` com intervalo de polling
4. Executa primeiro refresh (`async_config_entry_first_refresh`)
5. Registra plataformas (sensor)
6. Configura listener para reload em alteração de opções

### 3. Atualização periódica

1. `DataUpdateCoordinator` dispara a cada `poll_interval` segundos
2. `_async_update_data()` chama `api.fetch_all()`
3. `fetch_all()`:
   - Garante token válido
   - Se necessário, executa `discover()` (plant_id/device_sn)
   - Obtém `plant_realtime(plant_id)` e `device_realtime(device_sn)`
   - Retorna `{ plant, device, selected }`

### 4. Criação de sensores

1. `async_setup_entry()` em `sensor.py`
2. Para cada item em `device.dataList`: cria `SolarmanDynamicSensor`
3. Se `include_plant_sensors`: para cada chave escalar em `plant`: cria `SolarmanScalarSensor`
4. Sensores herdam de `CoordinatorEntity` e leem de `coordinator.data`

## Constantes e configuração

- **DOMAIN**: `solarman_cloud_custom`
- **PLATFORMS**: `["sensor"]`
- **Endpoints**: `/account/v1.0/token`, `/station/v1.0/list`, `/station/v1.0/realTime`, `/station/v1.0/device`, `/device/v1.0/currentData`
- **Tipos de login**: `email`, `username`, `mobile`
- **Tipos de dispositivo**: `INVERTER`, `MICRO_INVERTER`, `COLLECTOR`
