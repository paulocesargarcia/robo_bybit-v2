from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd
from pandas import DataFrame
from src.utils.logger import logger
import numpy as np

class BaseStrategy(ABC):
    
    stop_loss = None
    take_profit = None    
    leverage = 1  # Valor padrão
    investment_percent = None
    
    def __init__(self, config: Dict):
        self.config = config
        self.name = self.__class__.__name__
        self.metadata = {}  # Inicializar metadata vazio

    def update_metadata(self, metadata: dict):
        """Atualiza o metadata da estratégia."""
        self.metadata.update(metadata)
        logger.info(f"Strategy: Metadata updated - {metadata}")

    @abstractmethod
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adiciona indicadores técnicos ao dataframe.
        Semelhante ao freqtrade, esta função deve adicionar todos os indicadores necessários.
        """
        pass

    @abstractmethod
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Baseado nos indicadores, define os sinais de entrada.
        Deve adicionar as colunas:
        - enter_long: Sinal para entrar long (True/False)
        - enter_short: Sinal para entrar short (True/False)
        """
        pass

    @abstractmethod
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Baseado nos indicadores, define os sinais de saída.
        Deve adicionar as colunas:
        - exit_long: Sinal para sair de long (True/False)
        - exit_short: Sinal para sair de short (True/False)
        """
        pass

    def populate_stop_loss(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define a lógica de stop loss para a estratégia.
        Para posições long: stop = close - (close * stop_loss)
        Para posições short: stop = close + (close * |stop_loss|)
        """
        if self.stop_loss is not None:
            # Converte stop_loss para valor positivo para cálculos
            stop_percent = float(self.stop_loss)
            close_prices = dataframe['close'].to_numpy(dtype=np.float64)
            
            # Calcula stop loss para posições long
            long_mask = dataframe['enter_long'] == 1
            if long_mask.any():
                long_stops = close_prices - (close_prices * stop_percent)
                dataframe.loc[long_mask, 'stop_loss'] = long_stops[long_mask]
            
            # Calcula stop loss para posições short
            short_mask = dataframe['enter_short'] == 1
            if short_mask.any():
                short_stops = close_prices + (close_prices * stop_percent)
                dataframe.loc[short_mask, 'stop_loss'] = short_stops[short_mask]
            
        return dataframe

    def populate_take_profit(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define a lógica de take profit para a estratégia.
        Para posições long: tp = close + (close * take_profit)
        Para posições short: tp = close - (close * take_profit)
        """
        if self.take_profit is not None:
            # Converte take_profit para valor positivo para cálculos
            tp_percent = float(self.take_profit)
            close_prices = dataframe['close'].to_numpy(dtype=np.float64)
            
            # Calcula take profit para posições long
            long_mask = dataframe['enter_long'] == 1
            if long_mask.any():
                long_tps = close_prices + (close_prices * tp_percent)
                dataframe.loc[long_mask, 'take_profit'] = long_tps[long_mask]
            
            # Calcula take profit para posições short
            short_mask = dataframe['enter_short'] == 1
            if short_mask.any():
                short_tps = close_prices - (close_prices * tp_percent)
                dataframe.loc[short_mask, 'take_profit'] = short_tps[short_mask]
            
        return dataframe

    def calculate_signals(self, dataframe: DataFrame, metadata: Optional[dict] = None) -> DataFrame:
        """
        Método principal que calcula todos os sinais.
        As estratégias podem sobrescrever este método se precisarem de lógica adicional.
        """
        if metadata is not None:
            self.update_metadata(metadata)        
        
        # 1. Inicializar colunas de sinais
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['stop_loss'] = np.zeros(len(dataframe))
        dataframe['take_profit'] = np.zeros(len(dataframe))

        # 2. Popular indicadores
        dataframe = self.populate_indicators(dataframe, self.metadata)

        # 3. Popular sinais de entrada
        dataframe = self.populate_entry_trend(dataframe, self.metadata)

        # 4. Popular sinais de saída
        dataframe = self.populate_exit_trend(dataframe, self.metadata)

        # 5. Popular stop loss e take profit
        dataframe = self.populate_stop_loss(dataframe, self.metadata)
        dataframe = self.populate_take_profit(dataframe, self.metadata)
        
        # 6. Log dos últimos valores para debug
        last_row = dataframe.iloc[-1]
        logger.info(f"Strategy: Last row - Close: {last_row['close']:.2f}, EnterLong: {last_row.get('enter_long', 0)}, "
                   f"EnterShort: {last_row.get('enter_short', 0)}, ExitLong: {last_row.get('exit_long', 0)}, "
                   f"ExitShort: {last_row.get('exit_short', 0)}, StopLoss: {last_row.get('stop_loss', 0):.2f}, "
                   f"TakeProfit: {last_row.get('take_profit', 0):.2f}")

        return dataframe
