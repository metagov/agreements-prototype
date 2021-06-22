import json
from flask import Flask, redirect, render_template

flask_app = Flask(__name__)

def get_db():
    f = open('app/database/db.json', 'r')
    db = json.load(f)
    f.close()
    return db

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

@flask_app.route('/api/user/<id>')
def get_user(id):
    users = get_db()['accounts']
    if id in users:
        return users[id]
    else:
        return {'error': 'user not found'}

@flask_app.route('/api/contract/<id>')
def get_contract(id):
    contracts = get_db()['contracts']
    if id in contracts:
        return contracts[id]
    else:
        return {'error': 'contract not found'}

@flask_app.route('/api/agreement/<id>')
def get_agreement(id):
    agreements = get_db()['agreements']
    if id in agreements:
        return agreements[id]
    else:
        return {'error': 'agreement not found'}

@flask_app.route('/api/execution/<id>')
def get_execution(id):
    executions = get_db()['executions']
    if id in executions:
        return executions[id]
    else:
        return {'error': 'execution not found'}

@flask_app.route('/api/metadata')
def get_metadata():
    return get_db()['metadata']


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
    for s in list(agreements.keys())[1:]:
        if count > 10:
            break

        a = agreements[s]
        name = a['creator_screen_name']

        # adds users to list of urls displayed on home page if they aren't on the block list
        if name not in blocked_users:
            url = f'https://twitter.com/{name}/status/{s}'
            urls.append(url)

        count += 1
    print(urls)
    # converts list to json recognizable dictionary
    return dict(zip(range(0, 10), urls[::-1]))

# flask_app.run(host="127.0.0.1", port=80, debug=True)