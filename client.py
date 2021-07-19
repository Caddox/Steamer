from steam.client import SteamClient
from steam.client.cdn import CDNClient
import sqlite3
from pathlib import Path
from dl_handler import manifest_process_factory
from multiprocessing import Process, Pipe
import json
from gevent import spawn
from gevent.socket import wait_write, wait_read

import time

class LocalSteamClient(SteamClient):
    def __init__(self, *args, **kwargs):
        self.db_conn = None
        SteamClient.__init__(self, *args, **kwargs)
        self.set_credential_location('.')

        self.download_location: Path = Path('.')
        self.os_list = []
        self.languages = []
        self.load_settings_from_file("settings.json")

        self.init_db()
        try:
            self.db_login()
        except:
            pass
        #self.force_login()
        if self.logged_on:
            self.cdn = CDNClient(self)
        else :
            self.cdn = None
        self.process_list = []


    def init_db(self):
        self.db_conn = sqlite3.connect("steamer.db")

        # Make tables if they don't exist
        self.db_conn.execute("""
            create table if not exists apps (
                app_id number PRIMARY KEY,
                name text,
                logo text
            )
        """)

        self.db_conn.execute("""
            create table if not exists depots (
                depot_id number,
                app_id number,
                name text,
                size number,
                is_dlc bool
            )
        """)

        self.db_conn.execute("create table if not exists users (user text, pass text)")

        self.db_conn.commit()

    def force_login(self):
        if self.logged_on:
            return
        if self.relogin_available:
            self.relogin()
        else:
            self.cli_login()

    def db_login(self):
        user, password = self.db_conn.execute("select user, pass from users").fetchone()
        # Try to login
        self.login(user, password)

    def add_login_to_db(self, username, password):
        # Create the user table
        self.db_conn.execute("create table if not exists users (user text, pass text)")

        # Check the table for the user
        if self.db_conn.execute("select user from users where user=?", (username,)).fetchone() is not None:
            # Run the db_login?
            self.db_login()
            if self.logged_on is False:
                print("Data was saved, but the logon failed?")

        #Add the user to the table
        self.db_conn.execute("insert or ignore into users VALUES (?, ?)", (username, password,))

        self.db_conn.commit()

    def load_settings_from_file(self, filepath):
        p = Path(filepath)

        if not p.exists():
            payload = {
                'download_location': str(Path('./.downloads').resolve()),
                'os_list': [],
                'languages': [],
            }

            with open(p, 'w') as f:
                f.write(json.dumps(payload))

        # p is a json file.
        with open(p, 'r') as f:
            data = json.loads(f.read())

            self.download_location = Path(data['download_location'])
            self.os_list = data['os_list']
            self.languages = data['languages']

    def update_settings(self, settings_filepath, data):
        settings_file = Path(settings_filepath)
        current_settings = {}
        with open(settings_file, 'r') as f:
            current_settings = json.loads(f.read())

        current_settings.update(data)

        # Write the new settings
        with open(settings_file, 'w') as f:
            f.write(json.dumps(current_settings))

        # Re-read the settings back into the object
        self.load_settings_from_file(settings_filepath)

    def get_settings_as_json(self):
        out = {
            'download_location': str(self.download_location.resolve()),
            'os_list': self.os_list,
            'languages': self.languages,
        }

        return out


    def populate_apps(self):
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
        #print(ids)

        if len(ids) == 0:
            print("There is nothing to do.")
            return

        # call steam.get_product_info with these ids
        print("Reading from get_product_info. . .")
        apps = self.get_product_info(apps=ids) # This will take some time. . .

        # iterate over the returned apps to populate the database (eventually?)
        print("Iterating over apps and depots")
        app_list = []
        depot_list = []
        for app_id in apps['apps'].keys():
            if apps['apps'][app_id]["_missing_token"]: # If the item needs a further token, we ignore it.
                print(app_id, " is missing token")
                continue

            item = apps['apps'][app_id]

            # Populate some variables
            try:
                name = item['common']['name']
                logo = item['common']['logo']

            except KeyError:
                # Skip it I guess. . .
                continue

            # add items to the app_list
            app_list.append((app_id, name, logo))

            # Iterate over the depots
            try:
                depots = apps['apps'][app_id]['depots']
            except KeyError:
                #print(apps['apps'][app_id])
                continue

            for d_id in depots.keys():
                try:
                    int(d_id)
                    d_name = depots[d_id]['name']
                    size = depots[d_id]['maxsize']
                    dlc = False
                    if 'dlcappid' in depots[d_id].keys():
                        dlc = True
                except (ValueError, KeyError): # Skip the items that are not actually depots
                    #print(depots[d_id])
                    continue

                depot_list.append((d_id, app_id, d_name, size, dlc))

        # Out of the loop
        # Add the items to the database
        self.db_conn.executemany("insert into apps VALUES(?, ?, ?)", app_list)
        self.db_conn.executemany("insert into depots VALUES(?, ?, ?, ?, ?)", depot_list)
        self.db_conn.commit()

        end = time.time()
        print(f"Elapsed {end-start} seconds")

    def download_app(self, app_id, time_range, download_path=None):
        local_conn, proc_conn = Pipe()
        if download_path is None:
            download_path = self.download_location

        download_path = Path(download_path)
        download_path = download_path / str(app_id)
        
        if self.cdn is None:
            self.cdn = CDNClient(self)

        #proc = Process(target=manifest_process_factory, args=(proc_conn, self.cdn, download_path,), kwargs={'timerange': time_range}, daemon=True)
        proc = spawn(manifest_process_factory, proc_conn, self.cdn, download_path, timerange=time_range)
        proc.start()
        local_conn.send(["download", app_id])
        
        #add the process and some info to the process list
        self.process_list.append((local_conn, app_id, time_range))

        # Return the PID to search by for later
        print(dir(proc))
        return proc

    def check_download_state_all(self):
        state = []
        for item in self.process_list:
            wait_write(item[0].fileno())
            item[0].send("query")
            wait_read(item[0].fileno())
            running = item[0].recv()

            state.append((item[1], running))

        return state

    def get_apps(self):
        self.init_db()
        out = self.db_conn.execute("select * from apps where name not like '%Server%' and logo not like '' order by name ASC").fetchall()

        if len(out) == 0:
            self.populate_apps()
            return self.get_apps()

        return out

    def get_depots_for(self, app_id):
        self.init_db()
        out = self.db_conn.execute("select * from depots where app_id=? and is_dlc=0", (app_id,)).fetchall()

        return out

if __name__ == "__main__":
    client = LocalSteamClient()
    #client.populate_apps()
    #client.download_app(579180, './_579180')
