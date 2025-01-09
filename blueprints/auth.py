# blueprints/auth.py

"""
Authentication Blueprint.

This module handles user authentication routes such as login, logout,
and login with token.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import service functions
from story_creator.database_handler import get_user_by_email, create_user, get_user_by_username, update_username

auth_bp = Blueprint('auth', __name__)

# Initialize serializer for generating tokens
serializer = URLSafeTimedSerializer('your_secret_key')  # Should match the app's secret key

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if not email:
            flash('Please enter your email address.')
            return redirect(url_for('auth.login'))

        # Generate a token
        token = serializer.dumps(email, salt='login')

        # Send the email with the token
        send_login_email(email, token)

        flash('A login link has been sent to your email address.')
        return redirect(url_for('main.index'))

    return render_template('login.html')

@auth_bp.route('/login/<token>')
def login_with_token(token):
    """Login with token route."""
    try:
        # The token expires after 1 hour (3600 seconds)
        email = serializer.loads(token, salt='login', max_age=3600)
    except Exception as e:
        flash('The login link is invalid or has expired.')
        return redirect(url_for('auth.login'))

    user = get_user_by_email(email)
    if not user:
        user = create_user(email)
    login_user(user)

    flash('You have been logged in.')
    return redirect(url_for('main.index'))

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route."""
    logout_user()
    session.pop('current_story_id', None)  # Clear the selected story
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

def send_login_email(email, token):
    """Send login email with the login link."""
    login_link = url_for('auth.login_with_token', token=token, _external=True)
    subject = "Your Login Link for Story Creator"
    body = f"""Hello,

Click the link below to log in to Story Creator:

{login_link}

This link will expire in 1 hour.

If you did not request this email, please ignore it.

Best regards,
Story Creator Team"""

    # Replace these with your SMTP server details or use environment variables
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.example.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("SMTP_USERNAME and SMTP_PASSWORD environment variables must be set.")
        print(f'Email: {email}')
        print(f'Link: {login_link}')
        return

    # Prepare the email
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Send the email via SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        print(f'Email Address: {email}')
        print(f'Secure Link: {login_link}')

# blueprints/auth.py

@auth_bp.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    """Allow users to change their username."""
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        errors = []

        if not new_username:
            errors.append('Please enter a new username.')
        elif get_user_by_username(new_username):
            errors.append('This username is already taken. Please choose another one.')
        else:
            # Update the username in the database
            update_username(current_user.email, new_username)
            current_user.username = new_username
            flash('Your username has been updated.')
            return redirect(url_for('main.index'))

        for error in errors:
            flash(error)
        return render_template('change_username.html', username=new_username)

    return render_template('change_username.html', username=current_user.username)
