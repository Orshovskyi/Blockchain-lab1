"""
Транзакції CNUCoin: формування транзакції, обчислення TAHash, оновлення BlockChainTable, ЕЦП.
"""
import sqlite3
from datetime import datetime

from crypto_utils import hash_data, sign_data_hex
from registration import get_private_key_pem


def get_current_blockchain_state(conn: sqlite3.Connection) -> tuple[str, int]:
    """Повертає (BlockChainHash, Nonce) з єдиного рядка BlockChainTable."""
    cur = conn.cursor()
    cur.execute(
        "SELECT BlockChainHash, Nonce FROM BlockChainTable WHERE id = 1"
    )
    row = cur.fetchone()
    if not row:
        return "0", 0
    return row["BlockChainHash"] or "0", row["Nonce"] or 0


def build_transaction_hash_payload(
    cnucoin_id: str,
    tadate: str,
    from_addr: str,
    to_addr: str,
    tasum: float,
    block_chain_hash: str,
    nonce: int,
) -> str:
    """
    Конкатенує поля транзакції (крім TAApproved), замість TAHash та Nonce
    використовує BlockChainHash та Nonce з таблиці BlockChainTable.
    Повертає рядок для хешування.
    """
    parts = [
        cnucoin_id,
        tadate,
        from_addr,
        to_addr,
        str(tasum),
        block_chain_hash,
        str(nonce),
    ]
    return "|".join(parts)


def create_transaction(
    conn: sqlite3.Connection,
    from_cnucoin_id: str,
    to_cnucoin_id: str,
    amount: float,
) -> int:
    """
    Виконує першу (або чергову) транзакцію:
    - бере поточні BlockChainHash та Nonce з BlockChainTable;
    - формує запис транзакції, обчислює TAHash, підписує відправником (TAssign);
    - записує транзакцію в TransactionsTable та оновлює BlockChainTable.
    Повертає TAID створеної транзакції.
    """
    cur = conn.cursor()
    block_chain_hash, nonce = get_current_blockchain_state(conn)
    tadate = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Транзакція: відправник = CNUCoinID у таблиці транзакцій
    payload = build_transaction_hash_payload(
        cnucoin_id=from_cnucoin_id,
        tadate=tadate,
        from_addr=from_cnucoin_id,
        to_addr=to_cnucoin_id,
        tasum=amount,
        block_chain_hash=block_chain_hash,
        nonce=nonce,
    )
    payload_bytes = payload.encode("utf-8")
    ta_hash = hash_data(payload_bytes)

    # Nonce для запису в таблицю транзакцій (для майнінгу в наступній ЛР)
    # У першій транзакції використовуємо 0 або поточний з BlockChainTable
    tx_nonce = nonce

    # ЕЦП відправника над даними транзакції (над payload або над ta_hash)
    private_pem = get_private_key_pem(conn, from_cnucoin_id)
    t_assign = sign_data_hex(private_pem, payload_bytes)

    cur.execute(
        """
        INSERT INTO TransactionsTable
        (CNUCoinID, TADate, "From", "To", TASum, TAHash, Nonce, TAApproved, TAssign)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            from_cnucoin_id,
            tadate,
            from_cnucoin_id,
            to_cnucoin_id,
            amount,
            ta_hash,
            tx_nonce,
            t_assign,
        ),
    )
    taid = cur.lastrowid

    # Оновлення BlockChainTable: новий BlockChainHash та дата
    cur.execute(
        """
        UPDATE BlockChainTable
        SET BlockChainHash = ?, DateTime = ?, BlockAssign = ?
        WHERE id = 1
        """,
        (ta_hash, tadate, t_assign),
    )

    conn.commit()
    return taid


def get_transaction(conn: sqlite3.Connection, taid: int) -> dict | None:
    """Повертає запис транзакції за TAID."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TAID, CNUCoinID, TADate, "From", "To", TASum, TAHash, Nonce, TAApproved, TAssign
        FROM TransactionsTable WHERE TAID = ?
        """,
        (taid,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def list_transactions(conn: sqlite3.Connection) -> list:
    """Повертає всі транзакції."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TAID, CNUCoinID, TADate, "From", "To", TASum, TAHash, Nonce, TAApproved, TAssign
        FROM TransactionsTable ORDER BY TAID
        """
    )
    return [dict(row) for row in cur.fetchall()]


def list_pending_transactions(conn: sqlite3.Connection) -> list:
    """Повертає транзакції з TAApproved=0 (очікують підтвердження майнером)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TAID, CNUCoinID, TADate, "From", "To", TASum, TAHash, Nonce, TAApproved, TAssign
        FROM TransactionsTable WHERE TAApproved = 0 ORDER BY TAID
        """
    )
    return [dict(row) for row in cur.fetchall()]


def approve_transaction(
    conn: sqlite3.Connection, taid: int, miner_cnucoin_id: str
) -> str | None:
    """
    Підтверджує транзакцію майнером: встановлює TAApproved=1 та додає рух коштів у EWalletTable.
    Повертає None при успіху, інакше рядок з помилкою.
    """
    cur = conn.cursor()
    tx = get_transaction(conn, taid)
    if not tx:
        return "Транзакцію не знайдено."
    if tx["TAApproved"]:
        return "Транзакція вже підтверджена."
    cur.execute(
        "SELECT IsMiner FROM CnuCoinMembersTable WHERE CNUCoinID = ?",
        (miner_cnucoin_id,),
    )
    row = cur.fetchone()
    if not row or not row["IsMiner"]:
        return "Лише майнер може підтверджувати транзакції. Обраний користувач не є майнером."

    from_addr = tx["From"]
    to_addr = tx["To"]
    amount = tx["TASum"]
    tadate = tx["TADate"]

    cur.execute(
        "UPDATE TransactionsTable SET TAApproved = 1 WHERE TAID = ?", (taid,)
    )
    cur.execute(
        """
        INSERT INTO EWalletTable (CNUCoinID, TADate, "From", "To", TASum)
        VALUES (?, ?, ?, ?, ?)
        """,
        (from_addr, tadate, from_addr, to_addr, amount),
    )
    conn.commit()
    return None
