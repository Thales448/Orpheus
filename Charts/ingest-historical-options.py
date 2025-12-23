import Charts.DataCollector as DataCollector
import Charts.DatabaseConnection as DatabaseConnection


data = DataCollector(DatabaseConnection())

data.populate_options("SPY", "2025-01-01", "2025-01-15", "1m")
