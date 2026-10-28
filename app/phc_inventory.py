"""
Medicine inventory tracking for Primary Health Centres (PHCs) across Indian districts.
Real-time visibility into stock levels, demand patterns, and cross-district redistribution.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MedicineStock(BaseModel):
    """Current stock level at a PHC."""
    medicine_id: str
    phc_id: str
    district: str
    state: str
    quantity_available: int = Field(ge=0)
    reorder_level: int
    unit_price: float
    last_updated: datetime


class MedicineRequest(BaseModel):
    """Incoming medicine stock update from a PHC."""
    phc_id: str
    phc_name: str
    district: str
    state: str
    medicine_id: str
    medicine_name: str
    current_stock: int
    daily_usage: int  # estimated daily consumption
    population_served: int
    timestamp: datetime


class StockAlert(Enum):
    """Alert severity levels for supply chain issues."""
    NORMAL = "normal"
    LOW_STOCK = "low_stock"
    CRITICAL = "critical"
    STOCK_OUT = "stock_out"
    EXCESS = "excess"


class SupplyChainAlert(BaseModel):
    """Alert generated when anomalies detected in supply chain."""
    alert_id: str
    phc_id: str
    medicine_id: str
    alert_type: StockAlert
    severity_score: float  # 0.0 (safe) to 1.0 (critical)
    current_stock: int
    estimated_days_remaining: float
    forecast_demand: int
    recommended_action: str
    timestamp: datetime


class RedistributionRecommendation(BaseModel):
    """Recommendation to redistribute medicine across PHCs."""
    from_phc_id: str
    to_phc_id: str
    medicine_id: str
    quantity: int
    distance_km: float
    priority: int  # 1-5, higher = more urgent
    cost_estimate: float
    reason: str
