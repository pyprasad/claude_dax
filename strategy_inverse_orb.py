"""
V4 Strategy: INVERSE ORB (Fade False Breakouts)
The Professional Counter-Trend Edge on DAX

HYPOTHESIS:
-----------
V3 ORB has 22% win rate (wrong 78% of the time)
If we INVERSE all signals → Should get ~78% win rate

LOGIC:
------
DAX has constant false breakouts due to:
- Wide overnight gaps
- Thin European morning liquidity
- Institutional fade behavior
- Mean-reverting intraday structure

When ORB says "breakout up" → Price reverses down (institutions fade)
When ORB says "breakdown" → Price reverses up (institutions fade)

STRATEGY:
---------
Use exact V3 logic to detect breakout setups
Then trade THE OPPOSITE direction (fade the breakout)

Example:
- V3 detects: Close > OR High → BUY signal
- V4 executes: Close > OR High → SELL SHORT (fade the false breakout)
"""

import pandas as pd
import numpy as np
from datetime import time
from strategy_pro_v3 import ProfessionalDAXStrategyV3


class InverseORBStrategy(ProfessionalDAXStrategyV3):
    """
    V4 Inverse ORB Strategy

    Inherits all V3 logic but INVERTS the signals
    - V3 says BUY → We SELL
    - V3 says SELL → We BUY

    Hypothesis: DAX false breakouts mean fading is profitable
    """

    def __init__(self, config: dict):
        super().__init__(config)
        print("🔄 INVERSE ORB MODE: Fading all breakouts (counter-trend)")

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals using V3 logic, then INVERT them
        """
        # Get V3 signals first
        signals = super().generate_signals(data)

        # INVERT all signals
        # V3: +1 = LONG, -1 = SHORT
        # V4: +1 = SHORT (fade breakout up), -1 = LONG (fade breakout down)

        original_signals = signals['Signal'].copy()

        # Flip the direction
        signals['Signal'] = -signals['Signal']

        # Update signal names to reflect fading
        signal_map = {
            'ORB_LONG': 'FADE_ORB_HIGH',    # Was: buy breakout up, Now: sell into high
            'ORB_SHORT': 'FADE_ORB_LOW',     # Was: sell breakout down, Now: buy into low
            'VWAP_LONG': 'FADE_VWAP_HIGH',   # Fade VWAP high touches
            'VWAP_SHORT': 'FADE_VWAP_LOW',   # Fade VWAP low touches
            'MOMENTUM_LONG': 'FADE_MOMENTUM_HIGH',
            'MOMENTUM_SHORT': 'FADE_MOMENTUM_LOW'
        }

        # Rename signal types
        signals['Signal_Type'] = signals['Signal_Type'].replace(signal_map)

        # Track that these are inverted signals
        signals['Inverted'] = signals['Signal'] != 0

        return signals

    # All other methods inherited from V3
    # Position sizing, stops/targets same as V3
    # Only the DIRECTION is inverted
