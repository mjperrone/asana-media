""""""
import json
import logging
import os
import asana
from flask import Flask, request, session, redirect, render_template_string


log = logging.getLogger(__name__)


# OAuth Instructions:
#
# 1. create a new application in your Asana Account Settings ("App" panel)
# 2. set the redirect URL to "http://localhost:5000/auth/asana/callback" (or whichever port you choose)
# 3. set your ASANA_CLIENT_ID and ASANA_CLIENT_SECRET environment variables

AUTHORIZATION_URL = "https://app.asana.com/-/oauth_authorize"
TOKEN_URL = "https://app.asana.com/-/oauth_token"
REFRESH_URL = TOKEN_URL

CLIENT_ID = os.environ['ASANA_CLIENT_ID']
CLIENT_SECRET = os.environ['ASANA_CLIENT_SECRET']


# convience method to create a client with your credentials, and optionally a 'token'
def Client(**kwargs):
    return asana.Client.oauth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri='http://localhost:5000/auth/asana/callback',
        **kwargs
    )

app = Flask(__name__)


@app.route("/")
def main():
    token = session.get('token', False)
    if token:
        def token_updater(token):
            session["token"] = token
        client = Client(
            token=token,
            auto_refresh_url=REFRESH_URL,
            auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
            token_updater=token_updater,
        )

        me = client.users.me()

        return render_template_string(
            '''
{%- if image_url -%}
<img src="{{ image_url }}">
{%- endif %}
<p>Hello {{ name }}.</p>
<p><pre>{{ dump }}</pre></p>
<p><a href="/logout">Logout</a></p>''',
            name=me['name'],
            image_url=me.get('photo', {}).get('image_60x60', None),
            dump=json.dumps(me, indent=2)
        )
    else:
        # show asana connect button
        (auth_url, state) = Client().session.authorization_url()
        session['state'] = state
        return render_template_string(
            '''
            <p><a href="{{ auth_url }}"><img src="https://luna1.co/7df202.png"></a></p>''',
            auth_url=auth_url
        )


@app.route("/logout")
def logout():
    del session['token']
    return redirect('/')


@app.route("/auth/asana/callback")
def auth_callback():
    if request.args.get('state') == session['state']:
        del session['state']
        session['token'] = Client().session.fetch_token(code=request.args.get('code'))
        return redirect('/')
    else:
        return "state doesn't match!"


@app.route('/health')
def health():
    return "Healthy!"


app.secret_key = "I don't understand what this does."

if __name__ == "__main__":
    app.debug = True
    app.run()
