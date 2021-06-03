#!/bin/bash
gunicorn -c "ssl.conf.py" "app.web.server:flask_app"
