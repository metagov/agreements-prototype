import json

from flask import Flask, redirect

flask_app = Flask(__name__)

def get_html(name):
    f = open(f'app/web/{name}.html', 'r')
    html = f.read()
    f.close()
    return html

@flask_app.route('/')
def root():
    return redirect('/home')
    
@flask_app.route('/home')
def home():
    return get_html('home')

@flask_app.route('/about')
def about():
    return get_html('about')

@flask_app.route('/help')
def help():
    return get_html('help')

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
    return dict(zip(range(0, 10), urls))

# flask_app.run(host="127.0.0.1", port=80, debug=True)