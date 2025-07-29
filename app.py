import os
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
import openai

# Load .env vars
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
bcrypt = Bcrypt(app)

openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_BASE_URL")

# Initialize DB
def init_db():
    with sqlite3.connect('chat.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sender TEXT,
                content TEXT,
                english_level TEXT DEFAULT 'Intermediate',
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        c.execute('PRAGMA journal_mode=WAL')
        conn.commit()

init_db()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html')

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
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
                conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username already exists.')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/ask', methods=['POST'])
def ask():
    if 'user_id' not in session:
        return jsonify({'reply': 'You must be logged in.'}), 401

    data = request.get_json()
    user_input = data.get('message', '').strip()
    level = data.get('english_level', 'Intermediate')

    if not user_input:
        return jsonify({'reply': 'Please enter a message.'}), 400

    try:
        # Store user input
        with sqlite3.connect('chat.db') as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO messages (user_id, sender, content, english_level) VALUES (?, ?, ?, ?)',
                (session['user_id'], 'user', user_input, level)
            )
            conn.commit()

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="llama3-70b-8192",  # Or gpt-3.5-turbo
            messages=[
                {"role": "system", "content": f"The user is an {level} English speaker. Respond clearly and appropriately."},
                {"role": "user", "content": user_input}
            ]
        )
        bot_reply = response["choices"][0]["message"]["content"]

        # Store bot reply
        with sqlite3.connect('chat.db') as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO messages (user_id, sender, content, english_level) VALUES (?, ?, ?, ?)',
                (session['user_id'], 'bot', bot_reply, level)
            )
            conn.commit()

        return jsonify({'reply': bot_reply})

    except Exception as e:
        print(f"❌ Error in /ask: {e}")
        return jsonify({'reply': 'Something went wrong while processing your request.'}), 500

@app.route('/history')
def history():
    if 'user_id' not in session:
        return jsonify([])

    with sqlite3.connect('chat.db') as conn:
        c = conn.cursor()
        c.execute('SELECT sender, content, english_level FROM messages WHERE user_id = ?', (session['user_id'],))
        rows = c.fetchall()

    # Return english_level with each message for frontend display
    return jsonify([{'sender': row[0], 'content': row[1], 'english_level': row[2]} for row in rows])

# *** DEV ONLY: Clear DB (users and messages) for testing fresh password hashes ***
@app.route('/reset_db')
def reset_db():
    with sqlite3.connect('chat.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users')
        c.execute('DELETE FROM messages')
        conn.commit()
    return "Database reset done. All users and messages deleted."

if __name__ == '__main__':
    app.run(debug=True, port=10000)
