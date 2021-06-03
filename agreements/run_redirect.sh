#!/bin/bash
gunicorn -c "redirect.conf.py" "app.web.redirect:flask_app" 