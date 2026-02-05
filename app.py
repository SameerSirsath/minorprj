"""
PWD Assistant - Single File Flask Backend
Deployable on Vercel, Netlify, and Local
"""

import os
import json
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from functools import wraps
from datetime import datetime
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_url_path='/static',
            static_folder='static',
            template_folder='templates')

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Database configuration
def get_db_config():
    """Get database configuration from environment variables"""
    # For PostgreSQL (Vercel/Netlify)
    if os.environ.get('DATABASE_URL'):
        return os.environ.get('DATABASE_URL')
    # For local development
    elif os.environ.get('DB_HOST'):
        return {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', ''),
            'database': os.environ.get('DB_NAME', 'pwd_assistant')
        }
    else:
        # Fallback to local SQLite for quick testing
        return None

# Database connection helper
def get_db_connection():
    """Create and return a database connection"""
    try:
        db_config = get_db_config()
        
        if isinstance(db_config, str):  # DATABASE_URL format
            conn = psycopg2.connect(db_config, sslmode='require')
        elif db_config:  # Dictionary config
            conn = psycopg2.connect(**db_config)
        else:
            # SQLite fallback (for local testing without PostgreSQL)
            import sqlite3
            conn = sqlite3.connect('pwd_assistant.db')
            conn.row_factory = sqlite3.Row
            return conn
            
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

# Initialize database tables
def init_database():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    if not conn:
        logger.warning("Could not connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if we're using PostgreSQL or SQLite
        is_postgres = isinstance(conn, psycopg2.extensions.connection)
        
        if is_postgres:
            # PostgreSQL tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(200) NOT NULL,
                    user_type VARCHAR(20) DEFAULT 'individual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ngo_students (
                    id SERIAL PRIMARY KEY,
                    ngo_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    age INTEGER,
                    disability_type VARCHAR(100),
                    certificate_file VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        else:
            # SQLite tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    user_type TEXT DEFAULT 'individual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ngo_students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ngo_id INTEGER,
                    name TEXT NOT NULL,
                    age INTEGER,
                    disability_type TEXT,
                    certificate_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ngo_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

# ===== MIDDLEWARE =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def ngo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'ngo':
            flash('NGO access required', 'error')
            return redirect('/home')
        return f(*args, **kwargs)
    return decorated_function

# ===== ROUTES =====
@app.route('/')
def index():
    """Main landing page"""
    return render_template('abcd.html', user=session if 'user_id' in session else None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, username))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if user:
                    # Convert to dict for easier access
                    user_dict = dict(user) if hasattr(user, '_asdict') else dict(user)
                    
                    if bcrypt.checkpw(password.encode('utf-8'), user_dict['password'].encode('utf-8')):
                        session['user_id'] = user_dict['id']
                        session['username'] = user_dict['username']
                        session['fullname'] = user_dict['full_name']
                        session['user_type'] = user_dict.get('user_type', 'individual')
                        session['email'] = user_dict['email']
                        
                        flash('Login successful!', 'success')
                        if session['user_type'] == 'ngo':
                            return redirect('/ngo/dashboard')
                        else:
                            return redirect('/home')
                
                flash('Invalid username or password', 'error')
                return redirect('/login')
                
            except Exception as e:
                logger.error(f"Login error: {e}")
                flash('An error occurred during login', 'error')
                return redirect('/login')
    
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    fullname = request.form.get('fullname')
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    user_type = request.form.get('user_type', 'individual')
    
    if not all([fullname, username, email, password]):
        flash('All fields are required', 'error')
        return redirect('/login')
    
    if len(password) < 6:
        flash('Password must be at least 6 characters', 'error')
        return redirect('/login')
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (full_name, username, email, password, user_type) VALUES (%s, %s, %s, %s, %s) RETURNING id, full_name, username, user_type, email",
                (fullname, username, email, hashed_password, user_type)
            )
            user = cursor.fetchone()
            conn.commit()
            
            if user:
                user_dict = dict(user) if hasattr(user, '_asdict') else dict(user)
                session['user_id'] = user_dict['id']
                session['fullname'] = user_dict['full_name']
                session['username'] = user_dict['username']
                session['user_type'] = user_dict['user_type']
                session['email'] = user_dict['email']
            
            cursor.close()
            conn.close()
            
            flash('Registration successful!', 'success')
            if user_type == 'ngo':
                return redirect('/ngo/dashboard')
            else:
                return redirect('/home')
                
        except Exception as e:
            logger.error(f"Signup error: {e}")
            if "duplicate" in str(e).lower():
                flash('Username or email already exists', 'error')
            else:
                flash('Registration failed. Please try again.', 'error')
            return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect('/')

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                user_dict = dict(user) if hasattr(user, '_asdict') else dict(user)
                return render_template('profile.html', user=session)
        except Exception as e:
            logger.error(f"Profile error: {e}")
    
    flash('Unable to load profile', 'error')
    return redirect('/home')

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    
    if not fullname or not email:
        flash('All fields are required', 'error')
        return redirect('/profile')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET full_name = %s, email = %s WHERE id = %s",
                (fullname, email, session['user_id'])
            )
            conn.commit()
            
            session['fullname'] = fullname
            session['email'] = email
            
            cursor.close()
            conn.close()
            flash('Profile updated successfully!', 'success')
            return redirect('/profile')
        except Exception as e:
            logger.error(f"Update profile error: {e}")
            flash('Error updating profile', 'error')
            return redirect('/profile')
    
    return redirect('/profile')

