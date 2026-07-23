"""Customers module for the banking transaction simulator.

This module implements the Factory pattern for generating realistic Customer profiles
and the CustomerManager to manage the customer registry.
"""

import random
import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional
from faker import Faker

from models import Customer, Device, Merchant


class CustomerFactory:
    """Factory class to create Customer objects with realistic personas."""

    # Cities mapping per country for consistency
    CITIES_BY_COUNTRY = {
        "US": ["New York", "Los Angeles", "Chicago", "Houston", "San Francisco", "Miami"],
        "FR": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes"],
        "DE": ["Berlin", "Munich", "Frankfurt", "Hamburg", "Cologne", "Stuttgart"],
        "GB": ["London", "Birmingham", "Manchester", "Glasgow", "Liverpool", "Edinburgh"],
        "JP": ["Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo"],
        "CA": ["Toronto", "Montreal", "Vancouver", "Calgary", "Ottawa"],
        "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
    }

    @staticmethod
    def _create_devices(faker: Faker) -> List[Device]:
        """Generates 1 to 3 devices for a customer."""
        device_types = ["Mobile", "Laptop", "Tablet"]
        num_devices = random.choice([1, 2, 3])
        devices = []
        for _ in range(num_devices):
            devices.append(
                Device(
                    device_id=str(uuid.uuid4()),
                    device_type=random.choice(device_types),
                    ip_address=faker.ipv4(),
                )
            )
        return devices

    @classmethod
    def create_customer(
        self,
        customer_id: str,
        spending_profile: str,
        countries: List[str],
        faker: Faker,
    ) -> Customer:
        """Creates a single Customer based on their spending profile (persona)."""
        # Determine demographic parameters based on persona
        if spending_profile == "Student":
            age = random.randint(18, 25)
            avg_monthly_income = round(random.uniform(500, 1500), 2)
            avg_transaction_amount = round(random.uniform(5, 25), 2)
            preferred_methods = ["Mobile", "Debit Card"]
        elif spending_profile == "Employee":
            age = random.randint(26, 60)
            avg_monthly_income = round(random.uniform(2000, 6000), 2)
            avg_transaction_amount = round(random.uniform(20, 80), 2)
            preferred_methods = ["Credit Card", "Debit Card"]
        elif spending_profile == "BusinessTraveler":
            age = random.randint(28, 65)
            avg_monthly_income = round(random.uniform(5000, 12000), 2)
            avg_transaction_amount = round(random.uniform(60, 200), 2)
            preferred_methods = ["Credit Card"]
        elif spending_profile == "Luxury":
            age = random.randint(30, 75)
            avg_monthly_income = round(random.uniform(15000, 50000), 2)
            avg_transaction_amount = round(random.uniform(200, 1500), 2)
            preferred_methods = ["Credit Card", "Mobile"]
        else:
            # Fallback
            age = random.randint(18, 70)
            avg_monthly_income = round(random.uniform(1500, 5000), 2)
            avg_transaction_amount = round(random.uniform(10, 100), 2)
            preferred_methods = ["Debit Card", "Credit Card", "Mobile"]

        # Basic identity details
        gender = random.choices(["M", "F", "Other"], weights=[48, 48, 4], k=1)[0]
        if gender == "M":
            first_name = faker.first_name_male()
        elif gender == "F":
            first_name = faker.first_name_female()
        else:
            first_name = faker.first_name()
        last_name = faker.last_name()

        # Location details
        country = random.choice(countries)
        cities = self.CITIES_BY_COUNTRY.get(country, ["Capital City"])
        city = random.choice(cities)

        # Account creation (1 to 5 years ago)
        account_days_ago = random.randint(365, 365 * 5)
        account_creation_date = date.today() - timedelta(days=account_days_ago)

        # Payment card generation
        card_brand = random.choice(["Visa", "Mastercard", "Amex"])
        card_num = faker.credit_card_number(card_type=card_brand.lower())
        masked_card = f"{card_brand} **** {card_num[-4:]}"

        preferred_payment_method = random.choice(preferred_methods)
        devices = self._create_devices(faker)

        return Customer(
            customer_id=customer_id,
            first_name=first_name,
            last_name=last_name,
            age=age,
            gender=gender,
            country=country,
            city=city,
            account_creation_date=account_creation_date,
            payment_card=masked_card,
            preferred_payment_method=preferred_payment_method,
            average_monthly_income=avg_monthly_income,
            spending_profile=spending_profile,
            preferred_merchants=[],
            average_transaction_amount=avg_transaction_amount,
            devices=devices,
        )


class CustomerManager:
    """Manages the generation, lookup, and maintenance of simulation customers."""

    def __init__(self, countries: List[str]):
        self.countries = countries
        self.customers: Dict[str, Customer] = {}
        self.faker = Faker()

    def generate_customers(self, count: int, merchants: List[Merchant]) -> List[Customer]:
        """Generates a complete registry of persistent customer profiles."""
        self.customers.clear()
        
        # Personas weights
        personas = ["Student", "Employee", "BusinessTraveler", "Luxury"]
        weights = [0.25, 0.50, 0.15, 0.10]  # 25% students, 50% employees, 15% business travelers, 10% luxury

        # Categorize merchants for mapping customer preferences
        merchants_by_profile = self._group_merchants_by_profile(merchants)

        for _ in range(count):
            customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
            spending_profile = random.choices(personas, weights=weights, k=1)[0]
            
            customer = CustomerFactory.create_customer(
                customer_id=customer_id,
                spending_profile=spending_profile,
                countries=self.countries,
                faker=self.faker,
            )

            # Assign preferred merchants based on spending profile
            candidate_merchants = merchants_by_profile.get(spending_profile, merchants)
            num_prefs = min(random.randint(3, 7), len(candidate_merchants))
            customer.preferred_merchants = [
                m.merchant_id for m in random.sample(candidate_merchants, num_prefs)
            ]

            self.customers[customer_id] = customer

        return list(self.customers.values())

    def get_random_customer(self) -> Customer:
        """Returns a random customer from the manager's registry."""
        return random.choice(list(self.customers.values()))

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Fetches a specific customer by ID."""
        return self.customers.get(customer_id)

    @staticmethod
    def _group_merchants_by_profile(merchants: List[Merchant]) -> Dict[str, List[Merchant]]:
        """Groups merchants into sets matching customer personas."""
        groups = {
            "Student": [],
            "Employee": [],
            "BusinessTraveler": [],
            "Luxury": [],
        }
        for m in merchants:
            cat = m.category
            # Student likes: Restaurant, Streaming, Gaming, Transportation, Clothing, E-commerce
            if cat in ["Restaurant", "Streaming", "Gaming", "Transportation", "Clothing", "E-commerce"]:
                groups["Student"].append(m)
            # Employee likes: Supermarket, Fuel, Restaurant, E-commerce, Healthcare, Electronics
            if cat in ["Supermarket", "Fuel", "Restaurant", "E-commerce", "Healthcare", "Electronics"]:
                groups["Employee"].append(m)
            # BusinessTraveler likes: Hotel, Airline, Restaurant, Transportation
            if cat in ["Hotel", "Airline", "Restaurant", "Transportation", "Fuel"]:
                groups["BusinessTraveler"].append(m)
            # Luxury likes: Luxury, Hotel, Airline, Electronics, Restaurant
            if cat in ["Luxury", "Hotel", "Airline", "Electronics", "Restaurant"]:
                groups["Luxury"].append(m)

        # Fallback if any profile lists are empty
        for key, val in groups.items():
            if not val:
                groups[key] = merchants

        return groups
