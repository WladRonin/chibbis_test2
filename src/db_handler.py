import datetime
import logging
import pandas as pd
# import urllib
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.engine import URL


class DataBaseHandler:
    def __init__(
            self,
            driver_name: str,
            connection_name: str
    ):
        self.driver_name = driver_name
        self.connection_name = connection_name
        self._engine = None
        self._metadata = MetaData()

    def get_engine(self, connection_string):
        # Добавить проверку исключений
        if self._engine is None:
            logging.info("Создаю новый пул соединений...")
            # Не храним connection_string, connection_url в атрибутах класса
            connection_url = URL.create(
                drivername=self.driver_name,
                query={self.connection_name: connection_string}
            )
            self._engine = create_engine(connection_url, pool_pre_ping=True)
        return self._engine

    def dispose_engine(self):
        if self._engine is not None:
            logging.info("Закрываю все соединения в пуле...")
            self._engine.dispose()
            self._engine = None
        else:
            logging.warning("Отсутствует движок")
        return self._engine

    def _get_connection(self):
        # Добавить проверку, что был инициализирован движок
        return self._engine.connect()

    def init_db(self):
        file_path = 'scripts/init_db.sql'
        logging.warning("Удаляю и пересоздаю ключевые таблицы и схемы!")
        with open(file_path, 'r', encoding='utf-8') as file:
            my_sql = file.read()
        with self._engine.begin() as connection:
            connection.execute(text(my_sql))

    def get_cities(self):
        # В лучшем мире я бы сделал это через модели
        logging.info("Получаю информацию о городах из prod.dbo.cities")
        my_sql = "SELECT TOP 10 * FROM prod.dbo.cities"
        result = pd.read_sql(my_sql, con=self._engine)
        return result

    @staticmethod
    def format_dttm(input_time: datetime.datetime):
        output_time = input_time.strftime('%Y-%m-%d %H:%M:%S.%f %z')
        output_time = output_time[:-2] + ':' + output_time[-2:]
        return output_time

    def get_orders(
            self,
            start_dttm: datetime.datetime =
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=1),
            end_dttm: datetime.datetime =
            datetime.datetime.now(datetime.timezone.utc)
    ):
        my_sql = "SELECT * FROM prod.dbo.orders"
        my_sql += " WHERE AddedOn >= :start_dttm"
        my_sql += " AND AddedOn <= :end_dttm"
        my_sql_text = text(my_sql)

        my_params = {
            "start_dttm": DataBaseHandler.format_dttm(start_dttm),
            "end_dttm": DataBaseHandler.format_dttm(end_dttm)
        }

        result = pd.read_sql(
            my_sql_text,
            con=self._engine,
            params=my_params
        )
        return result

    def flush_metadata(self):
        logging.info("Полностью очищаю метаданные DataBaseHandler")
        self._metadata.clear()

    def get_table_metadata(self, table_name: str, schema_name: str):
        logging.info(f"Запрашиваю метаданные для {schema_name}.{table_name}")
        table = Table(
            table_name,
            self._metadata,
            schema=schema_name,
            autoload_with=self._engine
        )
        return table

    def remove_table_metadata(self, table_name: str, schema_name: str):
        
        name_to_remove = schema_name + "." + table_name
        table_to_remove = self._metadata.tables.get(name_to_remove)
        if table_to_remove is not None:
            self._metadata.remove(table_to_remove)

    def truncate_table(
        self,
        table_name,
        table_schema
    ):
        check_table = self.get_table_metadata(table_name, table_schema)
        if check_table is not None:
            logging.info(f"Выполняю TRUNCATE для {table_schema}.{table_name}")
            with self._engine.begin() as connection:
                my_sql = f"TRUNCATE TABLE {table_schema}.{table_name}"
                connection.execute(text(my_sql))
        else:
            logging.error("Таблицы с таким именем не существует!")
        return check_table

    def append_from_dataframe(
        self,
        target_table_name: str,
        target_table_schema: str,
        source_data_frame: pd.DataFrame
    ):
        table = self.get_table_metadata(target_table_name, target_table_schema)
        if table is not None:
            logging.info(
                f"Загружаю в {target_table_schema}.{target_table_name}"
                " данные из DataFrame"
            )
            source_data_frame.to_sql(
                target_table_name,
                schema=target_table_schema,
                con=self._engine,
                if_exists='append',
                index=False
            )
        else:
            logging.error("Таблицы с таким именем не существует!")

    def insert_from_delta(
        self,
        target_table_name: str,
        target_table_schema: str,
        delta_table_name: str,
        delta_table_schema: str
    ):
        target_table = self.get_table_metadata(
            target_table_name,
            target_table_schema
        )
        delta_table = self.get_table_metadata(
            delta_table_name,
            delta_table_schema
        )
        # Здесь неявно предполагаем, что в таргете
        # количество и последовательность атрибутов совпадает с дельтой
        # (Кроме технических)
        if target_table is not None and delta_table is not None:
            logging.info(
                f"INSERT в {target_table_schema}.{target_table_name}"
                f" из {delta_table_schema}.{delta_table_name}"
            )
            delta_non_tech_columns = [
                attr for attr in delta_table.columns.keys()
                if attr not in ("HashKey", "AddedOn")  # Ручной костыль
            ]
            target_non_tech_columns = [
                attr for attr in target_table.columns.keys()
                if attr not in ("HashKey", "AddedOn")  # Ручной костыль
            ]
            my_sql = f"INSERT INTO {target_table_schema}.{target_table_name}"
            my_sql += " (" + ", ".join(target_non_tech_columns) + ")"
            my_sql += " SELECT " + ", ".join(delta_non_tech_columns)
            my_sql += f" FROM {delta_table_schema}.{delta_table_name}"
            with self._engine.begin() as connection:
                connection.execute(text(my_sql))
        else:
            logging.error("Таблицы с таким именем не существует!")
        return None

    def merge_from_delta_by_hashkey(
        self,
        target_table_name: str,
        target_table_schema: str,
        delta_table_name: str,
        delta_table_schema: str
    ):
        target_table = self.get_table_metadata(
            target_table_name,
            target_table_schema
        )
        delta_table = self.get_table_metadata(
            delta_table_name,
            delta_table_schema
        )
        # Здесь неявно предполагаем, что в таргете
        # количество последовательность атрибутов  совпадает с дельтой
        # (Кроме технических)
        if target_table is not None and delta_table is not None:
            logging.info(
                f"MERGE в {target_table_schema}.{target_table_name}"
                f" из {delta_table_schema}.{delta_table_name}"
            )
            my_sql = f"MERGE {target_table_schema}.{target_table_name} AS t"
            my_sql += f" USING {delta_table_schema}.{delta_table_name} AS s"
            my_sql += " ON (s.HashKey = t.HashKey)"
            my_sql += " WHEN MATCHED THEN"
            my_sql += f" UPDATE SET"

            delta_non_tech_columns = [
                attr for attr in delta_table.columns.keys()
                if attr not in ("HashKey", "AddedOn")  # Ручной костыль
            ]
            target_non_tech_columns = [
                attr for attr in target_table.columns.keys()
                if attr not in ("HashKey", "AddedOn", "ChangedOn")
                # Ручной костыль
            ]

            for i, attr in enumerate(delta_non_tech_columns):
                my_sql += f" t.{target_non_tech_columns[i]}"
                my_sql += f"  = s.{attr},"
            my_sql += f" t.ChangedOn = SYSDATETIMEOFFSET()"
            my_sql += " WHEN NOT MATCHED THEN INSERT"

            target_columns_with_date = target_non_tech_columns.copy()
            target_columns_with_date.extend(["AddedOn", "ChangedOn"])

            my_sql += " (" + ", ".join(target_columns_with_date) + ")"

            delta_non_tech_columns_s = [
                "s." + x for x in delta_non_tech_columns
            ]

            my_sql += " VALUES (" + ", ".join(delta_non_tech_columns_s)
            my_sql += ", SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET());"
            with self._engine.begin() as connection:
                connection.execute(text(my_sql))
        else:
            logging.error("Таблицы с таким именем не существует!")
        return None

    def run_sql_script(
        self,
        path_to_script: str,
        params: dict
    ):
        logging.warning(
            f"Запуск кастомного скрипта {path_to_script}"
            f" с параметрами {params}"
        )
        with open(path_to_script, 'r', encoding='utf-8') as file:
            my_sql = file.read()
        with self._engine.begin() as connection:
            connection.execute(text(my_sql), params)
