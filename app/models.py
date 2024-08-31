from pydantic import BaseModel
from typing import Dict, Union, Optional, List
from enum import Enum
from datetime import datetime

class Parameter(BaseModel):    
    key: str
    name: str
    tradeSystemName: str
    valueType: int  # Enum value of ParameterType
    default: Union[int, float, bool, str, tuple[float, int], int]  # Default value for the parameter
    minValue: Optional[Union[int, float]] = None
    maxValue: Optional[Union[int, float]] = None
    options: Optional[List[str]] = []
    restrictAutoTuning: bool = False
    displayOrder: int = 0

class ParameterValue(Parameter):
    value: Union[int, float, bool, str, tuple[float, int], int]  # The actual value

class ParameterGroup(BaseModel):
    id: str
    tradeSystemName: str
    lastUpdated: datetime
    note: Optional[str] = None
    parameters: Dict[str, ParameterValue]

class TradeStatistics(BaseModel):
    id: str
    profit: float
    maxDrawdown: float
    winRate: float
    totalTrades: int
    winningTrades: int
    losingTrades: int
    averageWin: float
    averageLoss: float
    profitFactor: float
    maxConsecutiveWins: int
    maxConsecutiveLosses: int
    averageTradeDuration: float
    largestWin: float
    largestLoss: float
    sharpeRatio: float
    sortinoRatio: float
    calmarRatio: float
    closedProfit: float
    closedLoss: float
    totalCommission: float
    maximumRunup: float
    maximumTradeRunup: float
    maximumTradeDrawdown: float
    maximumOpenPositionProfit: float
    maximumOpenPositionLoss: float
    totalLongTrades: int
    totalShortTrades: int
    totalWinningQuantity: float
    totalLosingQuantity: float
    totalFilledQuantity: float
    largestTradeQuantity: float
    timeInWinningTrades: int
    timeInLosingTrades: int
    maxConsecutiveWinners: int
    maxConsecutiveLosers: int
    lastTradeProfitLoss: float
    lastTradeQuantity: float
    lastFillDateTime: datetime
    lastEntryDateTime: datetime
    lastExitDateTime: datetime
    sessionEndDateTime: datetime
    totalBuyQuantity: float
    totalSellQuantity: float

class Session(BaseModel):
    id: str
    contextType: int # Enum value of context type
    tradeSystemName: str  # Added field to associate with a trading system
    parameterGroupId: str
    startDate: datetime
    endDate: datetime    
    tradeStatistics: TradeStatistics

class UpdateIntervalType(Enum):
    New_Bar = 0
    Always = 1

class TimeWindow(BaseModel):
    startTime: str
    endTime: str

class TradingWindow(BaseModel):
    Monday: Optional[TimeWindow] = None
    Tuesday: Optional[TimeWindow] = None
    Wednesday: Optional[TimeWindow] = None
    Thursday: Optional[TimeWindow] = None
    Friday: Optional[TimeWindow] = None
    Saturday: Optional[TimeWindow] = None
    Sunday: Optional[TimeWindow] = None

class SessionSettings(BaseModel):
    barType: str
    barPeriod: str
    updateIntervalType: UpdateIntervalType
    tradingWindow: TradingWindow

class SystemSettings(BaseModel):    
    enableLogging: bool
    liveResultsSnapshotIntervalMinutes: int

class TradingSystem(BaseModel):
    name: str
    description: Optional[str] = None      
    sessionSettings: Optional[SessionSettings] = None
    systemSettings: Optional[SystemSettings] = None    