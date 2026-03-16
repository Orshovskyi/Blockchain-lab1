"""
Реєстрація учасників CNUCoin: генерація ключів, CNUCoinID, запис у БД та початкове нарахування.
"""
import sqlite3
from datetime import datetime

from crypto_utils import (
    generate_rsa_key_pair,
    get_cnucoin_id,
    pem_to_storable,
)


# Адреса "системи" для початкового нарахування при реєстрації
GENESIS_ADDRESS = "0"


def register_user(
    conn: sqlite3.Connection,
    is_miner: bool = False,
    initial_balance: float = 100.0,
) -> str:
    """
    Реєструє нового користувача: генерує RSA-ключі, обчислює CNUCoinID,
    додає запис у CnuCoinMembersTable та PrivateTable, зараховує початкову суму в EWalletTable.
    Повертає CNUCoinID (адресу) нового користувача.
    """
    private_pem, public_pem = generate_rsa_key_pair()
    cnucoin_id = get_cnucoin_id(public_pem)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO CnuCoinMembersTable (CNUCoinID, PublicKey, IsMiner)
        VALUES (?, ?, ?)
        """,
        (cnucoin_id, pem_to_storable(public_pem), 1 if is_miner else 0),
    )
    cur.execute(
        """
        INSERT INTO PrivateTable (CNUCoinID, PrivateKey, PublicKey)
        VALUES (?, ?, ?)
        """,
        (
            cnucoin_id,
            pem_to_storable(private_pem),
            pem_to_storable(public_pem),
        ),
    )

    # Початкове нарахування на гаманець (запис у EWalletTable)
    tadate = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO EWalletTable (CNUCoinID, TADate, "From", "To", TASum)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cnucoin_id, tadate, GENESIS_ADDRESS, cnucoin_id, initial_balance),
    )

    conn.commit()
    return cnucoin_id


def list_members(conn: sqlite3.Connection) -> list:
    """Повертає список усіх зареєстрованих учасників (CNUCoinID, IsMiner) для вибору адреси."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT CNUCoinID, PublicKey, IsMiner
        FROM CnuCoinMembersTable
        ORDER BY CNUCoinID
        """
    )
    return [dict(row) for row in cur.fetchall()]


def get_private_key_pem(conn: sqlite3.Connection, cnucoin_id: str) -> bytes:
    """Повертає приватний ключ користувача в PEM (bytes) для підпису."""
    cur = conn.cursor()
    cur.execute(
        'SELECT PrivateKey FROM PrivateTable WHERE CNUCoinID = ?',
        (cnucoin_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Користувача не знайдено: {cnucoin_id}")
    return row["PrivateKey"].encode("utf-8")


def get_balance(conn: sqlite3.Connection, cnucoin_id: str) -> float:
    """Повертає поточний баланс: сума вхідних мінус сума вихідних з EWalletTable."""
    cur = conn.cursor()
    cur.execute(
        'SELECT COALESCE(SUM(TASum), 0) AS incoming FROM EWalletTable WHERE "To" = ?',
        (cnucoin_id,),
    )
    incoming = cur.fetchone()["incoming"]
    cur.execute(
        'SELECT COALESCE(SUM(TASum), 0) AS outgoing FROM EWalletTable WHERE "From" = ?',
        (cnucoin_id,),
    )
    outgoing = cur.fetchone()["outgoing"]
    return float(incoming - outgoing)
