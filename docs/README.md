# Documentação - Solarman Cloud Custom

Documentação técnica dos fontes da integração **Solarman Cloud Custom** para Home Assistant.

## Índice

| Documento | Descrição |
|-----------|-----------|
| [Arquitetura](ARCHITECTURE.md) | Visão geral da arquitetura, componentes e fluxo de dados |
| [Código-fonte](SOURCE_CODE.md) | Documentação detalhada de cada módulo e classe |

## Visão geral

A integração conecta-se à **OpenAPI da Solarman** via cloud para obter dados em tempo real de inversores e plantas solares. Funciona mesmo quando o Home Assistant está fora da rede local (ex.: VPS, Hostinger).

### Stack técnico

- **Home Assistant** 2024.1.0+
- **Python** 3.x (assíncrono com `asyncio`)
- **aiohttp** para requisições HTTP
- **voluptuous** para validação de configuração
