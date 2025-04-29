import openai
from firebase_admin import db

# ========== Firebase Helper Functions ==========

def get_user(mobile):
    """Fetch user data from Firebase."""
    ref = db.reference(f'users/{mobile}')
    return ref.get()

def update_user(mobile, data):
    """Update user data (credits/password) in Firebase."""
    ref = db.reference(f'users/{mobile}')
    ref.update(data)

def delete_user(mobile):
    """Delete a user from Firebase."""
    ref = db.reference(f'users/{mobile}')
    ref.delete()

def add_user(name, mobile, password, credits):
    """Add a new user to Firebase."""
    ref = db.reference(f'users/{mobile}')
    ref.set({
        'name': name,
        'mobile': mobile,
        'password': password,
        'credits': credits
    })

def deduct_credit(mobile):
    """Deduct 1 credit if user has enough."""
    user = get_user(mobile)
    if user and int(user['credits']) > 0:
        new_credits = int(user['credits']) - 1
        update_user(mobile, {'credits': new_credits})
        return True
    return False

# ========== OpenAI Helper Functions ==========

def generate_post(topic, tone):
    """Generate a formatted LinkedIn post."""
    prompt = f"""
    Write a LinkedIn post (80-100 words) on the topic: '{topic}' in a {tone} tone.
    - Use proper spacing and line breaks
    - Add bullet points if necessary
    - Include relevant hashtags
    - Slightly friendly tone but professional
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def generate_comment(post_text, tone):
    """Generate a human-like LinkedIn comment."""
    prompt = f"""
    Analyze this LinkedIn post:\n\n{post_text}\n\n
    Write a natural, human-sounding comment in a {tone} tone.
    - No emoji
    - No 'As an AI' language
    - 25-60 words max
    - Sound thoughtful and genuine
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
