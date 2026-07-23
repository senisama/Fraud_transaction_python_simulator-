"""Generator module for the banking transaction simulator.

This module defines the transaction generation process, the diurnal time modulators,
and the FraudEngine using the Strategy pattern.
"""

import abc
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from config import SimulatorConfig
from models import Customer, Device, Merchant, Transaction


class SimulationClock:
    """Controls the progression of time in the simulator."""

    def __init__(self, mode: str = "realtime", start_time: datetime = None, speed_factor: float = 1.0):
        self.mode = mode  # "realtime" or "simulated"
        self.system_start = datetime.now()
        self.sim_start = start_time or datetime.now()
        self.speed_factor = speed_factor  # 1.0 means real time; 60.0 means 1 minute per real second
        self.current_sim_time = self.sim_start

    def get_time(self) -> datetime:
        """Returns the current simulated datetime."""
        if self.mode == "realtime":
            return datetime.now()
        else:
            # Advance simulated time based on elapsed system time * speed_factor
            elapsed = datetime.now() - self.system_start
            return self.sim_start + (elapsed * self.speed_factor)

    def advance_by(self, delta: timedelta):
        """Manually advances the simulated time by a delta (used in ticks)."""
        if self.mode == "simulated":
            self.sim_start += delta


class FraudStrategy(abc.ABC):
    """Abstract Base Class for fraud strategies (Strategy Pattern)."""

    @abc.abstractmethod
    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        """Applies a fraud strategy to generate one or more fraudulent transactions."""
        pass


class HighAmountFraudStrategy(FraudStrategy):
    """Simulates a sudden high-value transaction that deviates from the customer's average."""

    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        # Luxury, Electronics, or Hotels
        luxury_merchants = [
            m for m in merchants if m.category in ["Luxury", "Electronics", "Hotel", "Airline"]
        ]
        merchant = random.choice(luxury_merchants) if luxury_merchants else random.choice(merchants)

        # 15x to 40x average transaction size, clamped within merchant limits
        raw_amount = customer.average_transaction_amount * random.uniform(15.0, 40.0)
        amount = round(min(max(raw_amount, merchant.min_price), merchant.max_price), 2)

        # Uses home country or customer's known location
        country = customer.country
        city = customer.city
        currency = config.get_currency_for_country(country)
        device = random.choice(customer.devices) if customer.devices else Device(str(uuid.uuid4()), "Mobile", "127.0.0.1")

        tx = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=timestamp.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.category,
            amount=amount,
            currency=currency,
            country=country,
            city=city,
            payment_method=customer.preferred_payment_method,
            device=device.device_type,
            ip_address=device.ip_address,
            transaction_status="APPROVED",
            is_fraud=True,
        )
        return [tx]


class UnusualCountryFraudStrategy(FraudStrategy):
    """Simulates a transaction occurring in a country where the customer has no footprint."""

    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        # Filter countries different from customer's home country
        other_countries = [c for c in config.countries if c != customer.country]
        country = random.choice(other_countries) if other_countries else customer.country

        # Get merchant in that country
        abroad_merchants = [m for m in merchants if m.country == country]
        merchant = random.choice(abroad_merchants) if abroad_merchants else random.choice(merchants)
        country = merchant.country  # sync country

        currency = config.get_currency_for_country(country)
        amount = round(random.uniform(merchant.min_price, merchant.max_price * 0.5), 2)
        
        # Keep device known but location is completely different (e.g. mobile roaming)
        device = random.choice(customer.devices) if customer.devices else Device(str(uuid.uuid4()), "Mobile", "8.8.8.8")

        tx = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=timestamp.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.category,
            amount=amount,
            currency=currency,
            country=country,
            city=merchant.city,
            payment_method=customer.preferred_payment_method,
            device=device.device_type,
            ip_address=device.ip_address,
            transaction_status="APPROVED",
            is_fraud=True,
        )
        return [tx]


