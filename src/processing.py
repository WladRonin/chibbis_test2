# import datetime
import logging
import pandas as pd
import urllib
# from sqlalchemy import create_engine, text, Table, MetaData
# from sqlalchemy.engine import URL
from src.config import WEATHER_DICT

from src.db_handler import DataBaseHandler
from src.api_client import ServiceClient


class DataProcessor:
    def __init__(
        self,
        driver_name: str,
        connection_name: str
    ):
        self.db_handler = DataBaseHandler(
            driver_name=driver_name,
            connection_name=connection_name
        )
        self.service_client = None

    def reset_database(
        self,
        db_connection_string
    ):
        self.db_handler.get_engine(db_connection_string)
        self.db_handler.init_db()
        self.db_handler.dispose_engine()

    def get_cities(self, db_connection_string: str):
        self.db_handler.get_engine(db_connection_string)
        df_cities = self.db_handler.get_cities()
        self.db_handler.dispose_engine()
        return df_cities

    def get_daily_weather_for_cities(
        self,
        db_connection_string: str,
        weather_indicators_list: list,
        start_date: str,
        end_date: str,
    ):
        # Забираем города, и сразу закрываем соединение
        self.db_handler.get_engine(db_connection_string)
        df_cities = self.db_handler.get_cities()
        self.db_handler.dispose_engine()

        # Забираем данные чанками по 10 штук, чтобы не перегружать URL
        city_chunk = 10
        weather_data = pd.DataFrame()
        for i in range(0, len(df_cities), city_chunk):
            cities_chunk = df_cities.iloc[i:i + city_chunk]
            logging.info(
                f"Загружаю города {i}-{i+city_chunk}"
                f"\n {df_cities.iloc[i:i + city_chunk]['Name'].to_list()}"
            )
            # Здесь костыль, широта и долгота поменяны местами
            api_params = {
                "latitude": df_cities["Lng"][i:i + city_chunk].tolist(),
                "longitude": df_cities["Lat"][i:i + city_chunk].tolist(),
                "start_date": start_date,
                "end_date": end_date,
                "hourly": ",".join(weather_indicators_list)
            }
            with ServiceClient() as sc:
                weather_data_chunk = sc.get_weather_archive(api_params)
            if weather_data_chunk is not None:
                # Здесь дописываю логику (!)
                chunk_data = [row["hourly"] for row in weather_data_chunk]
                for row_data, raw_meta in zip(chunk_data, weather_data_chunk):
                    row_data.update({
                        "latitude": raw_meta["latitude"],
                        "longitude": raw_meta["longitude"]
                    })
                chunk_df = pd.json_normalize(chunk_data, sep="_")
                # result_df = pd.concat([cities_chunk["Id"], chunk_df], axis=1)
                chunk_df["CityId"] = cities_chunk["Id"].values
                weather_data = pd.concat(
                    [weather_data, chunk_df], ignore_index=True
                )
            else:
                logging.warning("Пустой дата-чанк")

        # Немного причесываем
        explode_list = weather_indicators_list.copy()
        explode_list.append("WeatherTime")
        # weather_data = weather_data.rename(columns={"Id": "CityId"})
        weather_data = weather_data.rename(columns={"time": "WeatherTime"})
        weather_data = weather_data.explode(explode_list)
        weather_data["weather_code"] = weather_data["weather_code"].apply(
            lambda x: WEATHER_DICT.get(x, "No Data")
        )
        weather_data["WeatherTime"] = pd.to_datetime(
            weather_data["WeatherTime"],
            format="%Y-%m-%dT%H:%M"
        )
        return weather_data

    def upload_raw_weather_for_cities(
        self,
        db_connection_string: str,
        weather_data: pd.DataFrame
    ):
        self.db_handler.get_engine(db_connection_string)
        self.db_handler.truncate_table("weather_series", "raw")
        self.db_handler.append_from_dataframe(
            "weather_series",
            "raw",
            weather_data
        )
        self.db_handler.dispose_engine()
        return None

    def upload_dm_weather_for_cities(
        self,
        db_connection_string: str
    ):
        self.db_handler.get_engine(db_connection_string)
        self.db_handler.truncate_table("weather_series", "stg")
        self.db_handler.insert_from_delta(
            target_table_name="weather_series",
            target_table_schema="stg",
            delta_table_name="weather_series",
            delta_table_schema="raw"
        )
        self.db_handler.merge_from_delta_by_hashkey(
            target_table_name="weather_series",
            target_table_schema="dm",
            delta_table_name="weather_series",
            delta_table_schema="stg"
        )
        self.db_handler.dispose_engine()
        return None

    def update_orders_n_weather(
        self,
        start_date: str,  # Уже не хочется заморачиваться
        end_date: str,  # Здесь должен быть формат YYYY-MM-DD
        db_connection_string: str
    ):
        params_dict = {"start_date": start_date, "end_date": end_date}
        self.db_handler.get_engine(db_connection_string)
        self.db_handler.truncate_table("orders_n_weather", "stg")
        self.db_handler.run_sql_script(
            "scripts/orders_n_weather_delta.sql",
            params_dict
        )
        self.db_handler.merge_from_delta_by_hashkey(
            target_table_name="orders_n_weather",
            target_table_schema="dm",
            delta_table_name="orders_n_weather",
            delta_table_schema="stg"
        )
        self.db_handler.dispose_engine()
        return None
