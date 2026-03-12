# Solarman Cloud for Home Assistant

Integração custom para Home Assistant via Solarman OpenAPI (cloud), desenhada para:

- múltiplos microinversores
- sensores canônicos compatíveis com Energy Dashboard
- sensores por placa/canal quando o payload do microinversor expuser esses dados
- controle de janela horária de coleta
- controle de orçamento anual de requests
- atualização via HACS / GitHub release
- validação manual de topologia (planta + devices)

## Instalação manual

1. Copie `custom_components/solarman_cloud` para `/config/custom_components/`.
2. Reinicie o Home Assistant.
3. Vá em **Configurações > Dispositivos e Serviços > Adicionar integração**.
4. Procure por **Solarman Cloud**.

## Instalação via HACS

1. Publique este conteúdo em um repositório GitHub.
2. Crie uma release/tag nova a cada versão.
3. No HACS, adicione o repositório em **Custom repositories** como **Integration**.
4. Instale a integração.

## Regras de requests

- A planta/topologia é carregada somente na instalação inicial e quando o usuário aciona o botão **Validar planta / Atualizar topologia**.
- O polling normal consulta apenas os microinversores selecionados.
- Sensores por placa são derivados da mesma resposta do microinversor, sem requests extras por placa.
- A integração calcula o consumo anual estimado e bloqueia configurações acima do limite seguro.

## Observações

- Os nomes exatos de chaves de painel/placa variam por fabricante/modelo.
- Quando a API não trouxer potência nominal por placa, a integração usa a capacidade padrão por placa configurada pelo usuário.
- Para atualização automática, o caminho recomendado é instalar via HACS e publicar novas releases GitHub com `version`/tag atualizados.