class ImpossibleTravelFraudStrategy(FraudStrategy):
    """Simulates a transaction location change at physically impossible speeds."""

    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        # Determine last country or default to home country
        last_country = customer.last_transaction_country or customer.country
        
        # Pick a different country for the fraud
        other_countries = [c for c in config.countries if c != last_country]
        fraud_country = random.choice(other_countries) if other_countries else "JP" if last_country != "JP" else "US"

        # Find merchants
        abroad_merchants = [m for m in merchants if m.country == fraud_country]
        merchant = random.choice(abroad_merchants) if abroad_merchants else random.choice(merchants)
        fraud_country = merchant.country

        # Create two transactions:
        # 1. A normal transaction 5 minutes ago in the customer's last country
        # 2. A fraud transaction now in the distant country
        normal_time = timestamp - timedelta(minutes=10)
        
        prev_merchants = [m for m in merchants if m.country == last_country]
        prev_m = random.choice(prev_merchants) if prev_merchants else random.choice(merchants)
        prev_device = random.choice(customer.devices) if customer.devices else Device(str(uuid.uuid4()), "Laptop", "192.168.1.50")

        tx1 = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=normal_time.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=prev_m.merchant_id,
            merchant_name=prev_m.merchant_name,
            merchant_category=prev_m.category,
            amount=round(random.uniform(prev_m.min_price, prev_m.max_price * 0.4), 2),
            currency=config.get_currency_for_country(last_country),
            country=last_country,
            city=customer.city,
            payment_method=customer.preferred_payment_method,
            device=prev_device.device_type,
            ip_address=prev_device.ip_address,
            transaction_status="APPROVED",
            is_fraud=False,
        )

        # Impossible transaction happening almost instantly in Tokyo/Paris/etc.
        fraud_device = Device(str(uuid.uuid4()), "Mobile", f"203.0.113.{random.randint(1, 254)}")
        tx2 = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=timestamp.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.category,
            amount=round(random.uniform(merchant.min_price, merchant.max_price * 0.8), 2),
            currency=config.get_currency_for_country(fraud_country),
            country=fraud_country,
            city=merchant.city,
            payment_method=customer.preferred_payment_method,
            device=fraud_device.device_type,
            ip_address=fraud_device.ip_address,
            transaction_status="APPROVED",
            is_fraud=True,
        )

        # Update customer state to make future sequence logical
        customer.last_transaction_timestamp = timestamp
        customer.last_transaction_country = fraud_country
        customer.last_transaction_city = merchant.city

        return [tx1, tx2]


class VelocityFraudStrategy(FraudStrategy):
    """Simulates cards testing where many small transactions occur in a short window."""

    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        # Choose 5 to 12 transactions in 1 minute
        num_transactions = random.randint(5, 12)
        transactions = []
        
        # High-frequency categories (E-commerce, Gaming, Streaming, Restaurants)
        micro_merchants = [
            m for m in merchants if m.category in ["E-commerce", "Gaming", "Streaming", "Restaurant"]
        ]
        
        device = Device(str(uuid.uuid4()), "Mobile", f"198.51.100.{random.randint(1, 254)}")
        current_time = timestamp

        for i in range(num_transactions):
            merchant = random.choice(micro_merchants) if micro_merchants else random.choice(merchants)
            amount = round(random.uniform(1.0, 15.0), 2)  # small amounts
            current_time += timedelta(seconds=random.randint(2, 6))

            tx = Transaction(
                transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
                timestamp=current_time.isoformat(),
                customer_id=customer.customer_id,
                merchant_id=merchant.merchant_id,
                merchant_name=merchant.merchant_name,
                merchant_category=merchant.category,
                amount=amount,
                currency=config.get_currency_for_country(customer.country),
                country=customer.country,
                city=customer.city,
                payment_method=customer.preferred_payment_method,
                device=device.device_type,
                ip_address=device.ip_address,
                transaction_status="APPROVED",
                is_fraud=True,
            )
            transactions.append(tx)

        # Record last one on customer
        customer.last_transaction_timestamp = current_time
        customer.last_transaction_country = customer.country
        customer.last_transaction_city = customer.city

        return transactions


