import pandas as pd
from pandas import DataFrame
import pandas_ta as ta
import numpy as np
from typing import Dict, List, Optional
from .base_strategy import BaseStrategy
from src.utils.logger import logger

class SimpleCrossShortTest(BaseStrategy):
    """
    Estratégia de cruzamento de médias móveis .
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Parâmetros da estratégia
        self.ema_fast = 2
        self.ema_slow = 4
        self.leverage = 1
        self.investment_percent = 10
        
        # Stop Loss e Take Profit em porcentagem do capital investido
        self.stoploss = 0.02  # 2% do valor de entrada
        self.takeprofit = 0.04  # 4% do valor de entrada
        
        # Período de lookback para cálculos
        self.lookback_period = self.ema_slow + 51

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calcula os indicadores técnicos."""
        dataframe['ema_fast'] = ta.ema(dataframe['close'], length=self.ema_fast)
        dataframe['ema_slow'] = ta.ema(dataframe['close'], length=self.ema_slow)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define os sinais de entrada."""
        dataframe.loc[
            (                
                (dataframe["ema_fast"].shift(1) < dataframe["ema_slow"].shift(2))
            ),
            "enter_short",
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define os sinais de saída."""
        dataframe.loc[
            (                
                (dataframe["ema_fast"].shift(1) > dataframe["ema_slow"].shift(2))
            ),
            "exit_short",
        ] = 1
        
        return dataframe

    