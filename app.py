from flask import Flask, render_template, request, redirect, url_for, session, flash
import openai
import firebase_admin
from firebase_admin import credentials, db
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key

# Initialize Firebase
cred = credentials.Certificate('firebase_config.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-firebase-project.firebaseio.com/'  # change to your database URL
})

# Set your OpenAI API key
openai.api_key = 'your_openai_api_key'

# ========== Helper Functions ==========

def get_user(mobile):
    ref = db.reference(f'users/{mobile}')
    return ref.get()

def update_user(mobile, data):
    ref = db.reference(f'users/{mobile}')
    ref.update(data)

def delete_user(mobile):
    ref = db.reference(f'users/{mobile}')
    ref.delete()

def add_user(name, mobile, password, credits):
    ref = db.reference(f'users/{mobile}')
    ref.set({
        'name': name,
        'mobile': mobile,
        'password': password,
        'credits': credits
    })

def deduct_credit(mobile):
    user = get_user(mobile)
    if user and int(user['credits']) > 0:
        new_credits = int(user['credits']) - 1
        update_user(mobile, {'credits': new_credits})
        return True
    return False

def generate_post(topic, tone):
    prompt = f"Write a professional LinkedIn post of 80-100 words on the topic '{topic}' in a {tone} tone. Format properly with pointers, spaces, and relevant hashtags. Use simple and friendly language."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def generate_comment(post_text, tone):
    prompt = f"Read this LinkedIn post:\n\n{post_text}\n\nWrite a human-sounding comment (no emoji, no AI words) in {tone} tone. Limit to 25-60 words. Make it natural and thoughtful."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

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
    if 'mobile' not in session or session['mobile'] != 'your_admin_mobile_number':  # set admin mobile number
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
