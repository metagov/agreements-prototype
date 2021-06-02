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
    with open('app/database/db.json', 'r') as f:
        db = json.load(f)
    with open('app/web/blocklist.json', 'r') as f:
        blocklist = json.load(f)
    agreements = db['agreements']
    blocked_users = blocklist['blocked_users']
    
    # retrieves status urls of 10 most recent agreements
    urls = []
    count = 0
    for s in agreements.keys():
        if count > 10:
            break

        a = agreements[s]
        name = a['creator_screen_name']

        # adds users to list of urls displayed on home page if they aren't on the block list
        if name not in blocked_users:
            url = f'https://twitter.com/{name}/status/{s}'
            urls.append(url)

        count += 1

    # converts list to json recognizable dictionary
    return dict(zip(range(0, 10), urls[::-1]))

# flask_app.run(host="127.0.0.1", port=80, debug=True)