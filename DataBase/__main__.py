#!flask/bin/python
from app import app

app.run("0.0.0.0", 5555, debug=False)
