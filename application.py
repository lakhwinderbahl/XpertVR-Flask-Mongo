from flask import Flask, render_template, request, url_for, redirect, jsonify, session
from pymongo import MongoClient
from flask_session import Session
from bson.objectid import ObjectId
import openai
import os
import regex as re
import datetime
import time
import binascii
import openai
from langdetect import detect

current_directory = os.getcwd()

application = Flask(__name__)
# Set up the session
# Generate a random 32-byte secret key
secret_key = binascii.hexlify(os.urandom(32)).decode()
application.config['SESSION_TYPE'] = 'filesystem'  # You can choose other session types as well
application.config['SECRET_KEY'] =  secret_key # Change to a secure secret key
Session(application)

client = MongoClient('mongodb+srv://200541808:IqqPvMpTys2uLQWa@cluster1111.p6rdc1z.mongodb.net/')

# Create a 'db' collection in the 'flask_db' database
db = client.flask_db

# Create a 'user' collection in the 'flask_db' database
user_collection = db.user

# Create an 'admin' collection in the 'flask_db' database
admin_collection = db.admin

# Create an 'chat_history' collection in the 'flask_db' database
chat_history_collection = db.chat_history

# Create an 'chat_history' collection in the 'flask_db' database
cases_collection = db.cases

@application.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Handle the signup form submission
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists in the user collection
        existing_user = user_collection.find_one({'username': username})
        if existing_user:
            return render_template('home.html', error='Username already exists. Please choose a different username.')

        # Insert the new user into the user collection
        user_collection.insert_one({'username': username, 'password': password})
        session['user'] = True
        session['username'] = username
        return redirect(url_for('user_index'))

    # If the request is a GET method, render the 'signup.html' template
    return render_template('signup.html')

@application.route('/user_index')
def user_index():
    # Check if the user is logged in
    if 'user' in session and session['user']:
        return render_template('user_index.html', username=session['username'])
    else:
        return render_template('home.html')

@application.route('/index')
def index():
    # Check if the admin is logged in
    if 'admin' in session and session['admin']:
        return render_template('index.html')
    else:
        return render_template('home.html')

@application.route('/logout')
def logout():
    # Clear the session and log out the user or admin
    session.clear()
    return render_template('home.html')

@application.route('/case_menu', methods=('GET', 'POST'))
def case_menu():
    if request.method=='POST':
        case_name = request.form['case_name']
        character_names = request.form['character_names'].split(",")
        case_detail = request.form['case_detail']
        existing_case = db.cases.count_documents({'case_name': case_name})

        if(existing_case>0):
            all_cases = db.cases.find()
            return render_template('case_menu.html', errors ='Cannot have more than one case', all_cases=all_cases)

        db.cases.insert_one({'case_name': case_name, 'character_names': character_names, 'case_detail': case_detail})
        return redirect(url_for('case_menu'))

    all_cases = db.cases.find()
    return render_template('case_menu.html', cases=all_cases)


@application.get('/dropdown/')
def dropdown():
    all_cases = db.cases.find()
    charactersByCase = {}
    for case in all_cases:
        charactersByCase[case['case_name']] = case['character_names']

    return charactersByCase


@application.post('/<id>/delete/')
def delete(id):
    db.cases.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('case_menu'))


# Set up your OpenAI API credentials
openai.api_key = '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' #client Key

from langdetect import detect

def detect_language(text):
    try:
        return detect(text)
    except Exception as e:
        # Handle exception (e.g., unable to detect language)
        return None
import openai
from langdetect import detect

openai.api_key = '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'

def get_response(input_text):
    # Detect the language of the input
    language = detect_language(input_text)
    if language is None:
        return "Language not detected."

    # Create a prompt for the OpenAI API
    # Here, you can customize the prompt based on the detected language
    prompt = f"{input_text} [Please answer in {language}]"

    # Get the response from OpenAI API
    response = openai.Completion.create(
        engine="text-davinci-003",  # or another model of your choice
        prompt=prompt,
        max_tokens=100  # adjust as needed
    )

    return response.choices[0].text.strip()

global api_exec_date_time
api_exec_date_time= datetime.datetime.now()

#Text_Cleansing Function
def apply_patterns(text):
  # Define the regex patterns
    patterns = [
        r'(?<=Answer:).*',
        r'(?<=according to the context.).*',
        r'(?<=From the information provided[\.,]).*',
        r'(?<=In response to the incident[\.,]).*',
        r'(?<=Based on the information provided[\.,]).*',
        r'(?<=In answer to the question[\.,]).*',
        r'(?<=Based on the provided information[\.,]).*',
        r'(?<=Based on the[\.,]).*',
        r'(?<=In this scenario[\.,]).*',
        r'(?<=Based on the evidence presented[\.,]).*',
        r'(?<=In response to the evidence[\.,]).*',
        r'(?<=Given the evidence found in the scenario[\.,]).*',
        r'(?<=In response to the question[\.,]).*',
        r'(?<=Based on the scenario[\.,]).*',
        r'(?<=From the given scenario[\.,]).*',
        r'(?<=Based on the provided information[\.,]).*',
        r'(?<=From the given scenario[\.,]).*',
    ]
    #print('in regex')
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()

    return text.strip()


