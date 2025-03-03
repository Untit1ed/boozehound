import logging
from typing import Any, Optional, Tuple, List

import pymysql
import psycopg2


class DbHelper:
    def __init__(self, config: dict):
        """
        Initialize the DbHelper with database connection configuration.

        :param config: A dictionary containing database connection parameters.
        """
        self.config = config
        self.is_mysql = True
        self.logger = logging.getLogger(__name__)

    def connect(self) -> pymysql.connections.Connection:
        """
        Establish and return a connection to the database.

        :return: A pymysql database connection object.
        """
        if 'localhost' in self.config['host']:
            return pymysql.connect(**self.config)
        else:
            self.is_mysql = False
            return psycopg2.connect(**self.config)


    def execute_query(self, query: str, params: Optional[Tuple] = None, fetch_one: bool = False) -> Any:
        """
        Execute a SQL query and return results.

        :param query: The SQL query to execute.
        :param params: Optional parameters for the SQL query.
        :param fetch_one: If True, fetches a single record; otherwise, fetches all records.
        :return: The query result. If fetch_one is True, returns a single record; otherwise, returns a list of records.
        """
        self.logger.debug(f"Executing query: {query[:100]}...")
        connection = self.connect()
        result = None

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
                connection.commit()
        except Exception as e:
            self.logger.error(f"Database error: {str(e)}")
            raise
        finally:
            connection.close()

        return result

    def insert_query(self, query: str, params: Optional[Tuple] = None) -> Any:
        """
        Executes an SQL query that inserts data into the database and returns the ID of the last inserted row.

        :param query: SQL query string to be executed. Should be an INSERT statement.
        :param params: Optional tuple of parameters to be passed to the query. Defaults to None.
        :return: The ID of the last inserted row. Returns None if no row was inserted.
        """
        connection = self.connect()
        result = None

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.lastrowid
                connection.commit()
        finally:
            connection.close()

        return result

    def bulk_insert_query(self, query: str, params_list: List[Tuple]) -> None:
        """
        Executes a bulk insert SQL query.

        :param query: SQL query string template for the bulk insert.
        :param params_list: List of parameter tuples to be inserted.
        """
        if not params_list:
            return

        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.executemany(query, params_list)
                connection.commit()
        finally:
            connection.close()