class UnknownDeviceFraudStrategy(FraudStrategy):
    """Simulates a transaction from a new device/IP, indicating an account takeover."""

    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        online_merchants = [m for m in merchants if m.category in ["E-commerce", "Electronics", "Gaming"]]
        merchant = random.choice(online_merchants) if online_merchants else random.choice(merchants)

        # Higher than usual amount
        amount = round(customer.average_transaction_amount * random.uniform(4.0, 8.0), 2)
        amount = min(max(amount, merchant.min_price), merchant.max_price)

        # Create unknown device
        unknown_device_type = random.choice(["Mobile", "Laptop", "Tablet"])
        unknown_ip = f"103.24.11.{random.randint(1, 254)}"

        tx = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=timestamp.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.category,
            amount=amount,
            currency=config.get_currency_for_country(customer.country),
            country=customer.country,
            city=customer.city,
            payment_method="Credit Card",
            device=unknown_device_type,
            ip_address=unknown_ip,
            transaction_status="APPROVED",
            is_fraud=True,
        )
        return [tx]


class LateNightLargePurchaseStrategy(FraudStrategy):
    """Simulates a large luxury/electronics purchase in the middle of the night (2 AM to 5 AM)."""

    def apply(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        # Force hour to be late night
        adjusted_timestamp = timestamp.replace(hour=random.randint(2, 4), minute=random.randint(0, 59))
        
        expensive_merchants = [
            m for m in merchants if m.category in ["Luxury", "Electronics", "Hotel"]
        ]
        merchant = random.choice(expensive_merchants) if expensive_merchants else random.choice(merchants)

        amount = round(customer.average_transaction_amount * random.uniform(5.0, 12.0), 2)
        amount = min(max(amount, merchant.min_price), merchant.max_price)

        device = random.choice(customer.devices) if customer.devices else Device(str(uuid.uuid4()), "Mobile", "127.0.0.1")

        tx = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=adjusted_timestamp.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.category,
            amount=amount,
            currency=config.get_currency_for_country(customer.country),
            country=customer.country,
            city=customer.city,
            payment_method="Credit Card",
            device=device.device_type,
            ip_address=device.ip_address,
            transaction_status="APPROVED",
            is_fraud=True,
        )
        return [tx]


class FraudEngine:
    """Coordinates and triggers fraud strategies (Strategy Pattern)."""

    def __init__(self):
        self.strategies: List[FraudStrategy] = [
            HighAmountFraudStrategy(),
            UnusualCountryFraudStrategy(),
            ImpossibleTravelFraudStrategy(),
            VelocityFraudStrategy(),
            UnknownDeviceFraudStrategy(),
            LateNightLargePurchaseStrategy(),
        ]

    def generate_fraud(
        self,
        customer: Customer,
        merchants: List[Merchant],
        timestamp: datetime,
        config: SimulatorConfig,
    ) -> List[Transaction]:
        """Selects a fraud strategy and applies it."""
        strategy = random.choice(self.strategies)
        return strategy.apply(customer, merchants, timestamp, config)


