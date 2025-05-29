from flask import render_template, redirect, url_for, flash, request, jsonify, session
from app import app
from app.forms import ChooseForm, LoginForm, RegisterForm, ReviewForm, ChangeEmailForm, ResetPasswordForm
from werkzeug.security import generate_password_hash
import os
import csv
import io
from uuid import uuid4
from flask_login import current_user, login_user, logout_user, login_required, fresh_login_required
from app import db
import sqlalchemy as sa
from app.models import User, Review, Conversation, Message
from urllib.parse import urlsplit
from app.chatbot import get_bot_response, chat_and_log
from collections import Counter
from datetime import datetime

@app.route("/")
def home():
    app.logger.debug("Debug")
    app.logger.info("Info")
    app.logger.warning("Warning")
    app.logger.error("Error")
    app.logger.critical("Critical")
    return render_template('home.html', title="Home")

@app.route("/review", methods=['GET', 'POST'])
@login_required
def review():
    choose_form = ChooseForm()
    review_form = ReviewForm()
    if current_user.is_authenticated and review_form.validate_on_submit():
        text = review_form.text.data.strip()
        text = None if text == '' else text
        feature = review_form.feature.data.strip()
        #  = None if feature == '' else feature
        review = Review(user=current_user, stars=int(review_form.stars.data), text=text, feature=feature)
        current_user.reviews.append(review)
        db.session.commit()
        return render_template('review.html', title="Home", form=review_form)
    return render_template('review.html', title="Home", form=review_form)

def get_greeting_message():
    now = datetime.now()
    current_hour = now.hour
    if current_hour < 12:
        time_greeting = "Good morning"
    elif 12 <= current_hour < 18:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"
    return f"{time_greeting}, {current_user.username}! How can I help you today?"
@app.route("/chatbot")
@login_required
def chatbot():
    initial_greeting = get_greeting_message()
    conv = Conversation(user_id=current_user.id)
    db.session.add(conv)
    db.session.commit()
    session["conversation_id"] = conv.id
    return render_template('chatbot.html', title="UoB Chatbot", initial_greeting=initial_greeting)

chatbot_queries = []

@app.route("/trend_report")
@login_required
def trend_report():
    all_reviews = Review.query.all()

    if all_reviews:
        avg_score = sum(review.stars for review in all_reviews) / len(all_reviews)
        total_ratings = len(all_reviews)
    else:
        avg_score = 0
        total_ratings = 0
    if chatbot_queries:
        query_counter = Counter(chatbot_queries)
        common_queries = [{'text': query, 'count': count}
                          for query, count in query_counter.most_common(5)]
    else:
        common_queries = []

    return render_template(
        'trend_report.html',
        title="Chatbot Trend Report",
        avg_score=avg_score,
        total_ratings=total_ratings,
        common_queries=common_queries
    )

@app.route('/get', methods=['POST'])
@login_required
def get_response():
    user_input = request.form['msg']

    global chatbot_queries
    chatbot_queries.append(user_input)

    response = chat_and_log(user_input)
    return jsonify({"reply": response})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('generic_form.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('generic_form.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/account')
@login_required
def account():
    return render_template("account.html", title="Account")

@app.route("/account/email", methods=["GET", "POST"])
@login_required
def change_email():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        current_user.email = form.new_email.data.lower()
        db.session.commit()
        flash("Your e-mail address was updated.", "success")
        return redirect(url_for("account"))
    return render_template("generic_form.html", title='Change Email', form=form)

@app.route("/account/password", methods=["GET", "POST"])
@login_required
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash("Password changed successfully. Please log in again.", "success")
        return redirect(url_for("logout"))
    return render_template("generic_form.html", title='Reset Password', form=form)

@app.route("/account/delete_history", methods=["POST"])
@login_required
def delete_history():
    convs = Conversation.query.filter_by(user_id=current_user.id).all()
    for conv in convs:
        db.session.delete(conv)
    db.session.commit()

    session.pop("conversation_id", None)

    flash("Your entire chat history has been deleted.", "info")
    return redirect(url_for("account"))

@app.route('/booking')
@login_required
def booking():
    return render_template("booking.html", title="Booking")

@app.route('/fqa')
def faq():
    return render_template("faq.html", title="FAQ")

@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html', title='Error'), 403
@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='Error'), 404
@app.errorhandler(413)
def error_413(error):
    return render_template('errors/413.html', title='Error'), 413
@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html', title='Error'), 500