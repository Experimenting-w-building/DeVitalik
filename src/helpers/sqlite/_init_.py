import sqlite3
import os

class SQLiteHelper:
    def __init__(self):
        """ Initialize the SQLiteHelper class with a database connection """
        # Get the directory of the current file
        current_dir = os.path.dirname(__file__)
        # Navigate up two levels to the Devitalik directory
        devitalik_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
        # Construct the database file path relative to the Devitalik directory
        db_path = os.path.join(devitalik_dir, "db.sqlite")
        self.conn = self._create_connection(db_path)
        self._create_table()

    def _create_connection(self, db_file):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Exception as e:
            print(e)
        return conn

    def _create_table(self):
        """ create a table for logs """
        try:
            sql_create_logs_table = """ CREATE TABLE IF NOT EXISTS logs (
                                            id integer PRIMARY KEY,
                                            timestamp text NOT NULL,
                                            level text NOT NULL,
                                            message text NOT NULL
                                        ); """
            cursor = self.conn.cursor()
            cursor.execute(sql_create_logs_table)
        except Exception as e:
            print(e)

    def insert_log(self, log_entry):
        """ Insert a new log into the logs table """
        sql = ''' INSERT INTO logs(timestamp, level, message)
                  VALUES(?,?,?) '''
        cur = self.conn.cursor()
        cur.execute(sql, log_entry)
        self.conn.commit()
        return cur.lastrowid
    
    def get_logs(self):
        results = self.conn.execute('SELECT * FROM logs')
        return results

# Example usage
# sqlite_helper = SQLiteHelper()

# # Insert a log entry
# log_entry = ('2023-04-01 10:00:00', 'INFO', 'This is a log message')
# log_id = sqlite_helper.insert_log(log_entry)