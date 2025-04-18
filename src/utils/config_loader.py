import json
import argparse
import os
import sys
from dotenv import load_dotenv
from src.utils.logger import logger

# Define o caminho padrão relativo à raiz do projeto
# Assume que config_loader.py está em src/utils/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config.json')

# Carrega as variáveis de ambiente do .env
load_dotenv()

def load_config(config_path=None):
    """Carrega o arquivo de configuração JSON."""
    # Se um caminho absoluto for fornecido, use-o. Caso contrário, use o padrão.
    path_to_load = os.path.abspath(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not os.path.exists(path_to_load):
        logger.warning(f"Aviso: Arquivo de configuração '{path_to_load}' não encontrado. Usando valores padrão ou argumentos de linha de comando.")
        return {}
    try:
        with open(path_to_load, 'r') as f:
            config = json.load(f)
            logger.info(f"Configuração carregada de '{path_to_load}'")
            return config
    except json.JSONDecodeError:
        logger.error(f"Erro: Falha ao decodificar o arquivo JSON '{path_to_load}'. Verifique a formatação.")
        return {}
    except Exception as e:
        logger.error(f"Erro ao carregar o arquivo de configuração '{path_to_load}': {e}")
        return {}

def parse_arguments():
    """Analisa os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description='Robô de Trade Bybit')
    parser.add_argument('--strategy', type=str, help='Nome da estratégia a ser usada (sem a extensão .py, ex: ExampleStrategy)')
    parser.add_argument('--config', type=str, help=f'Caminho para o arquivo de configuração JSON (padrão busca por config.json na raiz)')
    parser.add_argument('--pair', type=str, help='Par de moedas a ser negociado (ex: BTCUSDT)')
    parser.add_argument('--timeframe', type=str, help='Timeframe dos candles (ex: 1m, 5m, 1h, 1D)')
    # BooleanOptionalAction permite --testnet e --no-testnet
    parser.add_argument('--testnet', action=argparse.BooleanOptionalAction, default=None, help='Forçar uso da Testnet (--testnet) ou Mainnet (--no-testnet)')

    return parser.parse_args()

def get_parameters():
    """Obtém os parâmetros finais combinando config.json e argumentos CLI."""
    args = parse_arguments()
    config_from_file = load_config(args.config)
    
    # Depuração: mostrar estrutura do config_from_file
    logger.info("DEBUG - CONFIG CARREGADO:")
    logger.info(config_from_file)
    
    # Verificar tipo de config_from_file
    logger.info(f"DEBUG - TIPO: {type(config_from_file)}")

    # Determinar a categoria com base no par (simplificado)
    # Idealmente, isso seria mais robusto ou configurável
    category = "linear" # Default para USDT-M
    if args.pair and ("USD" in args.pair and not args.pair.endswith("USDT")): # Ex: BTCUSD
        category = "inverse"
    elif args.pair and not ("USD" in args.pair):
        # Poderia ser spot, mas vamos manter linear/inverse por enquanto
        # category = "spot"
        pass # Mantém default
    elif config_from_file.get('pair') and ("USD" in config_from_file.get('pair') and not config_from_file.get('pair').endswith("USDT")):
        category = "inverse"

    # Prioridade: Argumentos CLI > Arquivo config.json > .env > Padrões
    # DEBUG: Tentar acessar individualmente
    logger.info("DEBUG - Tentando acessar campos individualmente:")
    try:
        logger.info(f"strategy: {config_from_file.get('strategy')}")
        logger.info(f"pair: {config_from_file.get('pair')}")
        logger.info(f"timeframe: {config_from_file.get('timeframe')}")
    except Exception as e:
        logger.error(f"ERROR ao acessar campos: {e}")
    
    try:
        # Obtém o valor de TESTNET do .env (padrão True se não definido)
        env_testnet = os.getenv('TESTNET', 'true').lower() == 'true'
        
        params = {
            'strategy': args.strategy or config_from_file.get('strategy'),
            'pair': args.pair or config_from_file.get('pair'),
            'timeframe': args.timeframe or config_from_file.get('timeframe'),
            'testnet': args.testnet if args.testnet is not None else env_testnet,
            'category': category,
            'config_path_used': os.path.abspath(args.config) if args.config else DEFAULT_CONFIG_PATH
        }
        logger.info("DEBUG - Params criado com sucesso")
    except Exception as e:
        logger.error(f"ERROR na criação do params: {e}")
        import traceback
        traceback.print_exc()
        params = {
            'strategy': args.strategy,
            'pair': args.pair,
            'timeframe': args.timeframe,
            'testnet': args.testnet if args.testnet is not None else env_testnet,
            'category': category,
            'config_path_used': os.path.abspath(args.config) if args.config else DEFAULT_CONFIG_PATH
        }

    # Validação mais rigorosa
    required_params = ['strategy', 'pair', 'timeframe']
    missing_params = [p for p in required_params if not params[p]]
    if missing_params:
        raise ValueError(f"Parâmetros obrigatórios ausentes: {', '.join(missing_params)}. Forneça via CLI ou no arquivo de configuração ({params['config_path_used']}).")

    # Validação adicional (ex: timeframe válido)
    valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1D', '1W', '1M'] # Exemplos Bybit
    # Bybit usa '1', '3', '5'... para minutos, D/W/M para dias/semanas/meses
    # Ajuste a validação conforme a nomenclatura exata da pybit/Bybit API para get_kline
    bybit_timeframes = ['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M']
    if params['timeframe'] not in bybit_timeframes:
         logger.warning(f"Aviso: Timeframe '{params['timeframe']}' pode não ser reconhecido pela API Bybit. Usar formatos como: {bybit_timeframes}")
         # Poderia levantar erro aqui se desejado: raise ValueError("Timeframe inválido...")

    logger.info(f"Parâmetros finais: {params}")
    return params

