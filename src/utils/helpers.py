

import pandas as pd
from datetime import datetime

def format_datetime(dt):
    """Formata um objeto datetime para string."""
    if isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)

def calculate_percentage_change(old_value, new_value):
    """Calcula a variação percentual entre dois números."""
    if old_value is None or new_value is None or old_value == 0:
        return 0.0
    try:
        return ((float(new_value) - float(old_value)) / float(old_value)) * 100
    except (ValueError, TypeError):
        return 0.0



