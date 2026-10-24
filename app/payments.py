from app.monitoring import monitor_transaction
from app.database import get_connection

SQLITE_MAX_INTEGER = 2**63 - 1


def transfer_funds(from_account_id: int, to_account_id: int, amount_pence: int):
    for name, value in (
        ("from_account_id", from_account_id),
        ("to_account_id", to_account_id),
        ("amount_pence", amount_pence),
    ):
        # bool is an int subclass; reject it and all implicit coercions.
        if type(value) is not int or not 1 <= value <= SQLITE_MAX_INTEGER:
            raise ValueError(
                f"{name} must be a positive SQLite-range integer."
            )

    if from_account_id == to_account_id:
        raise ValueError("Cannot transfer to the same account.")

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        sender = connection.execute(
            "SELECT id, currency, balance_pence FROM accounts WHERE id = ?",
            (from_account_id,)
        ).fetchone()

        receiver = connection.execute(
            "SELECT id, currency, balance_pence FROM accounts WHERE id = ?",
            (to_account_id,)
        ).fetchone()

        if sender is None or receiver is None:
            raise ValueError("Account not found.")

        if sender["currency"] != receiver["currency"]:
            raise ValueError("Cross-currency transfers are not supported.")

        for account in (sender, receiver):
            balance = account["balance_pence"]
            if type(balance) is not int or not 0 <= balance <= SQLITE_MAX_INTEGER:
                raise ValueError("Account balance must be a SQLite-range integer.")

        if receiver["balance_pence"] > SQLITE_MAX_INTEGER - amount_pence:
            raise ValueError("Recipient balance would exceed SQLite integer range.")

        if sender["balance_pence"] < amount_pence:
            raise ValueError("Insufficient funds.")

        connection.execute(
            "UPDATE accounts SET balance_pence = balance_pence - ? WHERE id = ?",
            (amount_pence, from_account_id)
        )

        connection.execute(
            "UPDATE accounts SET balance_pence = balance_pence + ? WHERE id = ?",
            (amount_pence, to_account_id)
        )

        cursor = connection.execute(
            """INSERT INTO transactions
               (from_account_id, to_account_id, amount_pence)
               VALUES (?, ?, ?)""",
            (from_account_id, to_account_id, amount_pence)
        )

        monitor_transaction(connection, cursor.lastrowid)

        connection.commit()

        return {
            "transaction_id": cursor.lastrowid,
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount_pence": amount_pence,
            "status": "completed"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
