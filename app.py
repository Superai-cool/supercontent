from flask import Flask, render_template, request, redirect, url_for, session, flash
import openai
import firebase_admin
from firebase_admin import credentials, db
import os
from utils import get_user, update_user, delete_user, add_user, deduct_credit, generate_post, generate_comment

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key

# Initialize Firebase
cred = credentials.Certificate('firebase_config.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-firebase-project.firebaseio.com/'  # Change to your Firebase database URL
})

# Set OpenAI API Key
openai.api_key = 'your-openai-api-key'  # Replace with your OpenAI key

# ========== Routes ==========

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    mobile = request.form['mobile']
    password = request.form['password']
    user = get_user(mobile)
    if user and user['password'] == password:
        session['mobile'] = mobile
        session['name'] = user['name']
        session['credits'] = user['credits']
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid credentials. Please try again.')
        return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'mobile' not in session:
        return redirect(url_for('home'))

    post = None
    comment = None

    if request.method == 'POST':
        if 'topic' in request.form:
            topic = request.form['topic']
            tone = request.form['tone']
            if deduct_credit(session['mobile']):
                post = generate_post(topic, tone)
                session['credits'] = int(session['credits']) - 1
                update_user(session['mobile'], {'credits': session['credits']})
            else:
                flash('Insufficient credits.')
        elif 'post_input' in request.form:
            post_text = request.form['post_input']
            tone = request.form['tone']
            if deduct_credit(session['mobile']):
                comment = generate_comment(post_text, tone)
                session['credits'] = int(session['credits']) - 1
                update_user(session['mobile'], {'credits': session['credits']})
            else:
                flash('Insufficient credits.')

    return render_template('dashboard.html', name=session['name'], credits=session['credits'], post=post, comment=comment)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    if 'mobile' not in session:
        return redirect(url_for('home'))

    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    user = get_user(session['mobile'])
    if not user or user['password'] != current_password:
        flash('Current password is incorrect.')
        return redirect(url_for('dashboard'))

    if new_password != confirm_password:
        flash('New passwords do not match.')
        return redirect(url_for('dashboard'))

    update_user(session['mobile'], {'password': new_password})
    session.clear()
    flash('Password updated successfully. Please login again.')
    return redirect(url_for('home'))

@app.route('/admin')
def admin():
    if 'mobile' not in session or session['mobile'] != '8830720742':
        return redirect(url_for('home'))

    ref = db.reference('users')
    users = ref.get()

    user_list = []
    for mobile, details in users.items():
        user_list.append({
            'mobile': mobile,
            'name': details.get('name', ''),
            'credits': details.get('credits', 0)
        })

    return render_template('admin.html', users=user_list)

@app.route('/edit_credits', methods=['POST'])
def edit_credits():
    mobile = request.form['mobile']
    credits = request.form['credits']
    update_user(mobile, {'credits': credits})
    return redirect(url_for('admin'))

@app.route('/admin_update_password', methods=['POST'])
def admin_update_password():
    mobile = request.form['mobile']
    new_password = request.form['new_password']
    update_user(mobile, {'password': new_password})
    return redirect(url_for('admin'))

@app.route('/add_user', methods=['POST'])
def add_new_user():
    name = request.form['name']
    mobile = request.form['mobile']
    password = request.form['password']
    credits = request.form['credits']
    add_user(name, mobile, password, credits)
    return redirect(url_for('admin'))

@app.route('/delete_user', methods=['POST'])
def delete_user_route():
    mobile = request.form['mobile']
    delete_user(mobile)
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ========== Run App ==========

if __name__ == '__main__':
    app.run(debug=True)