class TransactionGenerator:
    """Core transaction state machine modulating dates, personas, location and fraud."""

    # Activity weight by hour (0 to 23)
    DIURNAL_WEIGHTS = {
        0: 4, 1: 2, 2: 0.5, 3: 0.2, 4: 0.2, 5: 1, 
        6: 4, 7: 6, 8: 7, 9: 7, 10: 7, 11: 8, 
        12: 10, 13: 9, 14: 7, 15: 7, 16: 8, 17: 9, 
        18: 10, 19: 9, 20: 8, 21: 7, 22: 6, 23: 5
    }

    # Probability matrix of categories per persona and hourly block
    # Structure: { persona: { hour_range: [ (category, weight) ] } }
    CATEGORY_PREFERENCES = {
        "Student": {
            "morning": [("Transportation", 30), ("Restaurant", 50), ("Fuel", 5), ("Supermarket", 10), ("Healthcare", 5)],
            "lunch": [("Restaurant", 60), ("Supermarket", 20), ("E-commerce", 20)],
            "afternoon": [("Gaming", 30), ("Clothing", 25), ("E-commerce", 25), ("Transportation", 20)],
            "evening": [("Streaming", 30), ("Restaurant", 40), ("Gaming", 20), ("E-commerce", 10)],
            "night": [("Streaming", 50), ("Gaming", 40), ("E-commerce", 10)]
        },
        "Employee": {
            "morning": [("Transportation", 20), ("Restaurant", 30), ("Fuel", 30), ("Supermarket", 15), ("Healthcare", 5)],
            "lunch": [("Restaurant", 50), ("Supermarket", 35), ("E-commerce", 15)],
            "afternoon": [("Supermarket", 30), ("E-commerce", 30), ("Clothing", 20), ("Healthcare", 20)],
            "evening": [("Restaurant", 40), ("Supermarket", 30), ("Streaming", 20), ("Fuel", 10)],
            "night": [("Streaming", 60), ("E-commerce", 40)]
        },
        "BusinessTraveler": {
            "morning": [("Airline", 30), ("Transportation", 40), ("Hotel", 20), ("Restaurant", 10)],
            "lunch": [("Restaurant", 60), ("Hotel", 20), ("Transportation", 20)],
            "afternoon": [("Airline", 30), ("Restaurant", 20), ("Hotel", 30), ("Transportation", 20)],
            "evening": [("Restaurant", 50), ("Hotel", 30), ("Transportation", 20)],
            "night": [("Hotel", 60), ("Airline", 20), ("Transportation", 20)]
        },
        "Luxury": {
            "morning": [("Hotel", 30), ("Restaurant", 30), ("Transportation", 30), ("Healthcare", 10)],
            "lunch": [("Restaurant", 40), ("Luxury", 40), ("Electronics", 20)],
            "afternoon": [("Luxury", 40), ("Clothing", 30), ("Electronics", 30)],
            "evening": [("Hotel", 40), ("Restaurant", 40), ("Luxury", 20)],
            "night": [("Hotel", 70), ("Luxury", 20), ("Electronics", 10)]
        }
    }

    def __init__(
        self,
        config: SimulatorConfig,
        customers: List[Customer],
        merchants: List[Merchant],
        clock: SimulationClock,
    ):
        self.config = config
        self.customers = customers
        self.merchants = merchants
        self.clock = clock
        self.fraud_engine = FraudEngine()
        
        # Buffer to queue multi-step fraud transactions (e.g. Velocity/Travel sequences)
        self.transaction_buffer: List[Transaction] = []

    def _get_time_block(self, hour: int) -> str:
        """Determines the category preference time block based on the hour."""
        if 5 <= hour < 11:
            return "morning"
        elif 11 <= hour < 14:
            return "lunch"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"

    def _select_active_customer(self, timestamp: datetime) -> Customer:
        """Selects a customer based on profile activity probability at the current hour."""
        hour = timestamp.hour
        base_weight = self.DIURNAL_WEIGHTS.get(hour, 1.0)
        
        for _ in range(15):
            customer = random.choice(self.customers)
            # Modulate activity by persona
            # Students are active later, Employees active earlier, business travelers highly active
            persona = customer.spending_profile
            
            if persona == "Student":
                persona_hour_weight = 1.5 if (18 <= hour or hour <= 2) else 0.5
            elif persona == "Employee":
                persona_hour_weight = 1.3 if (7 <= hour <= 19) else 0.2
            elif persona == "BusinessTraveler":
                persona_hour_weight = 1.2  # travel occurs at all hours
            else:  # Luxury
                persona_hour_weight = 1.0
                
            # Final roll based on relative weights
            activity_prob = (base_weight / 10.0) * persona_hour_weight
            if random.random() < activity_prob:
                return customer
                
        # Fallback
        return random.choice(self.customers)

    def generate_next(self) -> List[Transaction]:
        """Generates the next batch of transactions (returns 1 or a burst)."""
        # If there are queued transactions in the velocity/travel buffer, drain them first
        if self.transaction_buffer:
            return [self.transaction_buffer.pop(0)]

        timestamp = self.clock.get_time()
        
        # Roll for fraud
        if random.random() < self.config.fraud_rate:
            customer = random.choice(self.customers)
            fraud_txs = self.fraud_engine.generate_fraud(
                customer, self.merchants, timestamp, self.config
            )
            # Queue remainder if there's more than one
            if len(fraud_txs) > 1:
                self.transaction_buffer.extend(fraud_txs[1:])
            return [fraud_txs[0]]

        # Generate normal transaction
        customer = self._select_active_customer(timestamp)
        
        # 1. Determine Category
        block = self._get_time_block(timestamp.hour)
        prefs = self.CATEGORY_PREFERENCES.get(customer.spending_profile, {}).get(block, [("Restaurant", 100)])
        categories, weights = zip(*prefs)
        category = random.choices(categories, weights=weights, k=1)[0]

        # 2. Location Logic (95% customer country, 5% abroad)
        is_abroad = random.random() < 0.05
        if is_abroad:
            # Pick a random country other than customer's home
            other_countries = [c for c in self.config.countries if c != customer.country]
            country = random.choice(other_countries) if other_countries else customer.country
        else:
            country = customer.country

        # 3. Select Merchant
        merchant_pool = [m for m in self.merchants if m.category == category and m.country == country]
        if not merchant_pool:
            # Fallback: keep transaction country local by picking any merchant category in the target country
            merchant_pool = [m for m in self.merchants if m.country == country]
        if not merchant_pool:
            # If target country has no merchants at all, fallback to category in any country
            merchant_pool = [m for m in self.merchants if m.category == category]
        if not merchant_pool:
            # Complete fallback
            merchant_pool = self.merchants

        # Realism check: If customer has preferred merchants in this pool, higher chance to pick them
        preferred_in_pool = [m for m in merchant_pool if m.merchant_id in customer.preferred_merchants]
        if preferred_in_pool and random.random() < 0.4:
            merchant = random.choice(preferred_in_pool)
        else:
            merchant = random.choice(merchant_pool)

        # 4. Location sync (city / country)
        city = merchant.city
        country = merchant.country

        # 5. Pricing: Normal distribution around customer's average, clamped to merchant limits
        avg_amount = customer.average_transaction_amount
        raw_amount = random.normalvariate(avg_amount, avg_amount * 0.35)
        amount = round(min(max(raw_amount, merchant.min_price), merchant.max_price), 2)

        # 6. Currency
        currency = self.config.get_currency_for_country(country)

        # 7. Device (98% known device, 2% new device)
        is_known_device = random.random() < 0.98
        if is_known_device and customer.devices:
            device = random.choice(customer.devices)
            device_type = device.device_type
            ip_address = device.ip_address
        else:
            device_type = random.choice(["Mobile", "Laptop", "Tablet"])
            ip_address = f"192.168.1.{random.randint(10, 250)}" if not is_abroad else f"185.45.10.{random.randint(1, 254)}"

        # 8. Status (98% APPROVED, 2% DECLINED due to insufficient balance)
        status = "APPROVED" if random.random() < 0.98 else "DECLINED"

        tx = Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
            timestamp=timestamp.isoformat(),
            customer_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.category,
            amount=amount,
            currency=currency,
            country=country,
            city=city,
            payment_method=customer.preferred_payment_method,
            device=device_type,
            ip_address=ip_address,
            transaction_status=status,
            is_fraud=False,
        )

        # Update customer last transaction state
        customer.last_transaction_timestamp = timestamp
        customer.last_transaction_country = country
        customer.last_transaction_city = city

        return [tx]
