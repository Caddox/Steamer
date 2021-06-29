# To prevent gevent errors between Flask and steam.client
from threading import Timer
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, redirect, request
from client import LocalSteamClient
from db import init_app, get_db

from timelimits import TimeRange

# Init flask and its friends
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    DATABASE="./steamer.db"
)
init_app(app) # Setup the db connection for Flask
steam = LocalSteamClient()

def human_readable(bytes):
    '''
    Function used for translating a large byte value into something people can
    actually read.
    '''
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if bytes < 1024.0 or unit == 'PiB':
            break
        bytes /= 1024.0

    return f"{bytes:.2f} {unit}"

@app.route("/")
def main_page():
    if not steam.logged_on:
        return "Please run the setup.py file. Steam can't work without it!"

    db = get_db()
    apps = db.execute("select * from apps where name not like '%Server%' and logo not like '' order by name ASC").fetchall()
    username = steam.username
    return render_template("home.html", apps=apps, username=username)

@app.route("/app/<app_id>")
def app_page(app_id):
    db = get_db()
    depot_info = db.execute("select * from depots where app_id=? and is_dlc=0 and name not like '%Linux' and name not like '%Mac%'", (app_id,)).fetchall()
    app_name = db.execute("select name from apps where app_id=?", (app_id,)).fetchone()

    d_out = []
    total_size = 0
    for d in depot_info:
        depot_id, _, name, size, _ = d
        total_size += size
        size = human_readable(size)
        d_out.append((name, depot_id, size))
    
    return render_template("app.html", depots=d_out, total_size=human_readable(total_size), app_name=app_name['name'])

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/app/<app_id>/download", methods=["POST"])
def schedule_download(app_id):
    # Get the JSON request from the website
    j = request.get_json()
    tr = TimeRange(
        int(j['start_hour']),
        int(j['start_min']),
        int(j['end_hour']),
        int(j['end_min']),
    )

    steam.download_app(j['app_id'], tr)

    # Parse the time
    return "Okay!"
