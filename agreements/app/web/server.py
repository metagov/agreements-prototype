from flask import Flask, abort

flask_app = Flask(__name__)

def get_html(name):
    f = open(f'{name}.html')
    html = f.read()
    f.close()
    return html

@flask_app.route('/')
def home():
    return get_html('home')

flask_app.run(host="127.0.0.1", port=80, debug=True)