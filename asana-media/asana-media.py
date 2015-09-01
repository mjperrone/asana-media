""""""
import json
import logging
import os
import asana
from flask import Flask, request, session, redirect, render_template_string, render_template, jsonify, url_for

from flask_wtf import Form
from wtforms import SelectField, SubmitField, TextAreaField, StringField
from wtforms.validators import DataRequired

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


class WorkspaceSelectionForm(Form):
    workspace = SelectField("workspace", validators=[DataRequired()])
    submit = SubmitField("Submit")


class ProjectSelectionForm(Form):
    project = SelectField("project", validators=[DataRequired()])
    submit = SubmitField("Submit")

app = Flask(__name__)


@app.route('/workspace', methods=["GET", "POST"])
def set_workspace():
    token = session.get('token', False)
    if request.method == "POST":
        form = WorkspaceSelectionForm()
        form.workspace.choices = [(ws["id"], ws["name"]) for ws in session["workspaces"]]
        session["workspace"] = form.data["workspace"]
        return redirect(url_for('set_project'))
    elif token:
        def token_updater(token):
            session["token"] = token
        client = Client(
            token=token,
            auto_refresh_url=REFRESH_URL,
            auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
            token_updater=token_updater,
        )
        me = client.users.me()
        form = WorkspaceSelectionForm()
        session["workspaces"] = me["workspaces"]
        form.workspace.choices = [(ws["id"], ws["name"]) for ws in me["workspaces"]]
        return render_template("select_workspace.html", name=me['name'], form=form)


@app.route('/project', methods=["GET", "POST"])
def set_project():
    token = session.get('token', False)
    if request.method == "POST":
        form = ProjectSelectionForm()
        form.project.choices = [(p["id"], p["name"]) for p in session["projects"]]

        session["project"] = form.data["project"]
        return jsonify(dict(session))
    elif token:
        def token_updater(token):
            session["token"] = token
        client = Client(
            token=token,
            auto_refresh_url=REFRESH_URL,
            auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
            token_updater=token_updater,
        )
        projects = list(client.projects.find_all(workspace=session["workspace"], limit=25))
        form = ProjectSelectionForm()
        session["projects"] = projects
        form.project.choices = [(p["id"], p["name"]) for p in projects]
        return render_template("select_project.html", form=form)


class TaskForm(Form):
    title = StringField("title")
    description = TextAreaField("description")
    submit = SubmitField("Submit")


@app.route("/task", methods=["GET", "POST"])
def add_task():
    token = session.get('token', False)
    if request.method == "GET":
        form = TaskForm()
        return render_template("add_task.html", form=form)

    elif token:
        def token_updater(token):
            session["token"] = token
        client = Client(
            token=token,
            auto_refresh_url=REFRESH_URL,
            auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
            token_updater=token_updater,
        )
        form = TaskForm()
        task = client.tasks.create({
            "workspace": session["workspace"]["name"],
            "name": form.data["title"],
            "notes": form.data["description"],
            "assignee": session["user_id"],
            "projects": [session["project"]],
        })


@app.route("/")
def index():
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
        session["user_name"] = me["name"]
        session["user_id"] = me["id"]

        task = client.tasks.create({
            "workspace": session["workspace"]["id"],
            "name": "zzzzzzzzzzzzzzzzzzzzzzzzzzz baby",
            "notes": "zomg zomg zomg zomg zomg zomg zomg zomg zomg zomg zomg zomg",
            "assignee": session["user_id"],
            "projects": [session["project"]],
        })
        # me["taskzz"] = task
        # me["projectzz"] = list(client.projects.find_all(workspace=46626782955421, limit=5))

        form = WorkspaceSelectionForm()
        session["workspaces"] = me["workspaces"]
        form.workspace.choices = [(ws["id"], ws["name"]) for ws in me["workspaces"]]
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
            dump=json.dumps(dict(session), indent=2)
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
    return redirect(url_for('index'))


@app.route("/auth/asana/callback")
def auth_callback():
    if request.args.get('state') == session['state']:
        del session['state']
        session['token'] = Client().session.fetch_token(code=request.args.get('code'))
        return redirect(url_for('index'))
    else:
        return "state doesn't match!"


@app.route('/health')
def health():
    return "Healthy!"


app.secret_key = "I don't understand what this does."

if __name__ == "__main__":
    app.debug = True
    app.run()
