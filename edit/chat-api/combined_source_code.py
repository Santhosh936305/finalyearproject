from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
import warnings
import os
import uuid

# ==========================================
# CONFIGURATION & INITIALIZATION
# ==========================================
warnings.filterwarnings('ignore', category=FutureWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app_combined.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Initialize Gemini client
api_key = "AIzaSyCn-C28AFcYj4OgQ_TTMYcdqQMbzVOvKJM"
client = genai.Client(api_key=api_key)

# ==========================================
# DATABASE MODELS
# ==========================================
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
    model_used = db.Column(db.String(50), default='gemini-2.5-flash')
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# In-memory tracking for Gemini objects
# Structure: { user_id: { model_name: chat_session } }
gemini_sessions = {}

# ==========================================
# UI TEMPLATES (HTML/CSS/JS)
# ==========================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Login - Gemini AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #6366f1; --secondary: #a855f7; --bg: #0f172a; --glass: rgba(255, 255, 255, 0.05); --border: rgba(255, 255, 255, 0.1); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }
        body { background: radial-gradient(circle at top left, #1e1b4b, #0f172a); height: 100vh; display: flex; align-items: center; justify-content: center; color: white; }
        .login-card { background: var(--glass); backdrop-filter: blur(12px); padding: 40px; border-radius: 24px; border: 1px solid var(--border); width: 100%; max-width: 400px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
        h2 { font-size: 2rem; margin-bottom: 8px; text-align: center; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p.subtitle { text-align: center; color: #94a3b8; margin-bottom: 32px; font-size: 0.9rem; }
        input { width: 100%; padding: 12px 16px; background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 12px; color: white; outline: none; margin-bottom: 20px; }
        button { width: 100%; padding: 14px; background: linear-gradient(135deg, var(--primary), var(--secondary)); border: none; border-radius: 12px; color: white; font-weight: 600; cursor: pointer; transition: 0.2s; }
        button:hover { transform: translateY(-2px); opacity: 0.9; }
        .footer { margin-top: 24px; text-align: center; font-size: 0.9rem; color: #94a3b8; }
        .footer a { color: #818cf8; text-decoration: none; font-weight: 600; }
        .alert { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 12px; border-radius: 12px; margin-bottom: 20px; font-size: 0.85rem; text-align: center; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Welcome Back</h2>
        <p class="subtitle">Enter your credentials to access Gemini AI</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}{% for message in messages %}<div class="alert">{{ message }}</div>{% endfor %}{% endif %}
        {% endwith %}
        <form action="/login" method="POST">
            <input type="text" name="username" required placeholder="Username">
            <input type="password" name="password" required placeholder="Password">
            <button type="submit">Sign In</button>
        </form>
        <div class="footer">Don't have an account? <a href="/register">Create one</a></div>
    </div>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Register - Gemini AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #6366f1; --secondary: #a855f7; --bg: #0f172a; --glass: rgba(255, 255, 255, 0.05); --border: rgba(255, 255, 255, 0.1); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }
        body { background: radial-gradient(circle at top left, #1e1b4b, #0f172a); height: 100vh; display: flex; align-items: center; justify-content: center; color: white; }
        .login-card { background: var(--glass); backdrop-filter: blur(12px); padding: 40px; border-radius: 24px; border: 1px solid var(--border); width: 100%; max-width: 400px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
        h2 { font-size: 2rem; margin-bottom: 8px; text-align: center; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p.subtitle { text-align: center; color: #94a3b8; margin-bottom: 32px; font-size: 0.9rem; }
        input { width: 100%; padding: 12px 16px; background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 12px; color: white; outline: none; margin-bottom: 20px; }
        button { width: 100%; padding: 14px; background: linear-gradient(135deg, var(--primary), var(--secondary)); border: none; border-radius: 12px; color: white; font-weight: 600; cursor: pointer; transition: 0.2s; }
        button:hover { transform: translateY(-2px); opacity: 0.9; }
        .footer { margin-top: 24px; text-align: center; font-size: 0.9rem; color: #94a3b8; }
        .footer a { color: #818cf8; text-decoration: none; font-weight: 600; }
        .alert { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 12px; border-radius: 12px; margin-bottom: 20px; font-size: 0.85rem; text-align: center; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Join Gemini</h2>
        <p class="subtitle">Create an account to start chatting</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}{% for message in messages %}<div class="alert">{{ message }}</div>{% endfor %}{% endif %}
        {% endwith %}
        <form action="/register" method="POST">
            <input type="text" name="username" required placeholder="Choose Username">
            <input type="password" name="password" required placeholder="Choose Password">
            <button type="submit">Create Account</button>
        </form>
        <div class="footer">Already have an account? <a href="/login">Sign In</a></div>
    </div>
</body>
</html>
"""

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Chat - Gemini AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --primary: #6366f1; --secondary: #a855f7; --bg: #0f172a; --glass: rgba(255, 255, 255, 0.05); --border: rgba(255, 255, 255, 0.1); --user-bubble: linear-gradient(135deg, #6366f1, #4f46e5); --ai-bubble: rgba(255, 255, 255, 0.05); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }
        body { background: #0f172a; color: white; height: 100vh; display: flex; overflow: hidden; }
        .sidebar { width: 320px; background: #020617; border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 20px; }
        .sidebar h1 { font-size: 1.5rem; margin-bottom: 25px; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .search-box { margin-bottom: 20px; position: relative; }
        .search-box i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: #64748b; }
        .search-box input { width: 100%; padding: 10px 10px 10px 35px; background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 10px; color: white; outline: none; font-size: 0.9rem; }
        
        .model-selector { margin-bottom: 20px; }
        .model-selector select { width: 100%; padding: 10px; background: #1e293b; border: 1px solid var(--border); border-radius: 10px; color: white; outline: none; }

        .user-info { padding: 15px; background: var(--glass); border-radius: 12px; margin-top: auto; display: flex; align-items: center; justify-content: space-between; }
        
        .chat-area { flex: 1; display: flex; flex-direction: column; background: radial-gradient(circle at center, #1e1b4b, #0f172a); }
        .chat-header { padding: 15px 40px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.8); }
        .chat-messages { flex: 1; padding: 30px 40px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        
        .message { max-width: 80%; padding: 14px 18px; border-radius: 18px; font-size: 0.95rem; line-height: 1.5; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .message.user { align-self: flex-end; background: var(--user-bubble); border-bottom-right-radius: 4px; }
        .message.ai { align-self: flex-start; background: var(--ai-bubble); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
        .msg-meta { font-size: 0.75rem; color: #94a3b8; margin-top: 5px; opacity: 0.7; }
        
        .input-container { padding: 25px 40px; }
        .input-wrapper { background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border); border-radius: 100px; display: flex; align-items: center; padding: 6px 6px 6px 22px; gap: 12px; }
        input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 0.95rem; }
        
        .action-btn { width: 42px; height: 42px; border-radius: 50%; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; }
        .voice-btn { background: transparent; color: #94a3b8; }
        .voice-btn.recording { color: #ef4444; animation: pulse 1.5s infinite; }
        .send-btn { background: var(--primary); color: white; }
        .send-btn:hover { background: #4f46e5; transform: scale(1.05); }
        
        .typing { font-style: italic; color: #94a3b8; font-size: 0.8rem; margin-bottom: 8px; display: none; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
    </style>
</head>
<body>
    <div class="sidebar">
        <h1>Gemini Intelligence</h1>
        
        <div class="search-box">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input type="text" id="searchInput" placeholder="Search history..." oninput="handleSearch()">
        </div>

        <div class="model-selector">
            <label style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px; display: block;">Select Model</label>
            <select id="modelSelect">
                <option value="gemini-2.5-flash">Gemini 2.5 Flash (Global)</option>
                <option value="gemini-2.0-flash">Gemini 2.0 Flash (Fast)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash (Stable)</option>
            </select>
        </div>

        <div style="color: #64748b; font-size: 0.85rem; margin-top: 20px;">
            User Session: <strong>{{ username }}</strong>
        </div>
        
        <div class="user-info">
            <span style="font-size: 0.9rem;"><i class="fa-solid fa-shield-halved"></i> Active</span>
            <a href="/logout" style="color: #fca5a5; text-decoration: none; font-size: 0.85rem; font-weight: 600;">Sign Out</a>
        </div>
    </div>

    <div class="chat-area">
        <div class="chat-header">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%;"></div>
                <span style="font-size: 0.95rem; font-weight: 600;">Neural Response Engine</span>
            </div>
            <button onclick="location.reload()" style="background:none; border:none; color:#94a3b8; cursor:pointer;" title="Refresh Chat">
                <i class="fa-solid fa-rotate-right"></i>
            </button>
        </div>

        <div class="chat-messages" id="chatContainer"></div>

        <div class="input-container">
            <div class="typing" id="typingIndicator">Analyzing request...</div>
            <div class="input-wrapper">
                <input type="text" id="userInput" placeholder="Ask Gemini something intelligent..." autocomplete="off">
                <button class="action-btn voice-btn" id="voiceBtn" title="Speak to Gemini"><i class="fa-solid fa-microphone"></i></button>
                <button class="action-btn send-btn" id="sendBtn"><i class="fa-solid fa-paper-plane"></i></button>
            </div>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        const searchInput = document.getElementById('searchInput');
        const modelSelect = document.getElementById('modelSelect');
        const sendBtn = document.getElementById('sendBtn');
        const voiceBtn = document.getElementById('voiceBtn');
        const typingIndicator = document.getElementById('typingIndicator');
        let allMessages = [];

        async function loadHistory() {
            try {
                const res = await fetch('/api/history');
                allMessages = await res.json();
                renderMessages(allMessages);
            } catch (e) { console.error("History Error", e); }
        }

        function renderMessages(messages) {
            chatContainer.innerHTML = '';
            messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `message ${msg.role}`;
                div.innerHTML = `
                    <div>${msg.content}</div>
                    <div class="msg-meta">${msg.role === 'ai' ? 'AI ('+msg.model+')' : 'You'} • ${new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                `;
                chatContainer.appendChild(div);
            });
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function handleSearch() {
            const query = searchInput.value.toLowerCase();
            const filtered = allMessages.filter(msg => msg.content.toLowerCase().includes(query));
            renderMessages(filtered);
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            const model = modelSelect.value;
            if (!message) return;

            // Fake append for instant feedback
            const tempMsg = { content: message, role: 'user', timestamp: new Date(), model: model };
            allMessages.push(tempMsg);
            renderMessages(allMessages);
            
            userInput.value = '';
            typingIndicator.style.display = 'block';

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: message, model: model })
                });
                const data = await res.json();
                typingIndicator.style.display = 'none';
                
                if (data.response) {
                    const aiMsg = { content: data.response, role: 'ai', timestamp: new Date(), model: model };
                    allMessages.push(aiMsg);
                    renderMessages(allMessages);
                } else {
                    appendSystemMessage("Error: " + (data.error || "Unknown error"));
                }
            } catch (e) {
                typingIndicator.style.display = 'none';
                appendSystemMessage("Connection failed.");
            }
        }

        function appendSystemMessage(text) {
            const div = document.createElement('div');
            div.style.textAlign = 'center';
            div.style.color = '#ef4444';
            div.style.fontSize = '0.8rem';
            div.style.margin = '10px 0';
            div.textContent = text;
            chatContainer.appendChild(div);
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            voiceBtn.onclick = () => { recognition.start(); voiceBtn.classList.add('recording'); };
            recognition.onresult = (e) => { userInput.value = e.results[0][0].transcript; sendMessage(); };
            recognition.onend = () => voiceBtn.classList.remove('recording');
        }

        sendBtn.onclick = sendMessage;
        userInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
        loadHistory();
    </script>
</body>
</html>
"""

# ==========================================
# ROUTES & LOGIC
# ==========================================

@app.route('/')
@login_required
def home():
    return render_template_string(INDEX_HTML, username=current_user.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid Username or Password')
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

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
        model_name = data.get('model', 'gemini-2.5-flash')

        if not message: return jsonify({'error': 'Message is required'}), 400

        # AI Session Handling
        uid = current_user.id
        if uid not in gemini_sessions:
            gemini_sessions[uid] = {}
        
        if model_name not in gemini_sessions[uid]:
            gemini_sessions[uid][model_name] = client.chats.create(model=model_name)
        
        try:
            chat_session = gemini_sessions[uid][model_name]
            response = chat_session.send_message(message)
        except Exception as e:
            if "429" in str(e):
                return jsonify({'error': f'Rate limit hit for {model_name}. Try another model or wait 60s.'}), 429
            return jsonify({'error': str(e)}), 500

        # Persistent Storage
        db.session.add(ChatMessage(user_id=uid, session_id='default', role='user', content=message, model_used=model_name))
        db.session.add(ChatMessage(user_id=uid, session_id='default', role='ai', content=response.text, model_used=model_name))
        db.session.commit()

        return jsonify({'response': response.text})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
@login_required
def get_history():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    return jsonify([{
        'role': m.role, 
        'content': m.content, 
        'timestamp': m.timestamp.isoformat(),
        'model': m.model_used
    } for m in messages])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Intelligence Hub running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
