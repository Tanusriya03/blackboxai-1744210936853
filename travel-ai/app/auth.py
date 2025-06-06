from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db, mail
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer as Serializer
from config import Config
import os

auth_bp = Blueprint('auth', __name__)

def generate_token(email):
    serializer = Serializer(Config.SECRET_KEY)
    return serializer.dumps(email, salt='email-confirm')

def confirm_token(token, expiration=3600):
    serializer = Serializer(Config.SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt='email-confirm',
            max_age=expiration
        )
    except:
        return False
    return email

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', 'error')
            return redirect(url_for('auth.signup'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # Send verification email
        token = generate_token(email)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        msg = Message('Confirm Your Email', sender=os.getenv('EMAIL_USER'), recipients=[email])
        msg.body = f'Please click this link to verify your email: {confirm_url}'
        mail.send(msg)
        
        flash('A confirmation email has been sent. Please verify your email.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html')

@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'error')
        return redirect(url_for('auth.signup'))
    
    user = User.query.filter_by(email=email).first_or_404()
    if user.verified:
        flash('Account already verified. Please login.', 'info')
    else:
        user.verified = True
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.verified:
            flash('Please verify your email before logging in.', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
