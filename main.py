import os
import urllib
from dotenv import load_dotenv
from src.processing import DataProcessor
import argparse
from datetime import datetime, timedelta
from src.config import WEATHER_INDICATORS_LIST

default_start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
default_end = datetime.now().strftime("%Y-%m-%d")

parser = argparse.ArgumentParser(description="Тестовая интеграция")
parser.add_argument(
    "-r",
    "--reset",
    action="store_true",
    help="Reset схемы БД с помощью scripts/init_db.sql"
)
parser.add_argument(
    "-w",
    "--weather_only",
    action="store_true",
    help="Только обновление погоды"
)
parser.add_argument(
    "-o",
    "--orders_only",
    action="store_true",
    help="Только обновление заказов из имеющихся данных погоды"
)
parser.add_argument(
    "--start_date",
    type=str,
    default=default_start,
    help=f"Дата начала (гггг-мм-дд). По умолчанию, -3 дня от текущего"
)
parser.add_argument(
    "--end_date",
    type=str,
    default=default_end,
    help=f"Дата окончания (гггг-мм-дд). По умолчанию, текущая дата"
)
args = parser.parse_args()

load_dotenv()

driver = os.getenv("DRIVER")
server = os.getenv("SERVER")
db = os.getenv("DATABASE")
user = os.getenv("UID")
pwd = os.getenv("PWD")

connection_string = urllib.parse.quote_plus(
    f"DRIVER={driver};SERVER={server};DATABASE={db};"
    f"UID={user};PWD={pwd};TrustServerCertificate=yes"
)

my_data_processor = DataProcessor(
    driver_name="mssql+pyodbc",
    connection_name="odbc_connect"
)

# Если передан флаг, перегружаем схему
if args.reset:
    my_data_processor.reset_database(connection_string)

if not args.orders_only:
    # Загружаем погоду в пандас-датафрейм
    weather_data = my_data_processor.get_daily_weather_for_cities(
        db_connection_string=connection_string,
        weather_indicators_list=WEATHER_INDICATORS_LIST,
        start_date=args.start_date,
        end_date=args.end_date
    )
    # Перекладываем сырые данные в БД
    my_data_processor.upload_raw_weather_for_cities(
        connection_string, weather_data
    )
    # Перегружаем таргет мерджом
    my_data_processor.upload_dm_weather_for_cities(connection_string)

if not args.weather_only:
    # Обновляем таблицу заказов с погодой
    my_data_processor.update_orders_n_weather(
        start_date=args.start_date,
        end_date=args.end_date,
        db_connection_string=connection_string
    )
