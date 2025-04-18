# Robô de Trading Bybit

Sistema automatizado de trading para a exchange Bybit, desenvolvido em Python.

## Descrição

Este robô de trading foi desenvolvido para executar estratégias automatizadas na exchange Bybit. O sistema permite configurar diferentes estratégias de trading, gerenciar posições, definir stop loss e take profit, e monitorar o desempenho das operações.

## Funcionalidades

- Suporte a múltiplas estratégias de trading
- Execução automática de ordens de compra e venda
- Configuração de stop loss e take profit
- Monitoramento de posições abertas
- Notificações por email
- Logs detalhados das operações
- Suporte a diferentes timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- Compatível com contas spot e futuros

## Requisitos

- Python 3.8+
- Bibliotecas Python:
  - pandas
  - pandas-ta
  - pybit
  - python-dotenv
  - loguru

## Configuração

1. Clone o repositório:
```
git clone https://github.com/paulocesargarcia/robo_bybit-v2.git
cd robo_bybit-v2
```

2. Instale as dependências:
```
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
   - Crie um arquivo `.env` na raiz do projeto
   - Adicione suas chaves de API da Bybit:

## Estrutura do Projeto

```
robo_bybit-v2/
├── src/
│   ├── connector/
│   │   └── bybit_connector.py  # Conexão com a API da Bybit
│   ├── core/
│   │   └── executor.py         # Executor de estratégias
│   ├── utils/
│   │   ├── logger.py           # Configuração de logs
│   │   └── email_notifier.py   # Notificações por email
│   └── main.py                 # Ponto de entrada do sistema
├── strategies/
│   ├── base_strategy.py        # Classe base para estratégias
│   ├── simple_cross_long.py    # Estratégia de exemplo
│   └── simple_cross_short.py   # Estratégia de exemplo
├── logs/                       # Diretório para logs
├── .env                        # Variáveis de ambiente
├── requirements.txt            # Dependências
└── README.md                   # Este arquivo
```

## Como Executar

1. Configure sua estratégia:
   - Escolha uma estratégia existente ou crie uma nova
   - Ajuste os parâmetros como stop loss, take profit, etc.

2. Execute o robô:
```
python src/main.py
```

## Criando Novas Estratégias

Para criar uma nova estratégia, siga estes passos:

1. Crie um novo arquivo na pasta `strategies/`
2. Herde da classe `BaseStrategy`
3. Implemente os métodos necessários:
   - `populate_indicators`: Calcule os indicadores técnicos
   - `populate_entry_trend`: Defina as condições de entrada
   - `populate_exit_trend`: Defina as condições de saída
   - `populate_stoploss`: Configure o stop loss para customizar
   - `populate_takeprofit`: Configure o take profit para customizar


## Logs e Monitoramento

O sistema gera logs detalhados das operações no diretório `logs/`. Os logs incluem:
- Informações sobre ordens executadas
- Erros e exceções
- Status das posições
- Notificações de entrada e saída

## Notificações

O sistema pode enviar notificações por email quando:
- Uma ordem é executada
- Uma posição é fechada
- Ocorrem erros críticos

Para configurar as notificações, adicione as seguintes variáveis ao arquivo `.env`, e necessário ter uma conta na mailgun:
```
USE_NOTIFIER=false
MAILGUN_API_KEY=sua_chave_api_mailgun_aqui
MAILGUN_DOMAIN=seu_dominio_mailgun_aqui
MAILGUN_FROM_EMAIL=seu_email_remetente@seu_dominio.com
MAILGUN_TO_EMAIL=email1@exemplo.com,email2@exemplo.com
```

## Segurança

- Nunca compartilhe suas chaves de API
- Use sempre o modo testnet para testar novas estratégias
- Monitore regularmente o desempenho do robô
- Configure stop loss adequados para limitar perdas

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.
