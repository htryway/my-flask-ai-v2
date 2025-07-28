from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_cors import CORS
import openai
from flask_bcrypt import Bcrypt

# Flask setup
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

bcrypt = Bcrypt(app)

# OpenAI config (v0.28.0 syntax)
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_BASE_URL")  # Optional

# Initialize DB with WAL
def init_db():
    with sqlite3.connect('chat.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender TEXT,
            content TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        conn.commit()
        c.execute('PRAGMA journal_mode=WAL')
init_db()

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return render_template('index.html')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        input_password = request.form['password']
        with sqlite3.connect('chat.db') as conn:
            c = conn.cursor()
            c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
            user = c.fetchone()
        if user and bcrypt.check_password_hash(user[1], input_password):
            session['user_id'] = user[0]
            return redirect('/')
        return render_template('login.html', error='Invalid username or password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        raw_password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(raw_password).decode('utf-8')
        try:
            with sqlite3.connect('chat.db') as conn:
                c = conn.cursor()
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                          (username, hashed_password))
                conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username already exists.')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/ask', methods=['POST'])
def ask():
    if 'user_id' not in session:
        return jsonify({'reply': 'Please log in to chat.'}), 401

    data = request.get_json()
    user_input = data.get('message', '').strip()
    if not user_input:
        return jsonify({'reply': 'Please enter a message.'}), 400

    try:
        # Log user message
        with sqlite3.connect('chat.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO messages (user_id, sender, content) VALUES (?, ?, ?)',
                      (session['user_id'], 'user', user_input))
            conn.commit()

        # Legacy OpenAI v0.28 call
        response = openai.ChatCompletion.create(
            model="llama3-70b-8192",  # or replace with gpt-3.5-turbo
            messages=[{"role": "user", "content": user_input}]
        )
        bot_reply = response["choices"][0]["message"]["content"]

        # Log bot response
        with sqlite3.connect('chat.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO messages (user_id, sender, content) VALUES (?, ?, ?)',
                      (session['user_id'], 'bot', bot_reply))
            conn.commit()

        return jsonify({'reply': bot_reply})

    except Exception as e:
        print("⚠️ API Error:", e)
        return jsonify({'reply': 'Oops! Something went wrong.'}), 500

@app.route('/history')
def history():
    if 'user_id' not in session:
        return jsonify([])
    with sqlite3.connect('chat.db') as conn:
        c = conn.cursor()
        c.execute('SELECT sender, content FROM messages WHERE user_id = ?', (session['user_id'],))
        rows = c.fetchall()
    return jsonify([{'sender': row[0], 'content': row[1]} for row in rows])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
