from flask import Flask, abort

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello world!"
