from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('/home/yaniaular/mysite/hanami.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT created_at,email,id,username FROM user')
    users = cursor.fetchall()  # Obtener todos los resultados
    conn.close()
    return users

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT created_at,email,id,username FROM user WHERE id = ?', (user_id,))
    user = cursor.fetchone()  # Obtener una sola fila
    conn.close()
    return user

def get_accounts_by_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM account WHERE user_id = ?', (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def get_account_by_id(account_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM account WHERE id = ?', (account_id,))
    account = cursor.fetchone()
    conn.close()
    return account

def get_transactions_by_account(account_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE account_id = ?', (account_id,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_transactions_by_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE user_id = ?', (user_id,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_savings_by_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM saving WHERE user_id = ?', (user_id,))
    savings = cursor.fetchall()
    conn.close()
    return savings

@app.route('/')
def hello_world():
    return 'Hello from Flask to HanamiBank!'

@app.route('/api/users', methods=['GET'])
def get_users():
    users = get_all_users()
    print(users)
    return jsonify([dict(user) for user in users])

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        return jsonify(dict(user))
    else:
        return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/account/<int:account_id>', methods=['GET'])
def get_account(account_id):
    account = get_account_by_id(account_id)
    if account:
        return jsonify(dict(account))
    else:
        return jsonify({"error": "Cuenta no encontrado"}), 404

@app.route('/user-data/<int:user_id>', methods=['GET'])
def get_user_data(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    accounts = get_accounts_by_user(user_id)
    savings = get_savings_by_user(user_id)
    transactions = get_transactions_by_user(user_id)

    user_data = {
        "user": dict(user),
        "accounts": [dict(account) for account in accounts],
        "savings": [dict(saving) for saving in savings],
        "transactions": [dict(transaction) for transaction in transactions]
    }

    return jsonify(user_data)

@app.route('/api/users/<int:user_id>/accounts', methods=['GET'])
def get_all_accounts(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    accounts = get_accounts_by_user(user_id)
    user_data = {
        "accounts": [dict(account) for account in accounts],
    }
    return jsonify(user_data)

@app.route('/api/users/<int:user_id>/savings', methods=['GET'])
def get_all_savings(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    savings = get_savings_by_user(user_id)
    user_data = {
        "savings": [dict(saving) for saving in savings],
    }
    return jsonify(user_data)

@app.route('/api/accounts/<int:account_id>/transactions', methods=['GET'])
def get_all_transactions(account_id):

    transactions = get_transactions_by_account(account_id)
    user_data = {
        "transactions": [dict(transaction) for transaction in transactions],
    }
    return jsonify(user_data)

@app.route('/api/transfers', methods=['POST'])
def transfer():
    # Get request data
    data = request.get_json()

    # Validate required fields
    required_fields = ['source_account_number', 'destination_account_number', 'amount']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        source_account_number = str(data['source_account_number'])
        destination_account_number = str(data['destination_account_number'])
        amount = float(data['amount'])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid data format"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Begin transaction
        conn.execute('BEGIN TRANSACTION')

        # 1. Verify accounts exist and get their details
        cursor.execute('SELECT id, balance, user_id FROM account WHERE account_number = ?',
                      (source_account_number,))
        source_account = cursor.fetchone()
        if not source_account:
            conn.rollback()
            return jsonify({"error": "Source account not found"}), 404

        cursor.execute('SELECT id, balance, user_id FROM account WHERE account_number = ?',
                      (destination_account_number,))
        destination_account = cursor.fetchone()
        if not destination_account:
            conn.rollback()
            return jsonify({"error": "Destination account not found"}), 404

        # 2. Check sufficient funds
        if source_account['balance'] < amount:
            conn.rollback()
            return jsonify({"error": "Insufficient funds"}), 400

        # 3. Update balances
        # Deduct from source account
        new_source_balance = source_account['balance'] - amount
        cursor.execute('UPDATE account SET balance = ? WHERE account_number = ?',
                      (new_source_balance, source_account_number))

        # Add to destination account
        new_destination_balance = destination_account['balance'] + amount
        cursor.execute('UPDATE account SET balance = ? WHERE account_number = ?',
                      (new_destination_balance, destination_account_number))

        # 4. Record transactions
        cursor.execute('''
            INSERT INTO transactions
            (account_id, user_id, type, amount, description, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (
            source_account['id'],
            source_account['user_id'],
            'transfer_out',
            -amount,
            f'Transfer to account {destination_account_number}'
        ))

        cursor.execute('''
            INSERT INTO transactions
            (account_id, user_id, type, amount, description, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (
            destination_account['id'],
            destination_account['user_id'],
            'transfer_in',
            amount,
            f'Transfer from account {source_account_number}'
        ))

        # Commit transaction
        conn.commit()

        return jsonify({
            "message": "Transfer completed successfully",
            "new_source_balance": new_source_balance,
            "new_destination_balance": new_destination_balance,
            "source_account_number": source_account_number,
            "destination_account_number": destination_account_number
        })

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    finally:
        conn.close()

@app.route('/api/savings', methods=['POST'])
def create_saving():
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    amount = data.get('amount')

    if not all([user_id, name, amount]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO saving (user_id, name, amount)
            VALUES (?, ?, ?)
        ''', (user_id, name, amount))
        conn.commit()
        return jsonify({"message": "Saving created successfully"}), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/savings/transaction', methods=['POST'])
def saving_transaction():
    data = request.get_json()
    saving_id = data.get('saving_id')
    account_id = data.get('account_id')
    amount = data.get('amount')

    if not all([saving_id, account_id, amount]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')

        # 1. Get current balances
        cursor.execute('SELECT user_id, balance FROM account WHERE id = ?', (account_id,))
        account = cursor.fetchone()
        if not account:
            conn.rollback()
            return jsonify({"error": "Account not found"}), 404

        cursor.execute('SELECT amount FROM saving WHERE id = ?', (saving_id,))
        saving = cursor.fetchone()
        if not saving:
            conn.rollback()
            return jsonify({"error": "Saving not found"}), 404

        # 2. Validate withdrawal (if amount is negative)
        new_account_balance = account['balance'] - amount
        new_saving_balance = saving['amount'] + amount

        if new_account_balance < 0:
            conn.rollback()
            return jsonify({"error": "Insufficient funds in account"}), 400

        if new_saving_balance < 0:
            conn.rollback()
            return jsonify({"error": "Insufficient funds in saving"}), 400

        # 3. Update balances
        cursor.execute('UPDATE account SET balance = ? WHERE id = ?',
                      (new_account_balance, account_id))
        cursor.execute('UPDATE saving SET amount = ? WHERE id = ?',
                      (new_saving_balance, saving_id))

        # 4. Record transaction
        transaction_type = "deposit_to_saving" if amount > 0 else "withdraw_from_saving"
        cursor.execute('''
            INSERT INTO transactions
            (account_id, user_id, type, amount, description, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (
            account_id,
            account["user_id"],
            transaction_type,
            -amount,  # Negative for account, positive for saving
            f"{saving_id} {transaction_type} {abs(amount)}"
        ))

        conn.commit()
        return jsonify({
            "message": "Transaction completed",
            "new_account_balance": new_account_balance,
            "new_saving_balance": new_saving_balance
        })

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/login/', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Faltan datos de username o password"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify(dict(user))
    else:
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

def get_all_cars():
    conn = get_db()
    cursor = conn.cursor()

    # Obtener todos los autos
    cursor.execute('SELECT * FROM car')
    cars = cursor.fetchall()

    # Convertir a lista de diccionarios
    column_names = [description[0] for description in cursor.description]
    cars_dict = [dict(zip(column_names, car)) for car in cars]

    # Cerrar la conexión
    conn.close()

    return cars_dict

@app.route('/api/cars', methods=['GET'])
def get_cars():
    cars = get_all_cars()
    return jsonify(cars)

if __name__ == '__main__':
    app.run(debug=True)
