import sys
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Obter nível do log do .env
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Validar nível de log
valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
if LOG_LEVEL not in valid_levels:
    print(f"Nível de log inválido: {LOG_LEVEL}. Usando INFO como padrão.")
    LOG_LEVEL = 'INFO'

# Criar diretório de logs se não existir
log_path = Path('logs')
log_path.mkdir(parents=True, exist_ok=True)

# Remover handler padrão
logger.remove()

# Adicionar handler para arquivo
logger.add(
    'logs/trading.log',
    level=LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
    enqueue=True
)

# Adicionar handler para console com cores
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# Log inicial para confirmar configuração
logger.info(f"Logger configurado - Nível: {LOG_LEVEL}")