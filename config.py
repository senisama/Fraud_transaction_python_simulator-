"""Configuration module for the banking transaction simulator.

This module defines configuration options, target directories, country-currency mappings,
and pricing distributions for merchants.
"""

import os
from typing import Dict, List


class SimulatorConfig:
    """Configuration class for the transaction simulator."""

    def __init__(
        self,
        number_of_customers: int = 1500,
        transaction_rate_ms: int = 100,
        fraud_rate: float = 0.02,
        output_directory: str = "output",
        countries: List[str] = None,
        merchant_count: int = 100,
    ):
        self.number_of_customers = number_of_customers
        self.transaction_rate_ms = transaction_rate_ms
        self.fraud_rate = fraud_rate
        
        # Resolve output directory absolute path relative to simulator root if not absolute
        if os.path.isabs(output_directory):
            self.output_directory = output_directory
        else:
            self.output_directory = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), output_directory
            )
            
        self.countries = countries or ["US", "FR", "DE", "GB", "JP", "CA", "AU"]
        self.merchant_count = merchant_count

        # Country to Currency mapping
        self.country_to_currency: Dict[str, str] = {
            "US": "USD",
            "FR": "EUR",
            "DE": "EUR",
            "GB": "GBP",
            "JP": "JPY",
            "CA": "CAD",
            "AU": "AUD",
        }

        # Categories list
        self.categories: List[str] = [
            "Restaurant",
            "Supermarket",
            "Streaming",
            "Transportation",
            "Hotel",
            "Airline",
            "Fuel",
            "Luxury",
            "Healthcare",
            "Gaming",
            "Electronics",
            "Clothing",
            "E-commerce",
        ]

        # Price bounds per category: (min_price, max_price)
        self.category_price_bounds: Dict[str, tuple] = {
            "Restaurant": (10.0, 80.0),
            "Supermarket": (15.0, 250.0),
            "Streaming": (5.0, 25.0),
            "Transportation": (5.0, 50.0),
            "Hotel": (80.0, 500.0),
            "Airline": (100.0, 1500.0),
            "Fuel": (30.0, 120.0),
            "Luxury": (500.0, 10000.0),
            "Healthcare": (20.0, 300.0),
            "Gaming": (10.0, 100.0),
            "Electronics": (100.0, 3000.0),
            "Clothing": (20.0, 400.0),
            "E-commerce": (10.0, 500.0),
        }

    def get_currency_for_country(self, country: str) -> str:
        """Returns the currency code for a given country code."""
        return self.country_to_currency.get(country, "USD")

    def __repr__(self) -> str:
        return (
            f"SimulatorConfig(number_of_customers={self.number_of_customers}, "
            f"transaction_rate_ms={self.transaction_rate_ms}, "
            f"fraud_rate={self.fraud_rate}, "
            f"output_directory='{self.output_directory}', "
            f"countries={self.countries}, "
            f"merchant_count={self.merchant_count})"
        )
