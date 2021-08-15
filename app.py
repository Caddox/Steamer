# To prevent gevent errors between Flask and steam.client
from gevent import monkey

monkey.patch_all()

from flask import Flask, render_template, request, redirect, url_for
from steam.enums import EResult
from client import LocalSteamClient
from db import init_app, get_db, query_builder
from pathlib import Path
from utils import human_readable

from timelimits import TimeRange

# Init flask and its friends
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(DATABASE="./steamer.db")
init_app(app)  # Setup the db connection for Flask
steam = LocalSteamClient()


@app.route("/")
def main_page():
    """
    App route for rendering `home.html`. Touches the database for app information and the username.

    Redirects: Redirects to login page if the user is not logged in.
    """
    if not steam.logged_on:
        return redirect(url_for("login_dummy"))
        # return "Please run the setup.py file. Steam can't work without it!"

    db = get_db()
    apps = db.execute(
        "select * from apps where name not like '%Server%' and logo not like '' order by name ASC"
    ).fetchall()
    username = steam.username
    return render_template("home.html", apps=apps, username=username)


@app.route("/settings")
def settings_page():
    """
    App route for displaying the settings page.
    """
    return render_template("settings.html", settings=steam.get_settings_as_json())


@app.route("/login")
def login_dummy():
    """
    App route for the login page. Renders `login.html`
    """
    return render_template("login.html")


@app.route("/app/<app_id>")
def app_page(app_id):
    """
    App route for individual apps. Renders `app.html` after looking in the database for depots belonging to the app.
    Filters app information based on DLC and ignoring Linux and Mac depots.

    Inputs: app_id: Integer ID for a steam app.

    Note: This function also preforms calls to `human_readable(bytes)` to calculate the space needed by each depot.
    """
    db = get_db()

    # depot_info = db.execute("select * from depots where app_id=? and is_dlc=0 and name not like '%Linux' and name not like '%Mac%'", (app_id,)).fetchall()
    depot_ids = [app_id] + steam.get_filtered_depots_for_app(app_id)

    # Change the behavior for the case where no depots can be selected.
    unable_to_download = False
    if len(depot_ids) == 1:
        query_string = "select * from depots where app_id=? collate nocase"
        unable_to_download = True

    else:
        query_string = query_builder(
            "select * from depots where app_id=? and depot_id in (?",
            ",?",
            len(depot_ids) - 2,
            ") collate nocase",
        )

    depot_info = db.execute(query_string, depot_ids)
    app_name = db.execute("select name from apps where app_id=?", (app_id,)).fetchone()

    d_out = []
    total_size = 0
    for d in depot_info:
        depot_id, _, name, size, _, _, _ = d
        total_size += size
        size = human_readable(size)
        d_out.append((name, depot_id, size))

    return render_template(
        "app.html",
        depots=d_out,
        total_size=human_readable(total_size),
        app_name=app_name["name"],
        unable_to_download=unable_to_download,
    )


@app.route("/app/<app_id>/download", methods=["POST"])
def schedule_download(app_id):
    """
    App route for downloading a game from an app ID. *POST ONLY*

    Input:
    - Integer app_id -> app being targeted for download
    - JSON TimeRange -> time range app can be downloaded during.
    """
    # Get the JSON request from the website
    j = request.get_json()
    tr = TimeRange(
        int(j["start_hour"]),
        int(j["start_min"]),
        int(j["end_hour"]),
        int(j["end_min"]),
    )

    steam.download_app(app_id, tr)

    # Parse the time
    return "Okay!"


##### Some API Methods #####
@app.route("/api/v1/login", methods=["POST"])
def api_try_login():
    """
    API route for attempting to login to a steam account.

    **POST ONLY**

    Input:
    - JSON login_info -> Holds username, password, 2fa, and email code to try to login with.

    Output:
    - JSON result -> Returns bool:success, reason:str, and target:str to be parsed by the JavaScript
    """
    if steam.logged_on:
        return {"success": True}
    # Get the JSON content from the website
    j = request.get_json()

    # Try to log into steam using those creds
    result = steam.login(
        j["username"],
        password=j["password"],
        auth_code=j["email-code"],
        two_factor_code=j["2fa"],
    )

    if result == EResult.InvalidPassword:
        return {
            "success": False,
            "reason": "Bad username or password",
            "target": "password",
        }

    elif result in (EResult.AccountLogonDenied, EResult.InvalidLoginAuthCode):
        if result == EResult.InvalidLoginAuthCode:
            return {
                "success": False,
                "reason": "Bad Email Code",
                "target": "email-code",
            }
        return {
            "success": False,
            "reason": "Email Code Required",
            "target": "email-code",
        }

    elif result in (
        EResult.AccountLoginDeniedNeedTwoFactor,
        EResult.TwoFactorCodeMismatch,
    ):
        if result == EResult.TwoFactorCodeMismatch:
            return {"success": False, "reason": "Bad 2FA Code", "target": "2fa"}
        return {"success": False, "reason": "2FA Code Required", "target": "2fa"}

    elif result == EResult.ServiceUnavailable:
        return {
            "success": False,
            "reason": "Steam servers are currently dead.",
            "target": "steam",
        }

    # If we're good, try to add the user and pass to the database
    steam.add_login_to_db(j["username"], j["password"])

    return {"success": True}


@app.route("/api/v1/populate")
def update_app():
    """
    API route for populating apps with the Steam interface.

    Note: Often takes a long time to run.
    """
    # Try to run the populate app thingy for steam
    steam.populate_apps()
    return {"done": True}


@app.route("/api/v1/settings")
def api_get_settings():
    """
    API route for getting settings for the user to look at.
    """
    # Return JSON data containing the settings that can be updated.
    payload = {
        "download_location": str(steam.download_location.resolve()),
        "os_list": steam.os_list,
        "languages": steam.languages,
    }
    return payload


@app.route("/api/v1/settings/set", methods=["POST"])
def api_update_settings():
    """
    API route for updating settings

    **POST ONLY**
    """
    j = request.get_json()

    steam.update_settings("settings.json", j)

    return {"response": "Settings updated."}


@app.route("/api/v1/query_downloads")
def api_query_downloads():
    """
    API route for finding what items are in the download queue.

    Returns:
    - JSON -> data contains the information
    """
    s = steam.check_download_state_all()
    print(s)

    return {"data": s}
