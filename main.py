"""
CNUCoin — навчальна криптовалюта.
Лабораторна робота №1: реєстрація учасників та генерування транзакцій.

Запуск: python main.py
"""
import sqlite3

from db import init_database, clear_all_tables
from registration import register_user, list_members, get_balance
from transaction import (
    create_transaction,
    get_transaction,
    list_transactions,
    list_pending_transactions,
    approve_transaction,
)

DEFAULT_INITIAL_BALANCE = 100.0


def pick_member(conn: sqlite3.Connection, prompt: str):
    """
    Виводить нумерований список користувачів, запитує номер.
    Повертає CNUCoinID обраного або None при некоректному вводі / порожньому списку.
    """
    members = list_members(conn)
    if not members:
        print("Немає жодного користувача. Спочатку створіть користувача (п. 1).")
        return None
    for i, m in enumerate(members, 1):
        addr = m["CNUCoinID"]
        miner = " [майнер]" if m["IsMiner"] else ""
        bal = get_balance(conn, addr)
        print(f"  {i}. {addr} | баланс: {bal} CNUCoin{miner}")
    try:
        raw = input(prompt).strip()
        idx = int(raw)
        if 1 <= idx <= len(members):
            return members[idx - 1]["CNUCoinID"]
    except ValueError:
        pass
    print("Невірний вибір.")
    return None


def pick_miner(conn: sqlite3.Connection, prompt: str):
    """Виводить нумерований список лише майнерів, запитує номер. Повертає CNUCoinID або None."""
    members = [m for m in list_members(conn) if m["IsMiner"]]
    if not members:
        print("Немає жодного майнера. Зареєструйте користувача з позначкою «Майнер» (п. 1).")
        return None
    for i, m in enumerate(members, 1):
        addr = m["CNUCoinID"]
        bal = get_balance(conn, addr)
        print(f"  {i}. {addr} | баланс: {bal} CNUCoin")
    try:
        raw = input(prompt).strip()
        idx = int(raw)
        if 1 <= idx <= len(members):
            return members[idx - 1]["CNUCoinID"]
    except ValueError:
        pass
    print("Невірний вибір.")
    return None


def do_register(conn: sqlite3.Connection) -> None:
    """Створити користувача: запитати майнер/баланс, викликати register_user."""
    miner_raw = input("Майнер? (y/n) [n]: ").strip().lower() or "n"
    is_miner = miner_raw in ("y", "так", "yes")
    balance_raw = input("Початковий баланс (CNUCoin) [100]: ").strip()
    try:
        initial_balance = float(balance_raw) if balance_raw else DEFAULT_INITIAL_BALANCE
    except ValueError:
        initial_balance = DEFAULT_INITIAL_BALANCE
    try:
        cnucoin_id = register_user(conn, is_miner=is_miner, initial_balance=initial_balance)
        print(f"Користувача створено. CNUCoinID (адреса): {cnucoin_id}")
    except Exception as e:
        print(f"Помилка реєстрації: {e}")


def do_list_users(conn: sqlite3.Connection) -> None:
    """Переглянути список користувачів з балансами."""
    members = list_members(conn)
    if not members:
        print("Немає жодного користувача.")
        return
    for m in members:
        addr = m["CNUCoinID"]
        miner = " [майнер]" if m["IsMiner"] else ""
        bal = get_balance(conn, addr)
        print(f"  {addr} | баланс: {bal} CNUCoin{miner}")


def do_transfer(conn: sqlite3.Connection) -> None:
    """Зробити переказ: вибір відправника/отримувача, сума, перевірка балансу, create_transaction."""
    print("Відправник:")
    from_id = pick_member(conn, "Номер відправника: ")
    if from_id is None:
        return
    print("Отримувач:")
    to_id = pick_member(conn, "Номер отримувача: ")
    if to_id is None:
        return
    if from_id == to_id:
        print("Відправник і отримувач не можуть збігатися.")
        return
    raw_amount = input("Сума (CNUCoin): ").strip()
    try:
        amount = float(raw_amount)
        if amount <= 0:
            print("Сума має бути додатньою.")
            return
    except ValueError:
        print("Невірна сума.")
        return
    balance = get_balance(conn, from_id)
    if balance < amount:
        print(f"Недостатньо коштів. Баланс: {balance} CNUCoin.")
        return
    try:
        taid = create_transaction(conn, from_cnucoin_id=from_id, to_cnucoin_id=to_id, amount=amount)
        print(f"Транзакцію створено. TAID = {taid}. Очікує підтвердження майнерами.")
    except Exception as e:
        print(f"Помилка створення транзакції: {e}")


