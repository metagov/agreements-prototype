from flask import Flask, redirect, request

flask_app = Flask(__name__)

@flask_app.before_request
def before_request():
    # redirects http requests to https
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)