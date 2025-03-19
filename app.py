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
