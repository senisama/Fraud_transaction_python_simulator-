"""Verification script for the Banking Transaction Simulator.

Imports simulator components, generates a sample of 2,000 transactions,
and runs checks on the distributions of fraud, countries, categories, and personas
to verify statistical correctness and architectural integrity.
"""

import sys
from datetime import datetime
import pandas as pd
import numpy as np

from config import SimulatorConfig
from customers import CustomerManager
from merchants import MerchantManager
from generator import SimulationClock, TransactionGenerator


def run_verification():
    print("=== STARTING SIMULATOR VERIFICATION ===")

    # Initialize configuration
    config = SimulatorConfig(
        number_of_customers=1000,
        merchant_count=100,
        fraud_rate=0.02,
        transaction_rate_ms=10,  # Fast generation
    )
    print(f"1. Configuration initialized successfully: {config}")

    # Generate Merchants
    merchant_mgr = MerchantManager(config)
    merchants = merchant_mgr.generate_merchants()
    print(f"2. Merchants generated: count={len(merchants)}")
    assert len(merchants) == 100, f"Expected 100 merchants, got {len(merchants)}"

    # Generate Customers
    customer_mgr = CustomerManager(config.countries)
    customers = customer_mgr.generate_customers(config.number_of_customers, merchants)
    print(f"3. Customers generated: count={len(customers)}")
    assert len(customers) == 1000, f"Expected 1000 customers, got {len(customers)}"

    # Setup clock in simulated mode
    clock = SimulationClock(mode="simulated", start_time=datetime(2026, 7, 1, 12, 0, 0), speed_factor=1.0)
    
    # Setup Transaction Generator
    generator = TransactionGenerator(config, customers, merchants, clock)
    print("4. TransactionGenerator initialized successfully.")

    # Generate 2,000 transactions programmatically
    print("5. Generating 2,000 transactions...")
    tx_list = []
    
    # We loop and collect transactions.
    # Note: generator.generate_next() returns a list (to support fraud bursts)
    while len(tx_list) < 2000:
        # Advance simulated time slightly for each transaction
        clock.advance_by(pd.Timedelta(seconds=5))
        tx_list.extend(generator.generate_next())

    # Truncate to exact 2000 for analysis
    tx_list = tx_list[:2000]
    print(f"   Successfully generated {len(tx_list)} transactions.")

    # Convert to Pandas DataFrame for easy analysis
    df = pd.DataFrame([tx.to_dict() for tx in tx_list])

    # 1. Unique Transaction IDs
    unique_ids = df["transaction_id"].nunique()
    print(f"   [CHECK] Unique transaction IDs: {unique_ids} / {len(df)}")
    assert unique_ids == len(df), "Duplicate transaction IDs detected!"

    # 2. Fraud Rate Analysis
    fraud_count = df["is_fraud"].sum()
    fraud_rate = fraud_count / len(df)
    print(f"   [CHECK] Fraudulent transactions: {fraud_count} ({fraud_rate * 100:.2f}%)")
    # Expected rate is 2% trigger rate; due to velocity bursts, effective transaction fraud rate can be higher (between 0.5% and 8.0%)
    assert 0.005 <= fraud_rate <= 0.08, f"Unusual fraud rate: {fraud_rate * 100:.2f}%"

    # Merge customer profile details to verify persona and geographical stats
    cust_df = pd.DataFrame([c.__dict__ for c in customers])
    # Keep only demographic features for analysis
    cust_demographics = cust_df[["customer_id", "country", "spending_profile", "average_monthly_income"]]
    df = df.merge(cust_demographics, on="customer_id", suffixes=("", "_customer"))

    # 3. Geographical distribution (95% customer country / 5% abroad)
    # Exclude fraud transactions from this check as some fraud strategies purposefully transact abroad
    normal_df = df[~df["is_fraud"]]
    same_country_count = (normal_df["country"] == normal_df["country_customer"]).sum()
    same_country_pct = same_country_count / len(normal_df)
    print(f"   [CHECK] Domestic transactions (normal): {same_country_count} / {len(normal_df)} ({same_country_pct * 100:.2f}%)")
    # Expected is 95% same country, should be close
    assert 0.90 <= same_country_pct <= 0.98, f"Unusual domestic transaction rate: {same_country_pct * 100:.2f}%"

    # 4. Persona Spending Profiles Variance
    print("\n   [CHECK] Average Transaction Size and Count by Spending Profile:")
    summary = df.groupby("spending_profile").agg(
        tx_count=("transaction_id", "count"),
        avg_amount=("amount", "mean"),
        min_amount=("amount", "min"),
        max_amount=("amount", "max")
    ).reset_index()
    print(summary.to_string(index=False))

    # Verify that Luxury spends significantly more than Students on average
    luxury_avg = df[df["spending_profile"] == "Luxury"]["amount"].mean()
    student_avg = df[df["spending_profile"] == "Student"]["amount"].mean()
    print(f"\n   Luxury Average: €{luxury_avg:.2f} vs Student Average: €{student_avg:.2f}")
    assert luxury_avg > student_avg * 10, f"Luxury spend ({luxury_avg}) is not significantly higher than Student spend ({student_avg})"

    # 5. Diurnal volume distribution check
    # Convert timestamps to datetime to check hour-of-day counts
    df["dt_timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["dt_timestamp"].dt.hour
    late_night_txs = df[(df["hour"] >= 2) & (df["hour"] <= 5)]
    late_night_rate = len(late_night_txs) / len(df)
    print(f"   [CHECK] Late-night transactions (2 AM - 5 AM): {len(late_night_txs)} ({late_night_rate * 100:.2f}%)")
    # Expected late night to have very low weights (weight sum for 2, 3, 4, 5 is 0.5 + 0.2 + 0.2 + 1 = 1.9, compared to day hours with 7-10 weight)
    assert late_night_rate < 0.10, f"Unusually high late-night transaction rate: {late_night_rate * 100:.2f}%"

    # 6. Verify Fraud Strategy details
    fraud_txs = df[df["is_fraud"]]
    print("\n   [CHECK] Sample of generated fraud transactions:")
    cols_to_print = ["transaction_id", "spending_profile", "merchant_category", "amount", "country", "country_customer", "device", "ip_address"]
    print(fraud_txs[cols_to_print].head(10).to_string(index=False))

    print("\n=== VERIFICATION SUCCESSFULLY PASSED ===")


if __name__ == "__main__":
    try:
        run_verification()
    except AssertionError as e:
        print(f"\nAssertion Failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected Error during verification: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
