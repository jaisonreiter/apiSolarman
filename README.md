# Solarman Cloud Custom for Home Assistant

Integração custom para Home Assistant que consulta a OpenAPI da Solarman pela cloud, pensada para funcionar inclusive quando o Home Assistant está fora da rede local, como em VPS/Hostinger.

## Recursos
- autenticação via OpenAPI usando **App ID / API ID** e **App Secret / API Secret**
- suporte a login por `email`, `username` ou `mobile`
- descoberta automática da primeira planta e do primeiro dispositivo, se `plant_id` e `device_sn` não forem informados
- leitura de dados do dispositivo pela cloud
- criação dinâmica de sensores a partir do `dataList`
- tela de configuração via UI no Home Assistant
- opções pós-instalação para ajustar `poll_interval`, `plant_id`, `device_sn`, `device_type` e sensores da planta

## Compatibilidade
- Home Assistant `2024.1.0+`
- domínio internacional padrão: `https://globalapi.solarmanpv.com`

## Instalação manual
1. Extraia este pacote.
2. Copie `custom_components/solarman_cloud_custom` para `/config/custom_components/`.
3. Reinicie o Home Assistant.
4. Vá em **Configurações > Dispositivos e Serviços > Adicionar integração**.
5. Procure por **Solarman Cloud Custom**.

## Instalação via HACS (repositório custom)
1. Publique o conteúdo deste pacote em um repositório Git.
2. No HACS, vá em **Integrations** → menu de três pontos → **Custom repositories**.
3. Adicione a URL do repositório e escolha o tipo **Integration**.
4. Instale **Solarman Cloud Custom**.
5. Reinicie o Home Assistant.
6. Vá em **Configurações > Dispositivos e Serviços** e adicione a integração.

## Campos da configuração
- **Base URL**: normalmente `https://globalapi.solarmanpv.com`
- **API ID / App ID**
- **API Secret / App Secret**
- **Tipo de login**: `email`, `username` ou `mobile`
- **Email / usuário / celular**
- **Senha da conta**
- **Org ID** opcional
- **Plant ID** opcional
- **Device SN** opcional
- **Device type**: `INVERTER`, `MICRO_INVERTER` ou `COLLECTOR`
- **Poll interval** em segundos
- opção para informar que a senha já está em **SHA256**

## Documentação técnica

Documentação detalhada dos fontes está em [`docs/`](docs/README.md):

- [Arquitetura](docs/ARCHITECTURE.md) – componentes, fluxo de dados
- [Código-fonte](docs/SOURCE_CODE.md) – módulos, classes e APIs
- [Sensores](docs/SENSORS.md) – o que cada sensor exibe (potência, energia por dia/total, alternativas para min/hora/semana/mês/ano)

## Observações
- Nenhuma credencial vem fixa no código.
- Para alguns microinversores, `MICRO_INVERTER` funciona melhor que `INVERTER`.
- Esta integração foi estruturada com base na OpenAPI pública da Solarman, mas pode exigir ajuste fino dependendo do tipo de conta/planta/dispositivo retornado pela sua conta.
