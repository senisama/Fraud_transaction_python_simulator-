"""Merchants module for the banking transaction simulator.

This module manages the generation and lookup of merchant profiles, including
assigning realistic categories, locations, and pricing bounds.
"""

import random
import uuid
from typing import Dict, List, Optional

from config import SimulatorConfig
from models import Merchant


class MerchantManager:
    """Manages the lifecycle and generation of merchants."""

    # Realistic mock merchant names per category
    MERCHANT_NAMES = {
        "Restaurant": ["Bistro 88", "Pasta Palace", "Burger Joint", "Sushi Zen", "Green Salad Bar", "Taco Fiesta", "Golden Dragon", "Le Parisien", "Mama Mia Italian"],
        "Supermarket": ["Fresh Foods Market", "Walmart Supercenter", "Carrefour Express", "Mega Mart", "Corner Grocer", "Safeway", "ALDI", "Costco Wholesale", "Tesco Everyday"],
        "Streaming": ["Netflix", "Spotify Premium", "Disney+", "HBO Max", "YouTube Premium", "Apple Music", "Amazon Prime Video"],
        "Transportation": ["Uber", "Lyft Ride", "City Taxi Services", "Metro Transit", "Yellow Cab Co", "Lime Scooters", "Eurostar Train"],
        "Hotel": ["Grand Hyatt Resort", "Hilton Hotels", "Marriott Plaza", "Holiday Inn Express", "Ritz-Carlton", "Sheraton Grand", "Ibis Budget Hotel"],
        "Airline": ["Delta Air Lines", "Lufthansa", "British Airways", "Air France", "Ryanair", "Emirates Airline", "ANA Airlines", "Qantas Airways"],
        "Fuel": ["Shell Station", "BP Gas", "ExxonMobil", "TotalEnergies", "Chevron Corner", "Texaco Service", "Lukoil Depot"],
        "Luxury": ["Louis Vuitton Boutique", "Gucci Luxury", "Prada House", "Rolex Jewelers", "Cartier Paris", "Chanel Corner", "Hermès", "Tiffany & Co."],
        "Healthcare": ["City Pharmacy", "CVS Health", "Walgreens Pharmacy", "General Hospital Care", "Dental Clinic Group", "MedExpress", "Boots Pharmacy"],
        "Gaming": ["Steam Store", "Epic Games Launcher", "PlayStation Network", "Xbox Live Marketplace", "Nintendo eShop", "GOG Store"],
        "Electronics": ["Apple Store", "Samsung Experience", "Best Buy Electronics", "MediaMarkt Center", "Sony World", "Dell Technology Shop"],
        "Clothing": ["H&M Store", "Zara Fashion", "Nike Town", "Adidas Outlet", "Uniqlo Plaza", "Levi's Shop", "Gap Clothing"],
        "E-commerce": ["Amazon Marketplace", "eBay Auction House", "AliExpress Hub", "Shopify Storefront", "Etsy Crafters", "Target Online Store"],
    }

    # Cities mapping per country for consistency (shares names with customers.py)
    CITIES_BY_COUNTRY = {
        "US": ["New York", "Los Angeles", "Chicago", "Houston", "San Francisco", "Miami"],
        "FR": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes"],
        "DE": ["Berlin", "Munich", "Frankfurt", "Hamburg", "Cologne", "Stuttgart"],
        "GB": ["London", "Birmingham", "Manchester", "Glasgow", "Liverpool", "Edinburgh"],
        "JP": ["Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo"],
        "CA": ["Toronto", "Montreal", "Vancouver", "Calgary", "Ottawa"],
        "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
    }

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.merchants: Dict[str, Merchant] = {}

    def generate_merchants(self) -> List[Merchant]:
        """Generates mock merchants across categories and geographies."""
        self.merchants.clear()
        
        # For each merchant, pick category, country, city, and construct pricing bounds
        for i in range(self.config.merchant_count):
            merchant_id = f"MERCH-{1000 + i}"
            category = random.choice(self.config.categories)
            
            # Select merchant name from lists or build dynamic name
            names_pool = self.MERCHANT_NAMES.get(category, ["Generic Store"])
            base_name = random.choice(names_pool)
            # Add a suffix for uniqueness (e.g. branch number or store location ID)
            suffix = random.choice(["#1", "Express", "Main St", "Central", "Direct", "Outlet"])
            merchant_name = f"{base_name} {suffix}"

            # Distribute merchants across config countries
            country = random.choice(self.config.countries)
            cities = self.CITIES_BY_COUNTRY.get(country, ["Capital City"])
            city = random.choice(cities)

            # Price bounds setup from configuration
            min_price, max_price = self.config.category_price_bounds.get(
                category, (1.0, 100.0)
            )

            # Add minor variation to price bounds per merchant to make it realistic
            variance_factor = random.uniform(0.8, 1.2)
            merchant_min = round(min_price * variance_factor, 2)
            merchant_max = round(max_price * variance_factor, 2)

            # Ensure min is lower than max
            if merchant_min >= merchant_max:
                merchant_min, merchant_max = min(merchant_min, merchant_max), max(merchant_min, merchant_max)

            merchant = Merchant(
                merchant_id=merchant_id,
                merchant_name=merchant_name,
                category=category,
                country=country,
                city=city,
                min_price=merchant_min,
                max_price=merchant_max,
            )
            self.merchants[merchant_id] = merchant

        return list(self.merchants.values())

    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        """Fetches a specific merchant by ID."""
        return self.merchants.get(merchant_id)

    def get_random_merchant(self) -> Merchant:
        """Returns a random merchant from the registry."""
        return random.choice(list(self.merchants.values()))

    def get_merchants_by_category(self, category: str) -> List[Merchant]:
        """Filters merchants by category."""
        return [m for m in self.merchants.values() if m.category == category]

    def get_merchants_by_country(self, country: str) -> List[Merchant]:
        """Filters merchants by country."""
        return [m for m in self.merchants.values() if m.country == country]
