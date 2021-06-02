#!/bin/bash
gunicorn "app.web.server:flask_app"
