import pandas as pd
import sys
import time
from src.utils.logger import logger
from src.utils.email_notifier import EmailNotifier
from datetime import datetime
import os
from typing import Union, Optional, List, Dict

class StrategyExecutor:
    def __init__(self, connector, strategy):
        self.connector = connector
        self.strategy = strategy
        self.last_order_result = None
        logger.info("Strategy Executor initialized.")

    def _get_base_asset(self, symbol):
        # Assume USDT ou USD como quote asset por enquanto
        if symbol.endswith("USDT"):
            return symbol[:-4]
        elif symbol.endswith("USD"):
            return symbol[:-3]
        # Adicionar lógica para outros quotes se necessário
        return symbol # Fallback

    def calculate_order_size(self, category, symbol, close_price):
        account_type = "UNIFIED" # ou "CONTRACT" dependendo da conta/categoria
        if category == "spot":
            account_type = "SPOT" # ou UNIFIED se usar conta unificada

        # Buscar saldo da moeda de cotação (ex: USDT)
        quote_coin = "USDT" # Assumir USDT por padrão
        if category == "inverse":
            # Para inversos, a cotação é a base (ex: BTC em BTCUSD)
            quote_coin = self._get_base_asset(symbol)
        elif category == "spot":
             # Para spot, pode ser USDT ou outra moeda (ex: BTC em ETHBTC)
             # Esta lógica precisa ser robusta
             if symbol.endswith("USDT"):
                 quote_coin = "USDT"
             elif symbol.endswith("BTC"):
                 quote_coin = "BTC"
             # Adicionar mais casos ou pegar do config
             else:
                 quote_coin = "USDT" # Fallback

        logger.info(f"Executor: Getting balance for {quote_coin} (Account: {account_type})")
        balance_info = self.connector.get_balance(account_type=account_type, coin=quote_coin)

        if not balance_info or 'walletBalance' not in balance_info:
            logger.error(f"Executor Error: Could not get valid balance for {quote_coin}. Cannot calculate order size.")
            return None

        # Calcular o valor investido com base no investment_percent
        available_balance = float(balance_info['walletBalance'])
        investment_percent = self.strategy.investment_percent if hasattr(self.strategy, 'investment_percent') else 100
        capital_to_use = available_balance * (investment_percent / 100)
        
        logger.info(f"Executor: Available balance: {available_balance:.2f} {quote_coin}, Investment percent: {investment_percent}%, Capital to use: {capital_to_use:.2f} {quote_coin}")
        
        # Calcular a quantidade da ordem
        order_qty = capital_to_use / close_price
        
        # Arredondar a quantidade para o número correto de casas decimais
        if symbol == "BTCUSDT":
            order_qty = round(order_qty, 3)  # 3 casas decimais para BTC
            if order_qty < 0.001:
                order_qty = 0.001  # Quantidade mínima para BTC
        elif symbol.endswith("USDT"):
            order_qty = round(order_qty, 2)  # 2 casas decimais para outros pares USDT
            if order_qty < 0.01:
                order_qty = 0.01  # Quantidade mínima para outros pares USDT
        else:
            order_qty = round(order_qty, 3)  # 3 casas decimais para outros pares
            if order_qty < 0.001:
                order_qty = 0.001  # Quantidade mínima para outros pares
        
        # Adicionar o valor investido ao metadata
        metadata = {
            'capital_to_use': capital_to_use,
            'quote_coin': quote_coin,
            'close_price': close_price,
            'order_qty': order_qty
        }
        
        # Atualizar o metadata da estratégia
        self.strategy.update_metadata(metadata)
        
        logger.info(f"Executor: Order size calculated - Qty: {order_qty} {self._get_base_asset(symbol)}, Value: {order_qty * close_price:.2f} {quote_coin}")
        
        return order_qty

    def run(self, category, symbol, interval):
        """
        Executa a estratégia.
        """
        logger.info(f"Executor: Starting strategy execution for {symbol} on {interval} timeframe")
        
        try:
            # 1. Buscar candles históricos
            df = self.connector.get_historical_candles(category, symbol, interval)
            if df is None:
                logger.info("Executor: No candles data available.")
                return
            
            # 2. Verificar posição atual
            current_position = self.connector.get_open_position(category, symbol)
            
            if current_position:
                position_side = 'long' if current_position.get('side') == 'Buy' else 'short'
                position_size = float(current_position.get('size', 0))
                entry_price = float(current_position.get('entryPrice', 0))
                
                # Atualizar o metadata com a posição atual
                self.strategy.update_metadata({
                    'position_side': position_side,
                    'position_size': position_size,
                    'entry_price': entry_price,
                    'close_price': df['close'].iloc[-1]  # Adicionar preço de fechamento atual
                })

                # Se tem stop loss, deixa a corretora gerenciar
                stop_loss = current_position.get('stopLoss')
                
                if stop_loss is not None and stop_loss != '':
                    logger.info(f"Executor: Position has stop loss set at {stop_loss}. Letting exchange handle exit.")
                    return
            else:
                # Limpar o metadata da posição
                self.strategy.update_metadata({
                    'position_side': None,
                    'position_size': 0,
                    'entry_price': 0,
                    'close_price': df['close'].iloc[-1]  # Adicionar preço de fechamento atual
                })
            
            # 3. Calcular o valor investido antes de chamar a estratégia
            last_close = float(df['close'].iloc[-1])
            order_size = self.calculate_order_size(category, symbol, last_close)
            
            if order_size:
                # 4. Calcular indicadores e sinais
                df = self.strategy.calculate_signals(df, self.strategy.metadata)
                
                # 5. Verificar sinais de entrada/saída
                last_row = df.iloc[-1]
                
                # 6. Executar ordens se necessário
                if current_position:
                    # Posicionado - Verificar sinais de saída
                    should_close = False
                    
                    if position_side == 'long' and last_row.get('exit_long', 0) == 1:
                        logger.info("Executor: Signal to exit LONG position")
                        should_close = True
                        close_side = 'Sell'
                    elif position_side == 'short' and last_row.get('exit_short', 0) == 1:
                        logger.info("Executor: Signal to exit SHORT position")
                        should_close = True
                        close_side = 'Buy'
                    
                    if should_close:
                        # Preparar parâmetros da ordem de fechamento
                        order_params = {
                            'category': category,
                            'symbol': symbol,
                            'side': close_side,
                            'order_type': 'Market',
                            'qty': position_size,
                            'reduce_only': True
                        }
                        
                        # Executar a ordem
                        order_result = self.connector.place_order(**order_params)
                        if order_result:
                            logger.info(f"Executor: Position closed successfully - {order_result}")
                            
                            # Limpar o metadata da posição
                            self.strategy.update_metadata({
                                'position_side': None,
                                'position_size': 0,
                                'entry_price': 0,
                                'close_price': last_close,
                                'last_order': order_result
                            })
                        else:
                            logger.error("Executor Error: Failed to close position")
                
                else:
                    # Não posicionado - Verificar sinais de entrada
                    should_enter = False
                    
                    if last_row.get('enter_long', 0) == 1:
                        logger.info(f"Executor: Signal to enter LONG position with size {order_size}")
                        should_enter = True
                        entry_side = 'Buy'
                        new_position_side = 'long'
                    elif last_row.get('enter_short', 0) == 1:
                        logger.info(f"Executor: Signal to enter SHORT position with size {order_size}")
                        should_enter = True
                        entry_side = 'Sell'
                        new_position_side = 'short'
                    
                    if should_enter:
                        # Preparar parâmetros da ordem de entrada
                        order_params = {
                            'category': category,
                            'symbol': symbol,
                            'side': entry_side,
                            'order_type': 'Market',
                            'qty': order_size
                        }
                        
                        # Adicionar stop loss e take profit se disponíveis
                        if 'stop_loss' in last_row:
                            sl_value = float(last_row['stop_loss'])
                            if sl_value > 0:
                                order_params['stop_loss'] = sl_value
                        
                        if 'take_profit' in last_row:
                            tp_value = float(last_row['take_profit'])
                            if tp_value > 0:
                                order_params['take_profit'] = tp_value
                        
                        # Adicionar alavancagem da estratégia
                        order_params['leverage'] = self.strategy.leverage
                        
                        # Executar a ordem
                        order_result = self.connector.place_order(**order_params)
                        if order_result:
                            logger.info(f"Executor: Order placed successfully - {order_result}")
                            
                            # Atualizar o metadata com o resultado da ordem
                            self.strategy.update_metadata({
                                'last_order': order_result,
                                'position_side': new_position_side,
                                'position_size': order_size,
                                'entry_price': last_close,
                                'close_price': last_close
                            })
                            
                            # Envia notificação por email
                            EmailNotifier().send_email(
                                subject=f"Robô executou uma ordem - {symbol} - {entry_side} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                content={
                                    "title": "Ordem Executada",
                                    "symbol": symbol,
                                    "side": entry_side,
                                    "price": last_close,
                                    "quantity": order_size,
                                    "leverage": self.strategy.leverage,
                                    "stop_loss": order_params.get('stop_loss'),
                                    "take_profit": order_params.get('take_profit')    
                                }
                            )
                        else:
                            logger.error("Executor Error: Failed to place order")
            
        except Exception as e:
            logger.error(f"Executor Error: {e}")
            logger.exception("Detailed error information:")

