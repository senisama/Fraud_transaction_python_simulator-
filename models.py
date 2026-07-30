"""Data models for the banking transaction simulator.

This module uses Python dataclasses to represent core domain models:
Device, Customer, Merchant, and Transaction.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class Device:
    """Represents a device owned by a customer."""
    device_id: str
    device_type: str  # Mobile, Laptop, Tablet
    ip_address: str


@dataclass
class Customer:
    """Represents a banking customer profile."""
    customer_id: str
    first_name: str
    last_name: str
    age: int
    gender: str
    country: str
    city: str
    account_creation_date: date
    payment_card: str
    preferred_payment_method: str
    average_monthly_income: float
    spending_profile: str  # Student, Employee, BusinessTraveler, Luxury
    preferred_merchants: List[str] = field(default_factory=list)
    average_transaction_amount: float = 0.0
    devices: List[Device] = field(default_factory=list)

    # Runtime state trackers for simulating velocity and geographic checks
    last_transaction_timestamp: Optional[datetime] = None
    last_transaction_country: Optional[str] = None
    last_transaction_city: Optional[str] = None
    recent_transactions: List[datetime] = field(default_factory=list)

    def record_transaction(self, ts: datetime) -> int:
        """Records a transaction timestamp and returns count of transactions in the last 10 minutes."""
        cutoff = ts - timedelta(minutes=10)
        self.recent_transactions = [t for t in self.recent_transactions if t >= cutoff]
        count = len(self.recent_transactions)
        self.recent_transactions.append(ts)
        self.last_transaction_timestamp = ts
        return count


@dataclass
class Merchant:
    """Represents a merchant accepting transactions."""
    merchant_id: str
    merchant_name: str
    category: str
    country: str
    city: str
    min_price: float
    max_price: float


@dataclass
class Transaction:
    """Represents a single banking transaction."""
    transaction_id: str
    timestamp: str  # ISO 8601 string
    customer_id: str
    customer_country: str
    merchant_id: str
    merchant_name: str
    merchant_category: str
    amount: float
    currency: str
    country: str
    city: str
    payment_method: str
    device: str
    ip_address: str
    transaction_status: str  # APPROVED, DECLINED
    hour: int
    transactions_last_10min: int
    is_fraud: bool

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Transaction object to a serializable dictionary, omitting internal is_fraud tag."""
        data = asdict(self)
        data.pop("is_fraud", None)
        return data
