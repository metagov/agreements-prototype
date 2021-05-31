#!/bin/bash
gunicorn -b 0.0.0.0:80 "app.web.server:flask_app"
