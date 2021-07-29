from pathlib import Path
import re

from steam.core.crypto import sha1_hash
from timelimits import TimeRange
from utils import human_readable

from gevent.socket import wait_read, wait_write
from gevent import sleep

import logging
logging.basicConfig(
    format='[%(asctime)s] === %(levelname)s === %(message)s',
    datefmt='%m/%d/%Y - %I:%M:%S',
    filename='log.txt',
    encoding='utf-8',
    level=logging.INFO
)
logger = logging

class ManifestProcess():
    '''
    Class used for wrapping the steam manifest download process.
    '''
    def __init__(self, pipe, cdn, download_path, timerange=TimeRange(0, 0, 0, 0)):
        '''
        Constructor method. Sets up the class object
        '''
        self.pipe = pipe
        self.cdn = cdn
        self.download_path = download_path
        self.downloading = False
        self.alive = True
        self.time_range = timerange
        self.target_app = None
        self.filter_func = None
        logger.info("Manifest Process object created")

    def download_app(self, app_id: int):
        '''
        Class method. Attempts to download an app given an app id. Encapsulates the logic behind manifests.
        '''
        print("Working on app: {}".format(app_id))
        logger.info("Working on app: %s", app_id)
        if self.time_range.inside_window():
            self.downloading = True
            logger.info("Process is inside window, continuing")
        else:
            logger.warn("Process manager is outside of time window")
            return

        # Get the manifest from the cdn
        print(self.cdn.steam.logged_on)
        if not self.cdn.steam.logged_on:
            try:
                self.steam.db_login()
            except:
                pass

        # Add a definition for the filter func
        if self.filter_func is None:
            def filter(depot_id, depot_info):
                filters_json = self.cdn.steam.get_settings_as_json()

                for filter in filters_json['languages']:
                    if re.search(filter, depot_info['name'], re.IGNORECASE):
                        logger.info("Filter func: Removed %s", depot_info)
                        return False

                for filter in filters_json['os_list']:
                    if re.search(filter, depot_info['name'], re.IGNORECASE):
                        logger.info("Filter func: Removed %s", depot_info)
                        return False
                    
                return True

            self.filter_func = filter

        manifests = self.cdn.get_manifests(int(app_id), filter_func=self.filter_func)
        logger.info("[%s]: Manifests: %s", self.target_app, manifests)

        for man in manifests:
            logger.info("[%s] Working on depot %s", self.target_app, man.name)
            print(man.name)
            if self.downloading:
                self.handle_manifest(man)

    def pump_messages(self):
        '''
        Class method. Because the download process exists within a gevent Greenlet, we can poll it with Pipes.

        Commands: 
            - 'stop' -> Stop the process from downloading.
            - 'start' -> Start the process downloading.
            - 'download' -> Tuple message; msg[1] is the app id to download.

        Note: While pumping messages, the system will begin downloading if it gets within the time window.
        '''
        # Poll the pipe for new info
        while self.pipe.poll():
            wait_read(self.pipe.fileno())
            msg = self.pipe.recv()
            logger.info("[%s]: Received message: `%s`", self.target_app, msg)

            if msg == "stop":
                self.downloading = False
            elif msg == "start":
                self.downloading = True
            elif msg[0] == "download":
                self.target_app = msg[1]
                self.download_app(msg[1])

            elif msg == 'query':
                wait_write(self.pipe.fileno())
                self.pipe.send(self.downloading)

        # if entering the window
        if self.time_range.inside_window() and not self.downloading:
            # Run the downloader
            self.downloading = True
            self.download_app(self.target_app)

        # If leaving the windoe
        if not self.time_range.inside_window() and self.downloading:
            self.downloading = False


    def handle_manifest(self, manifest):
        '''
        Class method. Given a manifest, downloading the files from the steam sever.
        '''
        base_path = Path(self.download_path)

        # Grab the file iterator
        file_list_iterator = manifest.iter_files()

        total_bytes = 0

        for file in file_list_iterator:
            logger.debug("[%s] Getting file %s", self.target_app, file)

            # Check if there are any messages in the pipe
            self.pump_messages()

            # Check for the stop condition
            if not self.downloading:
                return

            # Build the file path
            fp = base_path / file.filename

            # Check if the file exists 
            if not fp.exists():
                # Create the file if it does not
                Path(fp.parents[0]).mkdir(parents=True, exist_ok=True)

            # Read the chunks from the file and iterate over them.
            for chunk in file.chunks:
                # Pump messages after each chunk to improve responsiveness when downloading large files
                self.pump_messages()

                # Verify the sha1 hash of the file
                try:
                    with open(fp, 'rb') as f:
                        # Ensure we are seeking over actual data, as in the offset does not exceed the filesize
                        # because that's undefined behavior in python! For some reason.
                        max_offset = len(f.read())
                        f.seek(0)

                        if chunk.offset < max_offset:
                            f.seek(chunk.offset)
                            cur_data = f.read(chunk.cb_original)
                            if sha1_hash(cur_data) == chunk.sha:
                                # if the two are the same, we have the entire chunk!
                                total_bytes += chunk.cb_original
                                logger.debug("[%s] Chunk `%s` has the same hash as disk, skipping. . .", self.target_app, chunk.sha.hex())
                                continue
                except FileNotFoundError:
                    pass

                # get the chunk data from the cdn
                data = self.cdn.get_chunk(manifest.app_id, manifest.depot_id, chunk.sha.hex())
                logger.info(
                    "[%s] Got data for chunk `%s` from server (%s of %s bytes)",
                    self.target_app,
                    chunk.sha.hex(),
                    human_readable(total_bytes),
                    human_readable(file.size)
                )

                #Write the data to the file
                with open(fp, 'a+b') as f:
                    f.seek(chunk.offset)
                    f.write(data)

                total_bytes += chunk.cb_original


def manifest_process_factory(*args, **kwargs):
    '''
    Wrapper function used to create a new process. *args and **kwargs are passed directly into
    the ManifestProcess constructor. It will then sleep and pump the messages for the process until
    something occurs it needs to handle.
    '''
    p = ManifestProcess(*args, **kwargs)

    while p.alive:
        sleep(10)
        p.pump_messages()
