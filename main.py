"""Main module for the banking transaction simulator.

This module sets up CLI argument parsing, logging, initializes the managers
and engines, handles output redirection, and hosts the real-time simulation loop.
"""

import abc
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict

from config import SimulatorConfig
from customers import CustomerManager
from generator import SimulationClock, TransactionGenerator
from merchants import MerchantManager
from models import Transaction


class OutputWriter(abc.ABC):
    """Abstract Base Class for transaction output routing (Output Isolation)."""

    @abc.abstractmethod
    def write(self, transaction: Transaction) -> None:
        """Writes the transaction data to the destination."""
        pass

    @abc.abstractmethod
    def close(self) -> None:
        """Closes any open resources."""
        pass


class ConsoleOutputWriter(OutputWriter):
    """Outputs transactions to the standard output console."""

    def write(self, transaction: Transaction) -> None:
        sys.stdout.write(json.dumps(transaction.to_dict()) + "\n")
        sys.stdout.flush()

    def close(self) -> None:
        pass


class NDJSONFileOutputWriter(OutputWriter):
    """Writes transactions to a single rotating newline-delimited JSON (NDJSON) file.

    Ideal for Apache NiFi's TailFile processor.
    """

    def __init__(self, output_dir: str, filename: str = "transactions.log"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.filepath = os.path.join(self.output_dir, filename)
        # Open in append mode
        self.file = open(self.filepath, "a", encoding="utf-8")

    def write(self, transaction: Transaction) -> None:
        self.file.write(json.dumps(transaction.to_dict()) + "\n")
        self.file.flush()

    def close(self) -> None:
        if self.file and not self.file.closed:
            self.file.close()


class IndividualJSONOutputWriter(OutputWriter):
    """Writes each transaction as an individual JSON file in the output directory.

    Ideal for Apache NiFi's GetFile/FetchFile processors which ingest and clean up files.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write(self, transaction: Transaction) -> None:
        # Create a unique filename for each transaction
        filepath = os.path.join(
            self.output_dir, f"tx_{transaction.transaction_id}.json"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(transaction.to_dict(), f, indent=2)

    def close(self) -> None:
        pass


def setup_logger() -> logging.Logger:
    """Configures systemic logging to standard error."""
    logger = logging.getLogger("BankingSimulator")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def main():
    logger = setup_logger()
    logger.info("Initializing Banking Transaction Simulator...")

    # CLI Arguments setup
    parser = argparse.ArgumentParser(description="Real-Time Banking Transaction Simulator")
    parser.add_argument(
        "--customers", type=int, default=1500, help="Number of persistent customer profiles to generate"
    )
    parser.add_argument(
        "--rate", type=int, default=100, help="Transaction frequency in milliseconds"
    )
    parser.add_argument(
        "--fraud", type=float, default=0.02, help="Fraud rate percentage (0.0 to 1.0)"
    )
    parser.add_argument(
        "--merchants", type=int, default=100, help="Number of merchants to generate"
    )
    parser.add_argument(
        "--output-dir", type=str, default="output", help="Directory for JSON files"
    )
    parser.add_argument(
        "--writer",
        type=str,
        choices=["console", "ndjson", "individual"],
        default="ndjson",
        help="Output writer mode: console, ndjson (append log), or individual (separate JSONs)",
    )
    parser.add_argument(
        "--simulated-time",
        action="store_true",
        help="Use accelerated simulation time instead of system clock",
    )
    parser.add_argument(
        "--sim-speed",
        type=float,
        default=3000.0,
        help="Simulated time speed multiplier. (e.g. 3000 means 1 real second = 50 simulated minutes)",
    )

    args = parser.parse_args()

    # Instantiate Configuration
    config = SimulatorConfig(
        number_of_customers=args.customers,
        transaction_rate_ms=args.rate,
        fraud_rate=args.fraud,
        output_directory=args.output_dir,
        merchant_count=args.merchants,
    )

    logger.info(f"Loaded Configuration: {config}")

    # Generate Merchants
    logger.info(f"Generating {config.merchant_count} merchants...")
    merchant_manager = MerchantManager(config)
    merchants = merchant_manager.generate_merchants()
    logger.info(f"Successfully generated {len(merchants)} merchants.")

    # Generate Customers
    logger.info(f"Generating {config.number_of_customers} customers...")
    customer_manager = CustomerManager(config.countries)
    customers = customer_manager.generate_customers(config.number_of_customers, merchants)
    logger.info(f"Successfully generated {len(customers)} customers.")

    # Setup Simulation Clock
    if args.simulated_time:
        # Start simulated clock from 7 days ago
        start_time = datetime.now() - timedelta(days=7)
        clock = SimulationClock(mode="simulated", start_time=start_time, speed_factor=args.sim_speed)
        logger.info(
            f"Using SIMULATED CLOCK starting at {start_time.isoformat()} (Speed factor: {args.sim_speed}x)"
        )
    else:
        clock = SimulationClock(mode="realtime")
        logger.info("Using SYSTEM REALTIME CLOCK.")

    # Setup Transaction Generator
    generator = TransactionGenerator(config, customers, merchants, clock)

    # Resolve Output Writer
    if args.writer == "console":
        writer = ConsoleOutputWriter()
    elif args.writer == "individual":
        writer = IndividualJSONOutputWriter(config.output_directory)
    else:
        writer = NDJSONFileOutputWriter(config.output_directory)

    logger.info(f"Selected Output Writer: {type(writer).__name__}")
    logger.info(f"Outputs will be written to: {config.output_directory}")
    logger.info("Starting simulation loop. Press Ctrl+C to stop.")

    # Statistics Trackers
    stats: Dict[str, int] = {
        "total_transactions": 0,
        "approved": 0,
        "declined": 0,
        "fraud": 0,
        "normal": 0,
    }

    last_stats_log = time.time()
    try:
        while True:
            # Generate next batch of transactions
            tx_batch = generator.generate_next()
            
            for tx in tx_batch:
                # Write to chosen output target
                writer.write(tx)
                
                # Update statistics
                stats["total_transactions"] += 1
                if tx.is_fraud:
                    stats["fraud"] += 1
                else:
                    stats["normal"] += 1
                
                if tx.transaction_status == "APPROVED":
                    stats["approved"] += 1
                else:
                    stats["declined"] += 1

            # Log periodic status updates to stderr every 5 seconds
            now_time = time.time()
            if now_time - last_stats_log >= 5.0:
                elapsed_sim = ""
                if args.simulated_time:
                    elapsed_sim = f" | Simulated DateTime: {clock.get_time().strftime('%Y-%m-%d %H:%M:%S')}"
                
                logger.info(
                    f"Generated {stats['total_transactions']} txs | "
                    f"Normal: {stats['normal']} | Fraud: {stats['fraud']} (~{stats['fraud']/max(1, stats['total_transactions'])*100:.2f}%) | "
                    f"Approved: {stats['approved']} | Declined: {stats['declined']}"
                    f"{elapsed_sim}"
                )
                last_stats_log = now_time

            # Handle transaction spacing rate
            # If simulated clock is run manually we can speed it up, but we still sleep to regulate CPU utilization
            sleep_sec = config.transaction_rate_ms / 1000.0
            time.sleep(sleep_sec)

    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C). Saving stats and exiting...")
    finally:
        writer.close()
        # Log summary statistics
        logger.info("=== SIMULATION SUMMARY STATS ===")
        logger.info(f"Total Transactions: {stats['total_transactions']}")
        logger.info(f"Normal Transactions: {stats['normal']}")
        logger.info(f"Fraudulent Transactions: {stats['fraud']} ({stats['fraud']/max(1, stats['total_transactions'])*100:.2f}%)")
        logger.info(f"Approved Transactions: {stats['approved']}")
        logger.info(f"Declined Transactions: {stats['declined']}")
        logger.info("Simulator gracefully stopped.")


if __name__ == "__main__":
    main()