# ===== INDIVIDUAL USER ROUTES =====
@app.route('/home')
@login_required
def home():
    if session.get('user_type') == 'ngo':
        return redirect('/ngo/dashboard')
    return render_template('index.html', user=session)

@app.route('/services')
@login_required
def services():
    if session.get('user_type') == 'ngo':
        return redirect('/ngo/dashboard')
    return render_template('planner.html', user=session)

@app.route('/resources')
@login_required
def resources():
    if session.get('user_type') == 'ngo':
        return redirect('/ngo/dashboard')
    return render_template('guide.html', user=session)

@app.route('/community')
@login_required
def community():
    if session.get('user_type') == 'ngo':
        return redirect('/ngo/dashboard')
    return render_template('community.html', user=session)

@app.route('/about')
@login_required
def about():
    if session.get('user_type') == 'ngo':
        return redirect('/ngo/dashboard')
    return render_template('about.html', user=session)

# ===== NGO ROUTES =====
@app.route('/ngo/dashboard')
@ngo_required
def ngo_dashboard():
    return render_template('sample.html', user=session)

@app.route('/ngo/analyze')
@ngo_required
def ngo_analyze():
    return render_template('login_ngo.html', user=session)

# ===== API ROUTES =====
@app.route('/api/students', methods=['GET'])
@ngo_required
def get_students():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ngo_students WHERE ngo_id = %s ORDER BY created_at DESC", (session['user_id'],))
            students = cursor.fetchall()
            
            # Convert to list of dicts
            students_list = []
            for student in students:
                student_dict = dict(student) if hasattr(student, '_asdict') else dict(student)
                students_list.append(student_dict)
            
            cursor.close()
            conn.close()
            return jsonify(students_list)
        except Exception as e:
            logger.error(f"Get students error: {e}")
            return jsonify({'error': str(e)}), 500
    return jsonify([])

@app.route('/api/students', methods=['POST'])
@ngo_required
def add_student():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ngo_students (ngo_id, name, age, certificate_file) VALUES (%s, %s, %s, %s) RETURNING id",
                (session['user_id'], data.get('name'), data.get('age'), data.get('certificate_file'))
            )
            student_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'id': student_id})
    except Exception as e:
        logger.error(f"Add student error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False})

@app.route('/api/students/<int:student_id>', methods=['PUT'])
@ngo_required
def update_student(student_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ngo_students SET name = %s, age = %s, certificate_file = %s WHERE id = %s AND ngo_id = %s",
                (data.get('name'), data.get('age'), data.get('certificate_file'), student_id, session['user_id'])
            )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Update student error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False})

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
@ngo_required
def delete_student(student_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ngo_students WHERE id = %s AND ngo_id = %s", (student_id, session['user_id']))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Delete student error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False})

# ===== ERROR HANDLERS =====
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html', user=session if 'user_id' in session else None), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ===== CONTEXT PROCESSOR =====
@app.context_processor
def inject_user():
    """Inject user data into all templates"""
    user_data = {}
    if 'user_id' in session:
        user_data = {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'fullname': session.get('fullname'),
            'user_type': session.get('user_type'),
            'email': session.get('email')
        }
    return dict(user=user_data if user_data else None)

# ===== MAIN APPLICATION =====
if __name__ == '__main__':
    print("=" * 50)
    print("PWD Assistant Server Starting...")
    print("=" * 50)
    
    # Initialize database
    if init_database():
        print("✓ Database initialized successfully")
    else:
        print("⚠ Database initialization had issues (may already exist)")
    
    print("\n📱 Available routes:")
    print("  /              - Landing page")
    print("  /login         - Login page")
    print("  /logout        - Logout")
    print("  /profile       - User Profile")
    print("  /home          - Individual home")
    print("  /services      - Services hub")
    print("  /resources     - Resources")
    print("  /community     - Community")
    print("  /about         - About us")
    print("  /ngo/dashboard - NGO Dashboard")
    print("  /ngo/analyze   - NGO Analysis")
    
    print("\n⚙️  Environment:")
    print(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"  Database: {'PostgreSQL' if os.environ.get('DATABASE_URL') else 'SQLite (local)'}")
    
    print("\n🚀 Server running at: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=os.environ.get('FLASK_ENV') == 'development', port=5000)