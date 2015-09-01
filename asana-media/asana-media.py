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


def token_updater(token):
    session["token"] = token
# convience method to create an auto refreshing client with your credentials
def Client(**kwargs):
    return asana.Client.oauth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri='http://localhost:5000/auth/asana/callback',
        auto_refresh_url=asana.session.AsanaOAuth2Session.token_url,
        auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        token_updater=token_updater,
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
        session["workspace"] = next(x for x in session["workspaces"] if int(x["id"]) == int(form.data["workspace"]))
        return redirect(url_for('set_project'))
    elif token:
        client = Client(token=token)
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
        return redirect(url_for('add_task'))
    elif token:
        client = Client(token=token)
        projects = list(client.projects.find_all(workspace=session["workspace"]["id"], limit=25))
        form = ProjectSelectionForm()
        session["projects"] = projects
        form.project.choices = [(p["id"], p["name"]) for p in projects]
        return render_template("select_project.html", form=form, workspace=session["workspace"]["name"])


class TaskForm(Form):
    title = StringField("title")
    description = TextAreaField("description")
    submit = SubmitField("Submit")


@app.route("/task", methods=["GET", "POST"])
def add_task():
    token = session.get('token', False)
    if request.method == "GET":
        form = TaskForm()
        return render_template("add_task.html", form=form, workspace=session["workspace"]["name"])
    elif token:
        client = Client(token=token)
        form = TaskForm()
        task = client.tasks.create({
            "workspace": session["workspace"]["id"],
            "name": form.data["title"],
            "notes": form.data["description"],
            "assignee": session["user"]["id"],
            "projects": [session["project"]],
        })
        return render_template("add_task.html", form=form, workspace=session["workspace"]["name"])


@app.route("/")
def index():
    token = session.get('token', False)
    if token:
        if not session.get("user"):
            client = Client(token=token)
            me = client.users.me()
            session["user"] = {"name": me["name"], "id": me["id"], "photo": me.get("photo", {})}
        if not session.get("workspace"):
            return redirect(url_for("set_workspace"))
        if not session.get("project"):
            return redirect(url_for("set_project"))

        return render_template_string(
            '''
{%- if image_url -%}
<img src="{{ image_url }}">
{%- endif %}
<p>Hello {{ name }}.</p>
<p><pre>{{ dump }}</pre></p>
<p><a href="/logout">Logout</a></p>''',
            name=session["user"]["name"],
            image_url=session["user"]["photo"].get('image_60x60', None),
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
