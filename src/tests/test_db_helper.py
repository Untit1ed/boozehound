import unittest
from unittest.mock import patch, MagicMock, call, ANY
import os

# Assuming db_helper.py is in src directory and src is in PYTHONPATH
from src.db_helper import DbHelper, DatabaseConnectionError
# We might need to mock the database connector errors if DbHelper specifically catches them
# For now, we'll use generic Exception for pymysql.Error and psycopg2.Error
class PyMySQLError(Exception): pass
class Psycopg2Error(Exception): pass


class TestDbHelper(unittest.TestCase):

    def setUp(self):
        # Basic config, can be overridden in tests
        self.base_config = {
            'host': 'test_host',
            'user': 'test_user',
            'password': 'test_password',
            'database': 'test_db'
        }
        # Mock logger for all tests to avoid console output and allow assertions
        self.patcher_logger = patch('src.db_helper.logging.getLogger')
        self.mock_logger_instance = MagicMock()
        self.mock_getLogger = self.patcher_logger.start()
        self.mock_getLogger.return_value = self.mock_logger_instance

    def tearDown(self):
        self.patcher_logger.stop()

    @patch('src.db_helper.os.getenv')
    @patch('src.db_helper.pymysql.connect')
    def test_init_connect_mysql_success_from_config(self, mock_pymysql_connect, mock_os_getenv):
        mock_os_getenv.return_value = None # Ensure DB_TYPE is not from env
        mock_conn = MagicMock()
        mock_pymysql_connect.return_value = mock_conn
        
        config = {**self.base_config, 'DB_TYPE': 'mysql'}
        helper = DbHelper(config)

        self.assertEqual(helper.db_type, 'mysql')
        self.assertEqual(helper.connection, mock_conn)
        mock_pymysql_connect.assert_called_once_with(host='test_host', user='test_user', password='test_password', db='test_db')
        self.mock_logger_instance.info.assert_any_call("Attempting to connect to mysql database...")
        self.mock_logger_instance.info.assert_any_call("Successfully connected to mysql database.")

    @patch('src.db_helper.os.getenv')
    @patch('src.db_helper.psycopg2.connect')
    def test_init_connect_postgresql_success_from_env(self, mock_psycopg2_connect, mock_os_getenv):
        mock_os_getenv.return_value = 'postgresql' # DB_TYPE from env
        mock_conn = MagicMock()
        mock_psycopg2_connect.return_value = mock_conn

        # DbHelper's __init__ will derive db_type from env and store it in self.config
        # The _connect method for postgresql filters out 'DB_TYPE' before calling psycopg2.connect
        # and ensures 'dbname' is present.
        config_for_helper = self.base_config.copy() # Start with base config

        helper = DbHelper(config_for_helper) 

        self.assertEqual(helper.db_type, 'postgresql')
        self.assertEqual(helper.connection, mock_conn)
        
        # Expected config for psycopg2.connect call (after DbHelper processing)
        expected_call_config = {
            'host': 'test_host', 
            'user': 'test_user', 
            'password': 'test_password', 
            'dbname': 'test_db'  # 'database' key is converted to 'dbname'
        }
        mock_psycopg2_connect.assert_called_once_with(**expected_call_config)
        self.mock_logger_instance.info.assert_any_call("Attempting to connect to postgresql database...")
        self.mock_logger_instance.info.assert_any_call("Successfully connected to postgresql database.")

    @patch('src.db_helper.os.getenv')
    @patch('src.db_helper.pymysql.connect', side_effect=PyMySQLError("Connection failed"))
    def test_init_connect_mysql_failure(self, mock_pymysql_connect, mock_os_getenv):
        mock_os_getenv.return_value = None
        config = {**self.base_config, 'DB_TYPE': 'mysql'}
        with self.assertRaises(DatabaseConnectionError) as context:
            DbHelper(config)
        self.assertIn("Failed to connect to mysql database.", str(context.exception))
        self.mock_logger_instance.error.assert_any_call("Database connection error with mysql: Connection failed")

    @patch('src.db_helper.os.getenv')
    @patch('src.db_helper.psycopg2.connect', side_effect=Psycopg2Error("Connection failed"))
    def test_init_connect_postgresql_failure(self, mock_psycopg2_connect, mock_os_getenv):
        mock_os_getenv.return_value = 'postgresql'
        with self.assertRaises(DatabaseConnectionError) as context:
            DbHelper(self.base_config)
        self.assertIn("Failed to connect to postgresql database.", str(context.exception))
        self.mock_logger_instance.error.assert_any_call("Database connection error with postgresql: Connection failed")

    @patch('src.db_helper.os.getenv', return_value=None) # No DB_TYPE in env
    @patch('src.db_helper.pymysql.connect')
    def test_db_type_inference_localhost(self, mock_pymysql_connect, mock_os_getenv):
        config = {**self.base_config, 'host': 'localhost'} # DB_TYPE not in config
        DbHelper(config)
        self.mock_logger_instance.warning.assert_any_call(
            "DB_TYPE not specified in config or environment. "
            "Inferring from host: '%s'. Please set DB_TYPE explicitly.",
            'localhost'
        )

    @patch('src.db_helper.os.getenv', return_value=None)
    @patch('src.db_helper.psycopg2.connect')
    def test_db_type_inference_remote_host(self, mock_psycopg2_connect, mock_os_getenv):
        config = {**self.base_config, 'host': 'remote.example.com'}
        helper = DbHelper(config)
        self.assertEqual(helper.db_type, 'postgresql')
        self.mock_logger_instance.warning.assert_any_call(
            "DB_TYPE not specified in config or environment. "
            "Inferring from host: '%s'. Please set DB_TYPE explicitly.",
            'remote.example.com'
        )

    @patch('src.db_helper.os.getenv')
    @patch('src.db_helper.pymysql.connect')
    def test_close_connection(self, mock_pymysql_connect, mock_os_getenv):
        mock_os_getenv.return_value = 'mysql' # Make it explicit for _get_connected_helper logic
        config_with_type = {**self.base_config, 'DB_TYPE': 'mysql'}
        mock_conn = MagicMock()
        mock_pymysql_connect.return_value = mock_conn
        
        helper = DbHelper(config_with_type)
        self.assertIsNotNone(helper.connection)
        helper.close()
        
        mock_conn.close.assert_called_once()
        self.assertIsNone(helper.connection)
        self.mock_logger_instance.info.assert_any_call("Closing connection to mysql database.")

    def _get_connected_helper(self, db_type='mysql'):
        """Helper to create a DbHelper instance with a mocked connection."""
        mock_conn = MagicMock()
        test_config = {**self.base_config, 'DB_TYPE': db_type}

        if db_type == 'mysql':
            with patch('src.db_helper.pymysql.connect', return_value=mock_conn):
                with patch('src.db_helper.os.getenv', return_value=None): 
                    helper = DbHelper(test_config)
        elif db_type == 'postgresql':
            with patch('src.db_helper.psycopg2.connect', return_value=mock_conn):
                 with patch('src.db_helper.os.getenv', return_value=None):
                    helper = DbHelper(test_config)
        else:
            raise ValueError("Unsupported db_type for testing helper")
        
        helper.connection = mock_conn 
        helper.db_type = db_type 
        return helper, mock_conn


    def test_insert_query_mysql_return_id_true(self):
        helper, mock_conn = self._get_connected_helper(db_type='mysql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.lastrowid = 123 # Simulate lastrowid attribute
        query = "INSERT INTO test VALUES (%s)"
        params = ("test_val",)

        result = helper.insert_query(query, params, return_id=True)

        self.assertEqual(result, 123)
        mock_cursor.execute.assert_called_once_with(query, params)
        mock_conn.commit.assert_called_once()

    def test_insert_query_postgresql_return_id_true(self):
        helper, mock_conn = self._get_connected_helper(db_type='postgresql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.return_value = (456,)
        query = "INSERT INTO test (col) VALUES (%s)" 
        params = ("test_val",)

        result = helper.insert_query(query, params, return_id=True)
        
        self.assertEqual(result, 456)
        expected_query = f"{query.strip().rstrip(';')} RETURNING id"
        mock_cursor.execute.assert_called_once_with(expected_query, params)
        mock_cursor.fetchone.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_insert_query_postgresql_return_id_true_already_in_query(self):
        helper, mock_conn = self._get_connected_helper(db_type='postgresql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.return_value = (789,)
        query = "INSERT INTO test (col) VALUES (%s) RETURNING custom_id"
        params = ("test_val",)

        result = helper.insert_query(query, params, return_id=True)

        self.assertEqual(result, 789)
        mock_cursor.execute.assert_called_once_with(query, params) 
        mock_cursor.fetchone.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_insert_query_return_id_false(self):
        helper, mock_conn = self._get_connected_helper(db_type='mysql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        # For MySQL, if return_id is False, lastrowid should not be accessed.
        # We can check this by ensuring it's not in the mock_cursor's activity if it were a more complex mock,
        # or by simply verifying the result is None and the query executed.
        query = "INSERT INTO test VALUES (%s)"
        params = ("test_val",)

        result = helper.insert_query(query, params, return_id=False)

        self.assertIsNone(result)
        mock_cursor.execute.assert_called_once_with(query, params)
        mock_conn.commit.assert_called_once()
        # Ensure fetchone was not called (relevant for PG, but good general check)
        mock_cursor.fetchone.assert_not_called()


    def test_insert_query_no_connection(self):
        with patch('src.db_helper.pymysql.connect'), patch('src.db_helper.psycopg2.connect'), \
             patch('src.db_helper.os.getenv', return_value='mysql'): # Mock connect calls during instantiation
            helper = DbHelper(self.base_config) 
        helper.connection = None # Ensure connection is None *after* init for this test case
        
        with self.assertRaisesRegex(DatabaseConnectionError, "Database connection not established."):
            helper.insert_query("query", ("params",))

    def test_insert_query_db_error_rollback(self):
        helper, mock_conn = self._get_connected_helper(db_type='mysql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.execute.side_effect = PyMySQLError("Insert failed") 
        
        with self.assertRaises(PyMySQLError):
            helper.insert_query("INSERT", ("params",))
        
        mock_conn.rollback.assert_called_once()

    def test_execute_query_success_fetchall(self):
        helper, mock_conn = self._get_connected_helper()
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        expected_data = [("row1",), ("row2",)]
        mock_cursor.fetchall.return_value = expected_data
        query = "SELECT * FROM test"

        result = helper.execute_query(query, fetch_one=False)

        self.assertEqual(result, expected_data)
        mock_cursor.execute.assert_called_once_with(query, None)
        mock_cursor.fetchall.assert_called_once()
        mock_conn.commit.assert_not_called() 

    def test_execute_query_success_fetchone(self):
        helper, mock_conn = self._get_connected_helper()
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        expected_data = ("row1_col1",)
        mock_cursor.fetchone.return_value = expected_data
        query = "SELECT col FROM test WHERE id = %s"
        params = (1,)

        result = helper.execute_query(query, params, fetch_one=True)

        self.assertEqual(result, expected_data)
        mock_cursor.execute.assert_called_once_with(query, params)
        mock_cursor.fetchone.assert_called_once()
        mock_conn.commit.assert_not_called()

    def test_execute_query_no_connection(self):
        with patch('src.db_helper.pymysql.connect'), patch('src.db_helper.psycopg2.connect'), \
             patch('src.db_helper.os.getenv', return_value='mysql'):
            helper = DbHelper(self.base_config)
        helper.connection = None
        with self.assertRaisesRegex(DatabaseConnectionError, "Database connection not established."):
            helper.execute_query("query")
            
    def test_execute_query_db_error(self):
        helper, mock_conn = self._get_connected_helper(db_type='mysql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.execute.side_effect = PyMySQLError("Select failed")
        
        with self.assertRaises(PyMySQLError):
            helper.execute_query("SELECT", ("params",))
        mock_conn.rollback.assert_not_called() 
        mock_conn.commit.assert_not_called()

    def test_bulk_insert_query_success(self):
        helper, mock_conn = self._get_connected_helper()
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        query = "INSERT INTO test (col) VALUES (%s)"
        params_list = [("val1",), ("val2",)]

        helper.bulk_insert_query(query, params_list)

        mock_cursor.executemany.assert_called_once_with(query, params_list)
        mock_conn.commit.assert_called_once()

    def test_bulk_insert_query_empty_list(self):
        helper, mock_conn = self._get_connected_helper()
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        
        helper.bulk_insert_query("query", [])
        
        mock_cursor.executemany.assert_not_called()
        mock_conn.commit.assert_not_called()
        self.mock_logger_instance.debug.assert_any_call("Empty params_list for bulk_insert_query. Nothing to insert.")


    def test_bulk_insert_query_no_connection(self):
        with patch('src.db_helper.pymysql.connect'), patch('src.db_helper.psycopg2.connect'), \
             patch('src.db_helper.os.getenv', return_value='mysql'):
            helper = DbHelper(self.base_config)
        helper.connection = None
        with self.assertRaisesRegex(DatabaseConnectionError, "Database connection not established."):
            helper.bulk_insert_query("query", [("params",)])

    def test_bulk_insert_query_db_error_rollback(self):
        helper, mock_conn = self._get_connected_helper(db_type='mysql')
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.executemany.side_effect = PyMySQLError("Bulk insert failed")
        
        with self.assertRaises(PyMySQLError):
            helper.bulk_insert_query("INSERT", [("params",)])
        
        mock_conn.rollback.assert_called_once()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# To run these tests from the root directory of the project:
# PYTHONPATH=$PYTHONPATH:. python -m unittest src.tests.test_db_helper
# or
# python -m unittest discover -s src/tests -p "test_*.py"
