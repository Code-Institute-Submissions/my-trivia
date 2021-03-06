from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_user import login_required, UserManager, UserMixin
from flask_login import current_user
import os, trivia, json

app = Flask(__name__)
app.config.from_pyfile('config.cfg')

API_URL = 'https://opentdb.com/api.php?amount=1'
API_CATEGORIES = 'https://opentdb.com/api_category.php'

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# Define minimal User data-model for basic user sign in
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    username = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')

# Create all database tables
db.create_all()

# Setup Flask-User and specify the simplified User data-model
user_manager = UserManager(app, db, User)

@app.route('/', methods=['POST','GET'])
@login_required    # User must be authenticated
def index():
    alert_message = ''
    # Check user supplied answer and save if correct or render on screen if incorrect
    if request.method == "POST":
        # Account for no answer being provided, in which case we loop until one is provided
        if 'answers' in request.form:
            trivia.save_user_answer(current_user.username,
                                    request.form["answers"])
            trivia.commit_user_data(current_user.username)
        else:
            # If no answer has been provided then, instead of re-querying the API
            # for another question, retrieve the latest question and answer from
            # a file based cache of the most recently asked question.
            with open('data/' + current_user.username + '_cache.txt', 'r') as cached_qa:
                qa_dict = json.load(cached_qa)

            cat_icon = trivia.choose_category_icon(qa_dict['category'])
            all_qa = trivia.read_user_question_answer(current_user.username)
            if all_qa == []:
                latest_qa = []
            else:
                latest_qa = all_qa[-1]

            alert_message = 'No answer provided, please try again'
            return render_template('index.html', user = current_user.username,
                                                 question_answer = qa_dict,
                                                 cat_icon = cat_icon,
                                                 latest_qa = latest_qa,
                                                 alert_message = alert_message,
                                                 page_title = "My Trivia")

    qa_dict = trivia.get_question_answer(current_user.username, API_URL)
    cat_icon = trivia.choose_category_icon(qa_dict['category'])
    all_qa = trivia.read_user_question_answer(current_user.username)

    if all_qa == []:
        latest_qa = []
    else:
        latest_qa = all_qa[-1]

    if alert_message == '' and latest_qa != []:
        if latest_qa[1] == latest_qa[4]:
            if 'answers' in request.form:
                alert_message = 'Correct!'
            else:
                alert_message = ''
        else:
            if 'answers' in request.form:
                alert_message = 'Incorrect, better luck next time...'
            else:
                alert_message = ''

    return render_template('index.html', user = current_user.username,
                                         question_answer = qa_dict,
                                         cat_icon = cat_icon,
                                         latest_qa = latest_qa,
                                         alert_message = alert_message,
                                         page_title = "My Trivia")

@app.route('/scores')
@login_required    # User must be authenticated
def scores():
    scores = trivia.calculate_user_scores(current_user.username)
    latest_five = trivia.read_user_question_answer(current_user.username)[-5:]

    return render_template('scores.html', user = current_user.username,
                                          scores = scores,
                                          latest_five = latest_five,
                                          page_title = "My Trivia - Scores")

@app.route('/leaderboard')
def leader_board():
    top_scores = trivia.leader_board(5)
    user = trivia.user_logged_in(current_user)
    return render_template('leader_board.html', user = user, top_scores = top_scores,
                                                page_title = "My Trivia - Leader Board")

@app.route('/suggestion', methods=['POST','GET'])
def suggestion():
    if request.method == "POST":
        message = "Thanks {}, we have received your suggestion".format(request.form["fullname"])
    else:
        message = ""

    user = trivia.user_logged_in(current_user)
    category_list = trivia.get_category_list(API_CATEGORIES)

    return render_template('suggestion.html', user = user,
                                              category_list = category_list,
                                              message = message,
                                              page_title = "My Trivia - Suggestion")

@app.route('/contact', methods=['POST','GET'])
def contact():
    if request.method == "POST":
        message = "Thanks {}, we have received your message".format(request.form["fullname"])
    else:
        message = ""

    user = trivia.user_logged_in(current_user)
    return render_template('contact.html', user = user,
                                           message = message,
                                           page_title = "My Trivia - Contact")

if __name__ == "__main__":
    app.run(host=os.getenv('IP'), port=os.getenv('PORT'), debug=True)
