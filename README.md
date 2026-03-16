# CNUCoin — Лабораторна робота №1

Навчальна криптовалюта: реєстрація учасників та генерування транзакцій.

## Запуск

```bash
pip install -r requirements.txt
python main.py
```

## Структура проєкту

- **db.py** — створення БД SQLite та п’яти таблиць (CnuCoinMembersTable, PrivateTable, EWalletTable, TransactionsTable, BlockChainTable).
- **crypto_utils.py** — RSA (ЕЦП), MD5 (хешування), обчислення CNUCoinID з публічного ключа.
- **registration.py** — реєстрація користувача (ключі, CNUCoinID, початкове нарахування в EWalletTable).
- **transaction.py** — створення транзакції: конкатенація полів, TAHash, оновлення BlockChainTable, підпис TAssign.
- **main.py** — демо: ініціалізація БД, реєстрація кількох користувачів, перша транзакція.

Після виконання створюється файл **cnucoin.db** з усіма таблицями та даними.
