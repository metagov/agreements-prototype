from flask import Flask, abort

flask_app = Flask(__name__)

def get_html(name):
    f = open(f'app/web/{name}.html')
    html = f.read()
    f.close()
    return html

@flask_app.route('/')
def home():
    return get_html('home')

@flask_app.route('/about')
def about():
    return get_html('about')

@flask_app.route('/help')
def help():
    return get_html('help')

# flask_app.run(host="127.0.0.1", port=80, debug=True)