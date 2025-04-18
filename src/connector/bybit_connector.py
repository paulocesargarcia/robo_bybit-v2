import os
import sys 
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import pandas as pd 
from src.utils.logger import logger

class BybitConnector:
    def __init__(self, testnet=True):
        self.testnet = testnet
        if self.testnet:
            api_key_name = "TESTNET_API_KEY"
            api_secret_name = "TESTNET_API_SECRET"
            logger.info("Connector: Using TESTNET credentials.")
        else:
            api_key_name = "BYBIT_API_KEY"
            api_secret_name = "BYBIT_API_SECRET"
            logger.info("Connector: Using MAINNET credentials.")

        api_key = os.getenv(api_key_name)
        api_secret = os.getenv(api_secret_name)

        if not api_key or not api_secret:
            error_msg = f"{api_key_name} and {api_secret_name} must be set in environment or .env file"
            raise ValueError(error_msg)

        self.session = HTTP(
            testnet=self.testnet,
            api_key=api_key,
            api_secret=api_secret,
            log_requests=True # Habilitar log detalhado da API
        )
        logger.info(f"Bybit Connector initialized. Testnet: {self.testnet}")

    def get_historical_candles(self, category, symbol, interval, limit=200):
        """Busca candles históricos.
           Retorna um DataFrame com os candles formatados ou None em caso de erro.
        """
        try:
            response = self.session.get_kline(
                category=category,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            if response['retCode'] == 0:
                candles = response['result']['list']
                if not candles:
                    return None
                    
                # Inverte a ordem dos candles e converte para DataFrame
                candles = candles[::-1]
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                
                # Converte os tipos das colunas
                df = df.astype({
                    'timestamp': 'int64',
                    'open': 'float64',
                    'high': 'float64',
                    'low': 'float64',
                    'close': 'float64',
                    'volume': 'float64',
                    'turnover': 'float64'
                })
                
                return df
            else:
                logger.error(f"Connector Error (get_kline): Code={response['retCode']} Msg={response['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Connector Exception (get_kline): {e}")
            return None

    def get_open_position(self, category, symbol):
        """
        Busca posição aberta para um símbolo.
        
        Args:
            category (str): Categoria da posição (spot, linear, inverse)
            symbol (str): Par de trading (ex: BTCUSDT)
        
        Returns:
            dict: Informações da posição ou None se não houver posição aberta
        """
        try:
            # Buscar posição
            response = self.session.get_positions(
                category=category,
                symbol=symbol
            )
            
            if response['retCode'] == 0:
                positions = response['result'].get('list', [])
                
                # Filtrar posições com size > 0
                open_positions = [p for p in positions if float(p.get('size', 0)) > 0]
                
                if open_positions:
                    position = open_positions[0]  # Pegar a primeira posição aberta
                    logger.info(f"Connector: Found open position - {position}")
                    return position
                else:
                    logger.info("Connector: No open position found")
                    return None
            else:
                logger.error(f"Connector Error: Failed to get position - {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Connector Error: Exception while getting position - {e}")
            return None

    def set_leverage(self, category, symbol, leverage, margin_type="Cross"):
        """
        Define a alavancagem para um símbolo.
        
        Args:
            category (str): Categoria (spot, linear, inverse)
            symbol (str): Par de trading (ex: BTCUSDT)
            leverage (int): Nível de alavancagem (1-125)
            margin_type (str): Tipo de margem (Cross ou Isolated)
            
        Returns:
            bool: True se bem sucedido, False caso contrário
        """
        try:
            # Validar categoria
            if category == "spot":
                logger.warning("Connector: Leverage not applicable for spot trading")
                return True
                
            # Validar alavancagem
            leverage = int(leverage)
            if leverage < 1 or leverage > 125:
                logger.error(f"Connector Error: Invalid leverage value {leverage}. Must be between 1 and 125.")
                return False
                
            # Caso especial: alavancagem 1 não precisa ser definida explicitamente
            if leverage == 1:
                logger.info(f"Connector: Leverage 1x is the default, no need to set it explicitly for {symbol}")
                return True
                
            # Verificar a alavancagem atual
            try:
                position_info = self.session.get_position_info(
                    category=category,
                    symbol=symbol
                )
                
                if position_info['retCode'] == 0 and position_info['result']['list']:
                    current_leverage = int(position_info['result']['list'][0]['leverage'])
                    current_margin = position_info['result']['list'][0]['marginMode']
                    
                    # Se a alavancagem e o tipo de margem já estiverem corretos, não precisa alterar
                    if current_leverage == leverage and current_margin == margin_type:
                        logger.info(f"Connector: Leverage already set to {leverage}x ({margin_type}) for {symbol}")
                        return True
            except Exception as e:
                logger.warning(f"Connector: Could not check current leverage - {e}")
                # Continua mesmo se não conseguir verificar a alavancagem atual
                
            # Preparar parâmetros
            params = {
                'category': category,
                'symbol': symbol,
                'buyLeverage': str(leverage),
                'sellLeverage': str(leverage),
                'marginMode': margin_type
            }
            
            # Definir alavancagem
            logger.info(f"Connector: Setting leverage for {symbol} to {leverage}x ({margin_type})")
            response = self.session.set_leverage(**params)
            
            if response['retCode'] == 0:
                logger.info(f"Connector: Leverage set successfully for {symbol}")
                return True
            else:
                logger.error(f"Connector Error: Failed to set leverage - {response['retMsg']}")
                return False
                
        except Exception as e:
            logger.error(f"Connector Error: Exception while setting leverage - {e}")
            return False

    def place_order(self, category, symbol, side, order_type, qty, stop_loss=None, take_profit=None, reduce_only=False, leverage=None, **kwargs):
        """
        Coloca uma ordem na Bybit.
        
        Args:
            category (str): Categoria da ordem (spot, linear, inverse)
            symbol (str): Par de trading (ex: BTCUSDT)
            side (str): Direção da ordem (Buy, Sell)
            order_type (str): Tipo da ordem (Market, Limit)
            qty (float): Quantidade da ordem
            stop_loss (float, optional): Preço do stop loss
            take_profit (float, optional): Preço do take profit
            reduce_only (bool, optional): Se a ordem deve apenas reduzir a posição
            leverage (int, optional): Nível de alavancagem (1-125)
            **kwargs: Parâmetros adicionais para a ordem
        
        Returns:
            dict: Resultado da ordem ou None se falhar
        """
        try:
            # Validar quantidade mínima
            qty = float(qty)
            if symbol == "BTCUSDT":
                if qty < 0.001:
                    logger.error(f"Connector Error: Minimum quantity for BTCUSDT is 0.001 BTC. Got: {qty}")
                    return None
            elif symbol.endswith("USDT"):
                if qty < 0.01:
                    logger.error(f"Connector Error: Minimum quantity for {symbol} is 0.01. Got: {qty}")
                    return None
            else:
                if qty < 0.001:
                    logger.error(f"Connector Error: Minimum quantity for {symbol} is 0.001. Got: {qty}")
                    return None
            # Configurar alavancagem se fornecida e não for spot
            if leverage is not None and category != "spot":
                self.set_leverage(category, symbol, leverage)
            
            # Preparar parâmetros da ordem
            order_params = {
                'category': category,
                'symbol': symbol,
                'side': side,
                'orderType': order_type,
                'qty': str(qty),  # API requer string
                'reduceOnly': reduce_only
            }

            # Adicionar stop loss e take profit se fornecidos
            if stop_loss is not None:
                order_params['stopLoss'] = str(stop_loss)
            if take_profit is not None:
                order_params['takeProfit'] = str(take_profit)
            
            # Adicionar parâmetros adicionais
            order_params.update(kwargs)
            
            # Colocar a ordem
            logger.info("Connector: Placing order with params: {order_params}")
            response = self.session.place_order(**order_params)
            
            if response['retCode'] == 0:
                logger.info(f"Connector: Order placed successfully - {response['result']}")                
                return response['result']
            else:
                logger.error(f"Connector Error: Failed to place order - {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Connector Error: Exception while placing order - {e}")
            return None

    def get_balance(self, account_type="UNIFIED", coin="USDT"):
        """Consulta o saldo de uma moeda específica na conta.
           Retorna dicionário com info do saldo ou None.
        """
        try:
            # Para conta UNIFIED, não passamos a moeda na requisição inicial
            # pois queremos o resumo da conta que contém a lista de moedas.
            request_params = {"accountType": account_type}
            if account_type != "UNIFIED":
                # Para outros tipos de conta (ex: CONTRACT), a API pode aceitar 'coin'
                request_params['coin'] = coin

            response = self.session.get_wallet_balance(**request_params)

            if response['retCode'] == 0:
                balance_list = response['result']['list']
                if not balance_list:
                    logger.info(f"Connector: Empty balance list returned for account {account_type}.")
                    return None

                if account_type == "UNIFIED":
                    # A lista deve conter um dicionário principal para a conta UNIFIED
                    if len(balance_list) > 0:
                        account_summary = balance_list[0]
                        # Procurar a moeda específica dentro da lista 'coin' deste sumário
                        coin_list = account_summary.get('coin', [])
                        coin_info = next((c for c in coin_list if c.get('coin') == coin), None)
                        if coin_info:
                            logger.info(f"Connector: Found balance for {coin} in UNIFIED account.")
                            return coin_info
                        else:
                            # Moeda não encontrada na lista, significa saldo zero ou nunca usada
                            logger.info(f"Connector: Coin '{coin}' not found within UNIFIED account summary. Assuming zero balance.")
                            # Retornar um dict com saldo zero para evitar erros no executor
                            return {'coin': coin, 'walletBalance': '0', 'availableBalance': '0'}
                    else:
                        logger.error(f"Connector Error: Unexpected empty list for UNIFIED account summary.")
                        return None
                else:
                    # Para outras contas (ex: CONTRACT), a API pode retornar a lista direta
                    # ou filtrar se 'coin' foi passado na request.
                    # Assumindo que a lista contém diretamente a info da moeda solicitada.
                    balance_info = next((item for item in balance_list if item.get('coin') == coin), None)
                    if balance_info:
                        logger.info(f"Connector: Found balance for {coin} in {account_type} account.")
                        return balance_info
                    else:
                        logger.error(f"Connector: Coin '{coin}' not found in {account_type} account response.")
                        return None # Ou retornar saldo zero como em UNIFIED?

            else:
                logger.error(f"Connector Error (get_wallet_balance): Code={response['retCode']} Msg={response['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Connector Exception (get_wallet_balance): {e}")
            return None

