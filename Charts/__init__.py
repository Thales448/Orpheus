from fastapi import FastAPI, Request
from .DatabaseConnection import DatabaseConnection
from .DataCollector import DataCollector
from .main import SyntxDB
from . import config
import logging
import sys
import os

# script_dir = os.path.dirname(os.path.abspath(__file__))
# log_file = os.path.join(script_dir, "RQCharts.log")

# logging.basicConfig(
#     filename=log_file, 
#     filemode='a',  # Append mode (change to 'w' for overwriting each run)
#     format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
#     level=logging.INFO
# )

# logger = logging.getLogger(__name__)

