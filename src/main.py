import importlib
import sys
import os
import time 
from dotenv import load_dotenv
from utils.logger import logger

# Configuração do ambiente
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

# Carregar variáveis de ambiente
dotenv_path = os.path.join(ROOT_DIR, '.env')
if os.path.exists(dotenv_path):
    if load_dotenv(dotenv_path=dotenv_path, override=True):
        logger.info("Variáveis de ambiente carregadas e sobrescritas do .env")
    else:
        logger.warning("Aviso: .env encontrado, mas não foi possível carregar variáveis (talvez esteja vazio?).")
else:
    logger.warning("Aviso: .env não encontrado na raiz. As variáveis devem ser definidas no ambiente.")

from src.utils.config_loader import get_parameters
from src.connector.bybit_connector import BybitConnector
from src.core.executor import StrategyExecutor
from strategies.base_strategy import BaseStrategy

STRATEGIES_FOLDER = "strategies"

def load_strategy_class(strategy_name):
    """Carrega a classe da estratégia pelo nome."""
    try:
        module_path = f"{STRATEGIES_FOLDER}.{strategy_name}"
        strategy_module = importlib.import_module(module_path)

        # Procurar classe que herda de BaseStrategy
        for name, obj in strategy_module.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                logger.info(f"Found strategy class: {name}")
                return obj

        raise AttributeError(f"Could not find a valid class inheriting from BaseStrategy in '{module_path}.py'")
    except ImportError as e:
        raise ImportError(f"Could not import strategy module '{STRATEGIES_FOLDER}/{strategy_name}.py'. Details: {e}")
    except AttributeError as e:
        raise AttributeError(f"Error loading strategy '{strategy_name}': {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error loading strategy '{strategy_name}': {e}")

def log_configuration(params, strategy_instance, run_interval_seconds):
    """Loga a configuração atual do robô."""
    logger.info("\nConfigurações atuais:")
    logger.info(f"  - Estratégia: {strategy_instance.__class__.__name__}")
    logger.info(f"  - Par: {params['pair']}")
    logger.info(f"  - Timeframe: {params['timeframe']}")
    logger.info(f"  - Testnet: {params['testnet']}")
    logger.info(f"  - Intervalo de execução: {run_interval_seconds}s")
    logger.info(f"  - Alavancagem: {strategy_instance.leverage}x")
    logger.info(f"  - Investment %: {strategy_instance.investment_percent}%")
    logger.info(f"  - Stop Loss: {strategy_instance.stop_loss}%")
    logger.info(f"  - Take Profit: {strategy_instance.take_profit}%")

def main():
    run_interval_seconds = 5
    try:
        params = get_parameters()
        strategy_name = params['strategy']
        
        logger.info(f"Loading strategy: {strategy_name}...")
        StrategyClass = load_strategy_class(strategy_name)
        strategy_instance = StrategyClass(config=params)
        
        log_configuration(params, strategy_instance, run_interval_seconds)
        logger.info(f"Strategy '{StrategyClass.__name__}' loaded successfully.")

        logger.info("Initializing Bybit Connector...")
        connector = BybitConnector(testnet=params['testnet'])

        logger.info("Initializing Strategy Executor...")
        executor = StrategyExecutor(connector, strategy_instance)

        logger.info(f"\nStarting continuous execution loop (Interval: {run_interval_seconds}s). Press Ctrl+C to stop.")
        logger.info("-----------------------------------------------------------------------")

        while True:
            logger.info(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running check...")
            executor.run(category=params['category'], symbol=params['pair'], interval=params['timeframe'])
            logger.info(f"Check finished. Waiting {run_interval_seconds} seconds...")
            time.sleep(run_interval_seconds)

    except (ValueError, ImportError, AttributeError, TypeError, RuntimeError) as e:
        logger.error(f"\nExecution Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nLoop terminated by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nAn unexpected error occurred in main loop: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 