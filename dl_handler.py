from steam.core.crypto import sha1_hash
from pathlib import Path
from time import sleep
from timelimits import TimeRange

class ManifestProcess():
    def __init__(self, pipe, cdn, download_path, timerange=TimeRange(0, 0, 0, 0)):
        self.pipe = pipe
        self.cdn = cdn
        self.download_path = download_path
        self.downloading = False
        self.alive = True
        self.time_range = timerange
        self.target_app = None

    def download_app(self, app_id):
        print("Working on app: {}".format(app_id))
        if self.time_range.inside_window():
            self.downloading = True
        else:
            return

        # Get the manifest from the cdn
        manifests = self.cdn.get_manifests(app_id)
        for man in manifests:
            if self.downloading:
                self.handle_manifest(man)

    def pump_messages(self):
        # Poll the pipe for new info
        while self.pipe.poll():
            msg = self.pipe.recv()
            print(msg)

            if msg == "stop":
                self.downloading = False
            elif msg == "start":
                self.downloading = True
            elif msg[0] == "download":
                self.target_app = msg[1]
                self.download_app(msg[1])

            elif msg == 'query':
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
        base_path = Path(self.download_path)

        # Grab the file iterator
        file_list_iterator = manifest.iter_files()

        total_bytes = 0

        for file in file_list_iterator:
            # Check if there are any messages in the pipe
            self.pump_messages()

            # Check for the stop condition
            if not self.downloading:
                return

            # Build the file path
            fp = base_path / file.filename

            # Check if the file exists 
            offset = 0
            if not fp.exists():
                # Create the file if it does not
                #fp.mkdir(parents=True, exist_ok=True)
                Path(fp.parents[0]).mkdir(parents=True, exist_ok=True)

            # Read the file to the filepath 
            # Read the chunks from the file and iterate over them.
            for chunk in file.chunks:
                # Before we get the chunk, check if the size of the file is 
                # the same as the chunk.cb_original. If it is, skip the file download.
                try:
                    if fp.stat().st_size == chunk.cb_original:
                        # Skip the chunk
                        #print("Skipping chunk (already downloaded)")
                        total_bytes += chunk.cb_original
                        continue
                except FileNotFoundError:
                    # The file does not exist, so it must not be downloaded
                    pass

                # Verify the sha1 hash of the file
                with open(fp, 'rb') as f:
                    cur_data = f.read(chunk.cb_original)
                    if sha1_hash(cur_data) == chunk.sha:
                        # if the two are the same, we have the entire file!
                        total_bytes += chunk.cb_original
                        continue

                # get the chunk data from the cdn
                data = self.cdn.get_chunk(manifest.app_id, manifest.depot_id, chunk.sha.hex())
                #print("Got data for chunk {}".format(chunk))

                #Write the data to the file
                with open(fp, 'wb') as f:
                    f.write(data)

                total_bytes += chunk.cb_original


def manifest_process_factory(*args, **kwargs):
    p = ManifestProcess(*args, **kwargs)

    while p.alive:
        sleep(10)
        p.pump_messages()