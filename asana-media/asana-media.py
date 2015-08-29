"""."""
from flask import Flask

app = Flask(__name__)


@app.route('/')
def index():
    return "Hello, world!"

@app.route('/health')
def health():
    return "Healthy!"

if __name__ == "__main__":
    app.debug = True # TODO: parametarize that
    app.run()
