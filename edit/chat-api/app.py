from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import warnings
import os
import uuid

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Initialize Gemini client
api_key = "AIzaSyCn-C28AFcYj4OgQ_TTMYcdqQMbzVOvKJM"
client = genai.Client(api_key=api_key)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    chats = db.relationship('ChatMessage', backref='user', lazy=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'user' or 'ai'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# In-memory session tracking for Gemini internal state
# Since Gemini sessions are objects, we keep them in memory, 
# but we store the history in SQL for persistence across restarts.
gemini_sessions = {}

@app.route('/')
@login_required
def home():
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Hello Gemini"
    )
    return response.text

if __name__ == "__main__":
    app.run(debug=True)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.json
        message = data.get('message')
        session_id = data.get('session_id', 'default')
        selected_model = data.get('model', 'gemini-1.5-flash') # Default to a safe model

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Save user message to DB
        user_msg = ChatMessage(user_id=current_user.id, session_id=session_id, role='user', content=message)
        db.session.add(user_msg)

        # Gemini session management
        # Include model in the internal session ID to allow model-specific histories or clear session on switch
        internal_sid = f"{current_user.id}_{session_id}_{selected_model}"
        
        if internal_sid not in gemini_sessions:
            try:
                # Add a system instruction for neat formatting
                system_instruction = "Please provide responses neatly in a point-by-point manner, step by step. Use clear headings and formatting."
                gemini_sessions[internal_sid] = client.chats.create(
                    model=selected_model,
                    config={'system_instruction': system_instruction}
                )
            except Exception as e:
                # Fallback model if the selected one fails
                internal_sid = f"{current_user.id}_{session_id}_gemini-1.5-flash"
                gemini_sessions[internal_sid] = client.chats.create(model='gemini-1.5-flash')

        chat_session = gemini_sessions[internal_sid]
        
        try:
            response = chat_session.send_message(message)
        except Exception as api_error:
            if "429" in str(api_error):
                return jsonify({'error': 'AI is currently busy (Rate Limit). Please wait 30 seconds and try again.'}), 429
            raise api_error

        # Save AI response to DB
        ai_msg = ChatMessage(user_id=current_user.id, session_id=session_id, role='ai', content=response.text)
        db.session.add(ai_msg)
        db.session.commit()

        return jsonify({
            'response': response.text,
            'session_id': session_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    session_id = request.args.get('session_id', 'default')
    messages = ChatMessage.query.filter_by(user_id=current_user.id, session_id=session_id).order_by(ChatMessage.timestamp).all()
    return jsonify([{
        'role': m.role,
        'content': m.content,
        'timestamp': m.timestamp
    } for m in messages])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)