def do_list_transactions(conn: sqlite3.Connection) -> None:
    """Переглянути список транзакцій (TAID, From, To, TASum, TAApproved, TAHash скорочено)."""
    txs = list_transactions(conn)
    if not txs:
        print("Транзакцій немає.")
        return
    for tx in txs:
        taid = tx["TAID"]
        fr = (tx["From"] or "")[:12] + "..." if len(tx["From"] or "") > 12 else (tx["From"] or "")
        to = (tx["To"] or "")[:12] + "..." if len(tx["To"] or "") > 12 else (tx["To"] or "")
        approved = "так" if tx["TAApproved"] else "ні"
        h = (tx["TAHash"] or "")[:16] + "..." if len(tx["TAHash"] or "") > 16 else (tx["TAHash"] or "")
        print(f"  TAID={taid} | {fr} -> {to} | {tx['TASum']} CNUCoin | підтв.: {approved} | hash: {h}")


def do_approve_transaction(conn: sqlite3.Connection) -> None:
    """Підтвердити транзакцію (майнер): вибір транзакції та майнера, TAApproved=1, рух коштів у EWallet."""
    pending = list_pending_transactions(conn)
    if not pending:
        print("Немає транзакцій, що очікують підтвердження.")
        return
    print("Транзакції, що очікують підтвердження:")
    for i, tx in enumerate(pending, 1):
        print(f"  {i}. TAID={tx['TAID']} | {tx['From']} -> {tx['To']} | {tx['TASum']} CNUCoin")
    raw = input("Номер транзакції або TAID: ").strip()
    try:
        taid = int(raw)
    except ValueError:
        print("Невірний ввід.")
        return
    if 1 <= taid <= len(pending):
        taid = pending[taid - 1]["TAID"]
    else:
        tx = get_transaction(conn, taid)
        if not tx or tx["TAApproved"]:
            print("Транзакцію не знайдено або вже підтверджено.")
            return
    print("Оберіть майнера для підтвердження:")
    miner_id = pick_miner(conn, "Номер майнера: ")
    if miner_id is None:
        return
    err = approve_transaction(conn, taid, miner_id)
    if err:
        print(err)
    else:
        print("Транзакцію підтверджено. Баланси оновлено.")


def do_clear_db(conn: sqlite3.Connection) -> None:
    """Очистити всі записи з усіх таблиць (з підтвердженням)."""
    confirm = input("Видалити всі записи з бази? (y/n): ").strip().lower()
    if confirm not in ("y", "так", "yes"):
        print("Скасовано.")
        return
    try:
        clear_all_tables(conn)
        print("База даних очищена. Таблиці порожні, блокчейн скинуто до початкового стану.")
    except Exception as e:
        print(f"Помилка очищення: {e}")


def do_show_transaction(conn: sqlite3.Connection) -> None:
    """Деталі транзакції за TAID."""
    raw = input("TAID транзакції: ").strip()
    try:
        taid = int(raw)
    except ValueError:
        print("Невірний TAID.")
        return
    tx = get_transaction(conn, taid)
    if not tx:
        print("Транзакцію не знайдено.")
        return
    for key, value in tx.items():
        val = str(value)
        if len(val) > 60:
            val = val[:60] + "..."
        print(f"  {key}: {val}")


def main():
    print("=== CNUCoin — підсистема реєстрації та транзакцій ===\n")
    conn = init_database()
    print("База даних готова (cnucoin.db).\n")

    while True:
        print("--- Меню ---")
        print("  1. Створити користувача")
        print("  2. Переглянути користувачів")
        print("  3. Зробити переказ")
        print("  4. Переглянути транзакції")
        print("  5. Деталі транзакції")
        print("  6. Підтвердити транзакцію (майнер)")
        print("  7. Очистити базу")
        print("  0. Вийти")
        choice = input("Оберіть дію: ").strip()

        if choice == "0":
            break
        if choice == "1":
            do_register(conn)
        elif choice == "2":
            do_list_users(conn)
        elif choice == "3":
            do_transfer(conn)
        elif choice == "4":
            do_list_transactions(conn)
        elif choice == "5":
            do_show_transaction(conn)
        elif choice == "6":
            do_approve_transaction(conn)
        elif choice == "7":
            do_clear_db(conn)
        else:
            print("Невірний вибір. Введіть 0–7.")
        print()

    conn.close()
    print("До побачення. База даних: cnucoin.db")


if __name__ == "__main__":
    main()