# Will only limit 1 api call to open ai per 20 seconds
# Done because we lost 1 api key already
def sleep_if_necessary():
    global api_exec_date_time
    if(api_exec_date_time):
        difference = datetime.datetime.now() - api_exec_date_time
        if(difference.seconds<20):
            wait_time = 20-difference.seconds
            print('1. waiting for ' + str(wait_time) + ' seconds' )
            time.sleep(wait_time)
    api_exec_date_time = datetime.datetime.now()
    return


#Sentiment Analysis Function
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

def analyze_sentiment(text):
    nltk.download('vader_lexicon')
    sid = SentimentIntensityAnalyzer()
    sentiment_scores = sid.polarity_scores(text)
    # Analyzing sentiment scores
    if sentiment_scores['compound'] >= 0.05:
        sentiment = 'Positive'
    elif sentiment_scores['compound'] <= -0.05:
        sentiment = 'Negative'
    else:
        sentiment = 'Neutral'

        # Identifying emotions
    if sentiment_scores['compound'] >= 0.3:
        emotion = 'Happy'
    elif sentiment_scores['compound'] <= -0.9:
        emotion = 'Angry'
    elif sentiment_scores['neu'] >= 0.6:
        emotion = 'Neutral'
    elif sentiment_scores['neg'] > sentiment_scores['pos']:
        emotion = 'Fear'

    return sentiment, emotion, sentiment_scores

@application.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Check if the user is trying to login
        username = request.form['username']
        password = request.form['password']

        # Check if the user is an admin
        admin = admin_collection.find_one({'username': username, 'password': password})
        if admin:
            session['admin'] = True
            session.pop('user', None)  # Remove 'user' key from session if it exists
            return redirect(url_for('index'))

        # Check if the user is a regular user
        user = user_collection.find_one({'username': username, 'password': password})
        if user:
            session['user'] = True
            session['username'] = user['username']
            session.pop('admin', None)  # Remove 'admin' key from session if it exists
            return redirect(url_for('user_index'))
        else:
            return render_template('home.html', error='Invalid credentials. Please try again.')

    # If the request is a GET method, render the 'home.html' template
    # If the user is already logged in, redirect to the appropriate page
    if 'admin' in session and session['admin']:
        return redirect(url_for('index'))
    elif 'user' in session and session['user']:
        return redirect(url_for('user_index'))
    else:
        return render_template('home.html')



@application.route('/conversation')
def conversation():
    character = request.args.get('character')
    case = request.args.get('case')
    return render_template('conversation.html', character=character, case=case)

@application.route('/ask', methods=['POST'])
def ask_question():
    # Get the question from the request
    question = request.json['question']
    character = request.json['character']
    case = request.json['case']
    session_id = request.json['session_id']

    # Replacing loading context from file - fetch from database instead
    current_case = db.cases.find_one({'case_name': case})
    context = current_case['case_detail']

    with open(os.path.join(current_directory, "Instruction.txt"), 'r', encoding='utf-8') as file:
        instruction = file.read()

    # Replace the placeholder in the instruction with the character name
    instruction = instruction.replace("[CHARACTER_NAME]", character)

    # Combine the question and context for the GPT-3.5 model
    input_text = f"Language: French\nQuestion: {question}\nContext: {context}\n\nInstructions: {instruction}"
    # sleep_if_necessary()

    # Use the OpenAI API to generate the answer
    response = openai.Completion.create(
        engine='text-davinci-003',  # Choose the GPT-3.5 engine
        prompt=input_text,
        max_tokens=100,  # Adjust the value based on the desired answer length
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.3
    )
    application.debug = True
    # Extract the answer from the API response
    answer = response.choices[0].text.strip()
    answer=apply_patterns(answer)
    sentiment, emotion, sentiment_scores = analyze_sentiment(answer)

    #Insert into the db
    to_store = {"question": question, "answer": answer, "emotion": emotion}
    chat_hist = chat_history_collection.find_one({"session_id": session_id})
    if(chat_hist):
        chat_hist['history'].append(to_store)
        chat_history_collection.replace_one({"session_id": session_id}, chat_hist)
    else:
        chat_history_collection.insert_one({"session_id": session_id, "case": current_case, "character": character, "history": [to_store]})
    # Return the answer as a JSON response
    return jsonify({'answer': answer,'emotion':emotion})



@application.route('/chat_history')
def chat_history():
    chat_history = chat_history_collection.find({})
    return render_template('chat_history.html', items=chat_history)

@application.route('/get_messages/<string:session_id>')
def get_messages(session_id):
    chat_history = chat_history_collection.find_one({"session_id":session_id })
    if chat_history:
        return jsonify(chat_history["history"])
    return jsonify([])

if __name__ == '__main__':
    application.run()