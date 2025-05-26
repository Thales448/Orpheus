from conn import DatabaseConnection
from datacollector import DataCollector
import config

db = DatabaseConnection()
data = DataCollector(db, config)


# x=data.populate_options( "spy", 20230101, 20231231, 60000)

db.insert_option_quotes()