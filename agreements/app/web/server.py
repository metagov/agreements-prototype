import json
from flask import Flask, redirect, render_template

flask_app = Flask(__name__)

@flask_app.route('/')
def root():
    return redirect('/home')
    
@flask_app.route('/home')
def home():
    return render_template('home.html')

@flask_app.route('/about')
def about():
    return render_template('about.html')

@flask_app.route('/help')
def help():
    return render_template('help.html')

@flask_app.route('/api/latest_agreements')
def latest_agreements():
    f = open('app/database/db.json', 'r')
    db = json.load(f)
    f.close()
    agreements = db['agreements']
    # retrieves status ids of 10 most recent agreements
    statuses = list(agreements.keys())[1:11]

    urls = []
    for s in statuses:
        a = agreements[s]
        name = a['creator_screen_name']
        url = f'https://twitter.com/{name}/status/{s}'
        urls.append(url)

    # converts list to json recognizable dictionary
    return dict(zip(range(0, 10), urls[::-1]))

# flask_app.run(host="127.0.0.1", port=80, debug=True)