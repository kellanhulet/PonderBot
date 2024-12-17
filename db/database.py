# db/database.py
import sqlite3
from contextlib import contextmanager
from typing import Any, List, Dict

class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    address TEXT PRIMARY KEY,
                    dex_id TEXT,
                    market_cap REAL,
                    quote_token TEXT,
                    rugcheck_score INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create user_queries table to track user interactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    user_name TEXT,
                    query_type TEXT,
                    query_content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_token_info(self, token_data: Dict[str, Any]):
        """Save token information to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tokens 
                (address, dex_id, market_cap, quote_token, rugcheck_score, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                token_data.get('address'),
                token_data.get('dexId'),
                token_data.get('marketCap', 0),
                token_data.get('quoteToken', {}).get('name'),
                token_data.get('rugcheck_score', 0)
            ))
            conn.commit()
    
    def log_user_query(self, user_id: str, user_name: str, query_type: str, query_content: str):
        """Log user queries for analytics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_queries (user_id, user_name, query_type, query_content)
                VALUES (?, ?, ?, ?)
            """, (user_id, user_name, query_type, query_content))
            conn.commit()
    
    def get_token_info(self, address: str) -> Dict[str, Any]:
        """Retrieve token information from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tokens WHERE address = ?", (address,))
            row = cursor.fetchone()
            if row:
                return {
                    'address': row[0],
                    'dexId': row[1],
                    'marketCap': row[2],
                    'quoteToken': row[3],
                    'rugcheck_score': row[4],
                    'last_updated': row[5]
                }
            return None