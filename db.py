"""
Підсистема бази даних CNUCoin.
Створення та підключення до БД, визначення таблиць за схемою з Додатку.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cnucoin.db"


def get_connection():
    """Повертає з’єднання з SQLite БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """
    Створює всі таблиці БД CNUCoin згідно з приблизною структурою з Додатку.
    """
    cur = conn.cursor()

    # 1. Таблиця реєстрації учасників (публічна)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CnuCoinMembersTable (
            CNUCoinID TEXT PRIMARY KEY,
            PublicKey TEXT NOT NULL,
            IsMiner INTEGER NOT NULL DEFAULT 0
        )
    """)

    # 2. Таблиця для збереження ключів (приватна)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS PrivateTable (
            CNUCoinID TEXT PRIMARY KEY,
            PrivateKey TEXT NOT NULL,
            PublicKey TEXT NOT NULL,
            FOREIGN KEY (CNUCoinID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )
    """)

    # 3. Електронний гаманець (рух коштів; приватний для власника)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS EWalletTable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            CNUCoinID TEXT NOT NULL,
            TADate TEXT NOT NULL,
            "From" TEXT NOT NULL,
            "To" TEXT NOT NULL,
            TASum REAL NOT NULL,
            FOREIGN KEY (CNUCoinID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )
    """)

    # 4. Таблиця транзакцій (обов’язково поле Nonce для майнінгу)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS TransactionsTable (
            TAID INTEGER PRIMARY KEY AUTOINCREMENT,
            CNUCoinID TEXT NOT NULL,
            TADate TEXT NOT NULL,
            "From" TEXT NOT NULL,
            "To" TEXT NOT NULL,
            TASum REAL NOT NULL,
            TAHash TEXT NOT NULL,
            Nonce INTEGER NOT NULL,
            TAApproved INTEGER NOT NULL DEFAULT 0,
            TAssign TEXT NOT NULL,
            FOREIGN KEY (CNUCoinID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )
    """)

    # 5. Таблиця для збереження хеш-образу Block Chain
    # Для першої транзакції використовуємо один рядок "поточного стану" (id=1)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS BlockChainTable (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            MinerID TEXT,
            DateTime TEXT,
            BlockChainHash TEXT NOT NULL,
            Nonce INTEGER NOT NULL,
            BlockAssign TEXT
        )
    """)

    # Початковий рядок блокчейну (нульовий хеш та nonce для першої транзакції)
    cur.execute("""
        INSERT OR IGNORE INTO BlockChainTable (id, MinerID, DateTime, BlockChainHash, Nonce, BlockAssign)
        VALUES (1, NULL, NULL, '0', 0, NULL)
    """)

    conn.commit()


def clear_all_tables(conn: sqlite3.Connection) -> None:
    """
    Видаляє всі записи з усіх таблиць (у порядку, що враховує foreign key).
    Відновлює початковий рядок у BlockChainTable для подальших транзакцій.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM EWalletTable")
    cur.execute("DELETE FROM PrivateTable")
    cur.execute("DELETE FROM TransactionsTable")
    cur.execute("DELETE FROM CnuCoinMembersTable")
    cur.execute("DELETE FROM BlockChainTable")
    cur.execute("""
        INSERT INTO BlockChainTable (id, MinerID, DateTime, BlockChainHash, Nonce, BlockAssign)
        VALUES (1, NULL, NULL, '0', 0, NULL)
    """)
    conn.commit()


def init_database() -> sqlite3.Connection:
    """Ініціалізує БД: створює таблиці. Повертає з’єднання."""
    conn = get_connection()
    create_tables(conn)
    return conn
