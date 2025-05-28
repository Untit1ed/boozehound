import logging
import os
from typing import Any, List, Optional, Tuple

import psycopg2
import pymysql


class DatabaseConnectionError(Exception):
    pass


class DbHelper:
    def __init__(self, config: dict):
        """
        Initialize the DbHelper with database connection configuration.
        Establishes and stores the database connection.

        :param config: A dictionary containing database connection parameters.
                       Can include 'DB_TYPE' ('mysql' or 'postgresql').
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.connection = None

        # Determine DB_TYPE
        db_type = self.config.get('DB_TYPE')
        if db_type is None:
            db_type = os.getenv('DB_TYPE')
        
        if db_type is None:
            self.logger.warning(
                "DB_TYPE not specified in config or environment. "
                "Inferring from host: '%s'. Please set DB_TYPE explicitly.", 
                self.config.get('host')
            )
            # Infer based on old logic for backward compatibility
            if 'localhost' in self.config.get('host', ''):
                db_type = 'mysql'
            elif self.config.get('host'): # If host is defined but not localhost, assume postgresql
                db_type = 'postgresql'
            else: # Default to mysql if host is also not set (e.g. for testing with sqlite later)
                self.logger.warning("Host not specified, defaulting inferred DB_TYPE to 'mysql'.")
                db_type = 'mysql'
        
        self.db_type = db_type.lower()
        self.config['DB_TYPE'] = self.db_type # Ensure config has it

        self._connect()

    def _connect(self) -> None:
        """
        Establish a connection to the database based on self.db_type.
        Sets self.connection.
        Raises DatabaseConnectionError on failure.
        """
        if self.connection:
            self.logger.debug("Connection already established.")
            return

        self.logger.info(f"Attempting to connect to {self.db_type} database...")
        try:
            if self.db_type == 'mysql':
                # PyMySQL doesn't like 'dbname' or 'DB_TYPE' in the config for connect
                mysql_config = {k: v for k, v in self.config.items() if k not in ['dbname', 'DB_TYPE', 'database']}
                mysql_config['db'] = self.config.get('database') or self.config.get('dbname')
                if not mysql_config.get('db'):
                    raise ValueError("Database name not configured for MySQL.")
                self.connection = pymysql.connect(**mysql_config)
            elif self.db_type == 'postgresql':
                # Psycopg2 uses 'dbname'
                pg_config = {k: v for k, v in self.config.items() if k != 'DB_TYPE'}
                if 'database' in pg_config and 'dbname' not in pg_config: # common key is 'database'
                    pg_config['dbname'] = pg_config.pop('database')
                if not pg_config.get('dbname'):
                    raise ValueError("Database name not configured for PostgreSQL.")
                self.connection = psycopg2.connect(**pg_config)
            else:
                self.logger.error(f"Unsupported DB_TYPE: {self.db_type}")
                raise DatabaseConnectionError(f"Unsupported DB_TYPE: {self.db_type}")
            self.logger.info(f"Successfully connected to {self.db_type} database.")
        except ValueError as ve: # Specific check for missing db name
            self.logger.error(f"Configuration error for {self.db_type}: {ve}")
            self.connection = None
            raise DatabaseConnectionError(f"Configuration error for {self.db_type}: {ve}")
        except Exception as e:
            self.logger.error(f"Database connection error with {self.db_type}: {e}")
            self.connection = None # Ensure connection is None on failure
            raise DatabaseConnectionError(f"Failed to connect to {self.db_type} database. Original error: {e}")

    def close(self) -> None:
        """
        Close the database connection if it is open.
        """
        if self.connection:
            self.logger.info(f"Closing connection to {self.db_type} database.")
            try:
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing database connection: {e}")
            finally:
                self.connection = None
        else:
            self.logger.debug("No active database connection to close.")

    def execute_query(self, query: str, params: Optional[Tuple] = None, fetch_one: bool = False) -> Any:
        """
        Execute a SQL query and return results.

        :param query: The SQL query to execute.
        :param params: Optional parameters for the SQL query.
        :param fetch_one: If True, fetches a single record; otherwise, fetches all records.
        :return: The query result. If fetch_one is True, returns a single record; otherwise, returns a list of records.
        """
        if self.connection is None:
            self.logger.error("Database connection not established.")
            raise DatabaseConnectionError("Database connection not established.")

        self.logger.debug(f"Executing query: {query[:100]}...")
        result = None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
                # No commit here for select queries
        except Exception as e:
            self.logger.error(f"Database error during execute_query: {str(e)}")
            raise # Re-raise the exception after logging

        return result

    def insert_query(self, query: str, params: Optional[Tuple] = None, return_id: bool = True) -> Any:
        """
        Executes an SQL query that inserts data into the database.
        If return_id is True, it attempts to return the ID of the last inserted row.

        :param query: SQL query string to be executed. Should be an INSERT statement.
        :param params: Optional tuple of parameters to be passed to the query. Defaults to None.
        :param return_id: Boolean indicating whether to return the last inserted ID.
        :return: The ID of the last inserted row if return_id is True and successful, otherwise None.
        """
        if self.connection is None:
            self.logger.error("Database connection not established.")
            raise DatabaseConnectionError("Database connection not established.")

        self.logger.debug(f"Executing insert query: {query[:100]} (return_id: {return_id})")
        inserted_id = None
        
        original_query = query # Keep original for logging or non-returning execution
        
        try:
            with self.connection.cursor() as cursor:
                if return_id:
                    if self.db_type == 'postgresql':
                        # Ensure RETURNING id is part of the query for PostgreSQL
                        if "RETURNING" not in query.upper():
                            query = f"{query.strip().rstrip(';')} RETURNING id"
                        self.logger.debug(f"Modified PostgreSQL query for returning ID: {query[:150]}")
                        cursor.execute(query, params)
                        row = cursor.fetchone()
                        if row:
                            inserted_id = row[0]
                    elif self.db_type == 'mysql':
                        cursor.execute(query, params)
                        inserted_id = cursor.lastrowid
                    else:
                        # For other DB types, execute without specific ID retrieval logic if return_id is True
                        # and log a warning. User might have crafted query to return ID.
                        self.logger.warning(
                            f"ID retrieval with return_id=True is specifically implemented for "
                            f"MySQL (lastrowid) and PostgreSQL (RETURNING id). "
                            f"For DB_TYPE '{self.db_type}', query executed as is."
                        )
                        cursor.execute(query, params)
                        # Try to fetch if the query itself was modified to return something
                        try:
                            row = cursor.fetchone()
                            if row:
                                inserted_id = row[0]
                                self.logger.info(f"Query for '{self.db_type}' returned an ID: {inserted_id}")
                        except Exception as e:
                            self.logger.debug(f"No ID returned by query for '{self.db_type}' or error fetching: {e}")
                else: # return_id is False
                    cursor.execute(original_query, params)
                
                self.connection.commit()
        except Exception as e:
            self.logger.error(f"Database error during insert_query (query: {original_query[:150]}): {e}")
            if self.connection: # Check if connection is still valid before rollback
                try:
                    self.connection.rollback()
                except Exception as re:
                    self.logger.error(f"Error during rollback: {re}")
            raise

        return inserted_id

    def bulk_insert_query(self, query: str, params_list: List[Tuple]) -> None:
        """
        Executes a bulk insert SQL query.

        :param query: SQL query string template for the bulk insert.
        :param params_list: List of parameter tuples to be inserted.
        """
        if self.connection is None:
            self.logger.error("Database connection not established.")
            raise DatabaseConnectionError("Database connection not established.")

        if not params_list:
            self.logger.debug("Empty params_list for bulk_insert_query. Nothing to insert.")
            return

        self.logger.debug(f"Executing bulk insert query: {query[:100]} with {len(params_list)} rows.")
        try:
            with self.connection.cursor() as cursor:
                cursor.executemany(query, params_list)
                self.connection.commit()
        except Exception as e:
            self.logger.error(f"Database error during bulk_insert_query: {str(e)}")
            self.connection.rollback() # Rollback on error
            raise
