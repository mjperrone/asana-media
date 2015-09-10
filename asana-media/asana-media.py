"""Add urls to asana, with title suggestions!"""
import logging
import os
import urlparse

import asana
from flask import Flask, request, session, redirect, render_template_string, render_template, jsonify, url_for
import flask_wtf
from wtforms import SelectField, SubmitField, StringField, BooleanField
from wtforms.validators import DataRequired

from reddit.utils import get_title

log = logging.getLogger(__name__)


CLIENT_ID = os.environ['ASANA_CLIENT_ID']
CLIENT_SECRET = os.environ['ASANA_CLIENT_SECRET']


def token_updater(token):
    session["token"] = token


# convience method to create an auto refreshing client with your credentials
def Client(**kwargs):
    return asana.Client.oauth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri='http://asana.mikejperrone.com/auth/asana/callback',
        auto_refresh_url=asana.session.AsanaOAuth2Session.token_url,
        auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        token_updater=token_updater,
        **kwargs
    )


app = Flask(__name__)


class WorkspaceSelectionForm(flask_wtf.Form):
    workspace = SelectField("workspace", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route('/workspace', methods=["GET", "POST"])
def set_workspace():
    token = session.get('token', False)
    if not token:
        return redirect(url_for("add_task"))

    if request.method == "POST":
        form = WorkspaceSelectionForm()
        form.workspace.choices = [(ws["id"], ws["name"]) for ws in session["workspaces"]]
        session["workspace"] = next(x for x in session["workspaces"] if int(x["id"]) == int(form.data["workspace"]))
        return redirect(url_for('set_project'))
    else:
        client = Client(token=token)
        me = client.users.me()
        form = WorkspaceSelectionForm()
        session["workspaces"] = me["workspaces"]
        form.workspace.choices = [(ws["id"], ws["name"]) for ws in me["workspaces"]]
        return render_template("select_workspace.html", name=me['name'], form=form)


class ProjectSelectionForm(flask_wtf.Form):
    project = SelectField("project", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route('/project', methods=["GET", "POST"])
def set_project():
    token = session.get('token', False)
    if not token:
        return redirect(url_for("add_task"))
    if not session["workspace"]:
        return redirect(url_for("set_workspace"))

    if request.method == "POST":
        form = ProjectSelectionForm()
        form.project.choices = [(p["id"], p["name"]) for p in session["projects"]]
        session["project"] = next(x for x in session["projects"] if int(x["id"]) == int(form.data["project"]))
        return redirect(url_for('add_task'))
    else:  # GET
        client = Client(token=token)
        projects = list(client.projects.find_all(workspace=session["workspace"]["id"], limit=25))
        form = ProjectSelectionForm()
        session["projects"] = projects
        form.project.choices = [(p["id"], p["name"]) for p in projects]
        return render_template("select_project.html", form=form, workspace=session["workspace"]["name"])


class TaskForm(flask_wtf.Form):
    title = StringField("Title:")
    url = StringField("URL:")
    submit = SubmitField("Submit")
    assign_to_me = BooleanField("Assign To Me")


@app.route("/", methods=["GET", "POST"])
def add_task():
    token = session.get('token', False)
    if not token:
        (auth_url, state) = Client().session.authorization_url()
        session['state'] = state
        return render_template_string(
            '''
            <p><a href="{{ auth_url }}"><img src="https://luna1.co/7df202.png"></a></p>''',
            auth_url=auth_url
        )
    if not session.get("user"):
        client = Client(token=token)
        me = client.users.me()
        session["user"] = {"name": me["name"], "id": me["id"], "photo": me.get("photo", {})}
    if not session.get("workspace"):
        return redirect(url_for("set_workspace"))
    if not session.get("project"):
        return redirect(url_for("set_project"))

    if request.method == "GET":
        form = TaskForm(assign_to_me=session.get("assign_to_me", False))
        return render_template("add_task.html", form=form, workspace=session["workspace"]["name"])
    else:  # POST
        client = Client(token=token)
        form = TaskForm()
        session["assign_to_me"] = form.data["assign_to_me"]
        task = client.tasks.create({
            "workspace": session["workspace"]["id"],
            "name": form.data["title"],
            "notes": form.data["url"],
            "assignee": session["user"]["id"] if form.data["assign_to_me"] else None,
            "projects": [session["project"]["id"]],
        })
        return render_template(
            "add_task.html",
            form=form,
            workspace=session["workspace"]["name"],
            project_id=session["project"]["id"],
            project=session["project"]["name"],
            task_title=task["name"],
        )


@app.route("/logout")
def logout():
    del session['token']
    return redirect(url_for('add_task'))


@app.route("/auth/asana/callback")
def auth_callback():
    if request.args.get('state') == session['state']:
        del session['state']
        session['token'] = Client().session.fetch_token(code=request.args.get('code'))
        return redirect(url_for('add_task'))
    else:
        return "state doesn't match!"


@app.route('/suggest_title')
def suggest_title():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "must provide url"})
    title = get_title(url)
    if not title:
        # make something up based on the url
        parsed = urlparse.urlparse(url)
        title = "{} | {}".format(
            parsed.netloc,
            os.path.split(os.path.splitext(parsed.path)[0])[1]
        )
    return jsonify({"title": title})


@app.route('/health')
def health():
    return "Healthy!"

app.debug = os.environ.get("FLASK_DEBUG", False)
if app.debug:
    app.secret_key = "debug"
else:
    app.secret_key = os.environ["FLASK_SECRET_KEY"]

if __name__ == "__main__":
    app.run()
