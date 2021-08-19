from steam.client import SteamClient
from steam.client.cdn import CDNClient
import sqlite3
from pathlib import Path
from dl_handler import manifest_process_factory
from multiprocessing import Pipe
import json
from gevent import spawn
from gevent.socket import wait_write, wait_read
from db import query_builder
from timelimits import TimeRange

import time


class LocalSteamClient(SteamClient):
    """
    Class wrapping the steam client.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor for the class. *args and **kwargs are passed into the
        constructor for the SteamClient class.

        Initalizes class by setting credential location, attempting login, and setting up the database.
        """
        self.db_conn = None
        SteamClient.__init__(self, *args, **kwargs)
        self.set_credential_location(".")

        self.download_location: Path = Path(".")
        self.os_list = []
        self.languages = []
        self.load_settings_from_file("settings.json")

        self.init_db()
        try:
            self.db_login()
        except:
            pass
        # self.force_login()
        if self.logged_on:
            self.cdn = CDNClient(self)
        else:
            self.cdn = None
        self.process_list = []

    def init_db(self):
        """
        Class method. Initilizes the database `steamer.db`

        If the database already exists, nothing is done.
        """
        self.db_conn = sqlite3.connect("steamer.db")

        # Make tables if they don't exist
        self.db_conn.execute(
            """
            create table if not exists apps (
                app_id number PRIMARY KEY,
                name text,
                logo text,
                dl_dir text,
                oses test,
                langs text
            )
        """
        )

        self.db_conn.execute(
            """
            create table if not exists depots (
                depot_id number,
                app_id number,
                name text,
                size number,
                is_dlc bool,
                oses text,
                langs text
            )
        """
        )

        self.db_conn.execute("create table if not exists users (user text, pass text)")

        self.db_conn.commit()

    def force_login(self):
        """
        Class method. A command line way to attempt to login.

        Basically useless because we don't use the command line to login anymore.
        """
        if self.logged_on:
            return
        if self.relogin_available:
            self.relogin()
        else:
            self.cli_login()

    def db_login(self):
        """
        Class method. Queries the database to see if there is a username and password saved.
        If there is, it attempts to login with them.
        """
        user, password = self.db_conn.execute("select user, pass from users").fetchone()
        # Try to login
        self.login(user, password)

    def add_login_to_db(self, username: str, password: str):
        """
        Class method. Addes the table of users, then adds the username and password to the database.

        Really not a good idea, being plaintext and all, but I can't find another option.
        """
        # Create the user table
        self.db_conn.execute("create table if not exists users (user text, pass text)")

        # Check the table for the user
        if (
            self.db_conn.execute(
                "select user from users where user=?", (username,)
            ).fetchone()
            is not None
        ):
            # Run the db_login?
            self.db_login()
            if self.logged_on is False:
                print("Data was saved, but the logon failed?")

        # Add the user to the table
        self.db_conn.execute(
            "insert or ignore into users VALUES (?, ?)",
            (
                username,
                password,
            ),
        )

        self.db_conn.commit()

    def load_settings_from_file(self, filepath):
        """
        Class method. Loads the settings the user has defined into the Steam client object.
        """
        p = Path(filepath)

        if not p.exists():
            payload = {
                "download_location": str(Path("./.downloads").resolve()),
                "os_list": ["windows"],
                "languages": ["english"],
            }

            with open(p, "w") as f:
                f.write(json.dumps(payload))

        # p is a json file.
        with open(p, "r") as f:
            data = json.loads(f.read())

            self.download_location = Path(data["download_location"])
            self.os_list = data["os_list"]
            self.languages = data["languages"]

    def update_settings(self, settings_filepath, data):
        """
        Class method. Update the settings in both the object and the given filepath.
        """
        settings_file = Path(settings_filepath)
        current_settings = {}
        with open(settings_file, "r") as f:
            current_settings = json.loads(f.read())

        current_settings.update(data)

        # Write the new settings
        with open(settings_file, "w") as f:
            f.write(json.dumps(current_settings))

        # Re-read the settings back into the object
        self.load_settings_from_file(settings_filepath)

    def get_settings_as_json(self):
        """
        Class method. Returns the settings in the file as a dictionary
        """
        out = {
            "download_location": str(self.download_location.resolve()),
            "os_list": self.os_list,
            "languages": self.languages,
        }

        return out

    def populate_apps(self):
        """
        Class method. Using the Steam client functionallity, populate the database with:
        - App info, including name, app id, and logo (url)
        - Depot info, including name, app id, depot id, size (in bytes), and a boolean is_dlc marker.

        Note: Often very slow. The SteamClient emulates a, well, Steam client, without actually being Steam itself.
        It's just very slow, but is faster when the database is populated.
        """
        start = time.time()

        # Ensure the client is logged in
        if not self.logged_on and self.relogin_available:
            self.db_login()
            self.relogin()
            self.cdn = CDNClient(self)

        # Grab the ids from the cdn
        print("Loading licenses into CDN")
        if self.cdn is None:
            self.cdn = CDNClient(self)

        self.cdn.load_licenses()

        ids = list(self.cdn.licensed_app_ids)

        # Check the list of ids agains the ones in the database
        db_ids = self.db_conn.execute("select app_id from apps").fetchall()
        db_ids = list(sum(db_ids, ()))

        ids = list(set(ids).symmetric_difference(set(db_ids)))
        ids.sort()
        # print(ids)

        if len(ids) == 0:
            print("There is nothing to do.")
            return

        # call steam.get_product_info with these ids
        print("Reading from get_product_info. . .")
        apps = self.get_product_info(apps=ids)  # This will take some time. . .

        # iterate over the returned apps to populate the database (eventually?)
        print("Iterating over apps and depots")
        app_list = []
        depot_list = []
        for app_id in apps["apps"].keys():
            if apps["apps"][app_id][
                "_missing_token"
            ]:  # If the item needs a further token, we ignore it.
                print(app_id, " is missing token")
                continue

            item = apps["apps"][app_id]

            # Populate some variables
            try:
                name = item["common"]["name"]
                logo = item["common"]["logo"]

            except KeyError:
                # Skip it I guess. . .
                continue

            # Evaluate os's and languages on the app level
            try:
                app_oses = item["common"]["oslist"]
                app_langs_dict = item["common"]["languages"]
                app_langs = ",".join(app_langs_dict.keys())

            except KeyError:
                app_oses = ""
                app_langs = ""

            # Get the name of the download directory for the game
            try:
                dl_dir = item["config"]["installdir"]
            except KeyError:
                dl_dir = name

            # add items to the app_list
            app_list.append((app_id, name, logo, dl_dir, app_oses, app_langs))

            # Iterate over the depots
            try:
                depots = apps["apps"][app_id]["depots"]
            except KeyError:
                # print(apps['apps'][app_id])
                continue

            for d_id in depots.keys():
                try:
                    int(d_id)
                    d_name = depots[d_id]["name"]
                    size = depots[d_id]["maxsize"]
                    dlc = False
                    if "dlcappid" in depots[d_id].keys():
                        dlc = True
                except (
                    ValueError,
                    KeyError,
                ):  # Skip the items that are not actually depots
                    # print(depots[d_id])
                    continue

                try:
                    oses = depots[d_id]["config"]["oslist"]
                except KeyError:
                    oses = ""

                try:
                    langs = depots[d_id]["config"]["language"]
                except KeyError:
                    langs = ""

                depot_list.append((d_id, app_id, d_name, size, dlc, oses, langs))

        # Out of the loop
        # Add the items to the database
        self.db_conn.executemany("insert into apps VALUES(?, ?, ?, ?, ?, ?)", app_list)
        self.db_conn.executemany(
            "insert into depots VALUES(?, ?, ?, ?, ?, ?, ?)", depot_list
        )
        self.db_conn.commit()

        end = time.time()
        print(f"Elapsed {end-start} seconds")

    def download_app(
        self, app_id: int, time_range: TimeRange, download_path: Path = None
    ):
        """
        Class method. Wraps calls to the download handler, which itself is wrapped in a gevent spawn command.

        Inputs:
        - app_id: int -> The app id to download.
        - time_range: TimeRange -> The time the app is able to be downloaded during.
        - download_path: (Path | None) -> The path the download the content to.

        Adds information on the greenlit to `self.process_list`
        """
        local_conn, proc_conn = Pipe()
        if download_path is None:
            download_path = self.download_location

        # Grab the game's name to put as the filepath like Steam does.
        dl_dir = self.db_conn.execute(
            "select dl_dir from apps where app_id=?", (app_id,)
        ).fetchone()[0]
        download_path = Path(download_path)
        download_path = download_path / str(dl_dir)

        # Get the whitelist of depots for the app_id
        depot_whitelist = self.get_filtered_depots_for_app(app_id)

        if self.cdn is None:
            self.cdn = CDNClient(self)

        # proc = Process(target=manifest_process_factory, args=(proc_conn, self.cdn, download_path,), kwargs={'timerange': time_range}, daemon=True)
        proc = spawn(
            manifest_process_factory,
            proc_conn,
            self.cdn,
            download_path,
            timerange=time_range,
            depot_whitelist=depot_whitelist,
        )
        proc.start()
        local_conn.send(["download", app_id])

        # add the process and some info to the process list
        self.process_list.append((local_conn, app_id, time_range))

        # Return the PID to search by for later
        return proc

    def check_download_state_all(self):
        """
        Class method. Polls all processes it knows of, and queries their state.

        Returns:
        - List (app_id:int, running:str)
        """
        state = []
        for item in self.process_list:
            wait_write(item[0].fileno())
            item[0].send("query")
            wait_read(item[0].fileno())
            running = item[0].recv()

            state.append((item[1], running))

        return state

    def get_filtered_depots_for_app(self, app_id):
        """
        Class method. Returns a list of depot id's that are visible with the current
        filters on both language and os.
        """
        filter_vals = self.os_list[:]
        oses_string = query_builder(
            "(oses like ?", "or oses like ?", len(self.os_list) - 1, " or oses='')"
        )

        filter_vals.extend(self.languages[:])
        langs_string = query_builder(
            "(langs like ?", "or langs like ?", len(self.languages) - 1, " or langs='')"
        )

        query_string = (
            "select depot_id from depots where app_id = ? and "
            + oses_string
            + " and "
            + langs_string
            + " collate nocase"
        )
        # select * from depots where app_id=? and ([oses like '%?[oses]%'] or oses like '') and (langs like '%?[langs]%' or langs like '') collate nocase

        filter_vals = ["%" + i + "%" for i in filter_vals]
        filter_vals.insert(0, int(app_id))

        depot_info = list(
            sum(self.db_conn.execute(query_string, filter_vals).fetchall(), ())
        )
        return depot_info

    def get_apps(self):
        """
        Class method. Used to select apps from the databse.

        Outdated and unused due to Flask using gevent. It's just easier to access the database directy.
        """
        self.init_db()
        out = self.db_conn.execute(
            "select * from apps where name not like '%Server%' and logo not like '' order by name ASC"
        ).fetchall()

        if len(out) == 0:
            self.populate_apps()
            return self.get_apps()

        return out

    def get_depots_for(self, app_id: int):
        """
        Class method. Used to select the depots of a given app_id.

        Inputs:
        - app_id: int -> App id to target.

        Outdated and unused due to Flask using gevent. It's just easier to access the database directy.
        """
        self.init_db()
        out = self.db_conn.execute(
            "select * from depots where app_id=? and is_dlc=0", (app_id,)
        ).fetchall()

        return out


if __name__ == "__main__":
    client = LocalSteamClient()
