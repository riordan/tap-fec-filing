Now, let's write the code for our application.

tap_fec_filings.py
```python
import os
import re
import json
import logging
import s3fs
import zipfile
import io
from datetime import datetime
from collections import OrderedDict
from fastfec import FastFEC
from singer_sdk import Tap, Stream, typing as th

# Setup logging
logging.basicConfig(level=logging.INFO)

class FECFilingStream(Stream):
    name = "fec_filing"
    primary_keys = ["filing_id"]
    schema = th.PropertiesList(
        th.Property("filing_id", th.StringType),
        th.Property("fec_filing_date", th.StringType),
        th.Property("_FEC_SOURCE_LAST_MODIFIED_AT", th.StringType),
        # Add other properties here
    ).to_dict()

class FECFilingTap(Tap):
    name = "tap-fec-filings"
    streams = [FECFilingStream]
    config_jsonschema = th.PropertiesList(
        th.Property("start_date", th.StringType),
        th.Property("end_date", th.StringType, required=False),
        th.Property("s3_bucket", th.StringType),
        th.Property("local_dir", th.StringType),
    ).to_dict()

    def get_files_to_download(self):
        s3 = s3fs.S3FileSystem(anon=True)
        file_paths = s3.ls(self.config["s3_bucket"])
        start_date = datetime.strptime(self.config["start_date"], '%Y%m%d')
        end_date = datetime.strptime(self.config["end_date"], '%Y%m%d') if self.config["end_date"] else None
        pattern = re.compile(r'\d{8}\.zip$')
        return [
            path for path in file_paths
            if pattern.search(path)
            and datetime.strptime(path[-12:-4], '%Y%m%d') >= start_date
            and (end_date is None or datetime.strptime(path[-12:-4], '%Y%m%d') < end_date)
        ]

    def download_and_unzip(self, s3, file_path):
        with s3.open(file_path, 'rb') as s3_file:
            with io.BytesIO(s3_file.read()) as byte_stream:
                with zipfile.ZipFile(byte_stream) as z:
                    zip_folder = os.path.join(self.config["local_dir"], os.path.splitext(os.path.basename(file_path))[0])
                    os.makedirs(zip_folder, exist_ok=True)
                    z.extractall(zip_folder)
                    info = s3.info(file_path)
                    last_modified = info.get('LastModified').isoformat()
                    with open(os.path.join(zip_folder, "_FEC_SOURCE_LAST_MODIFIED_AT"), "w") as f:
                        f.write(last_modified)

    def parse_fec_files(self, input_directory):
        date_dir_pattern = re.compile(r"\d{8}")
        for root, dirs, files in os.walk(input_directory):
            if date_dir_pattern.match(os.path.basename(root)):
                last_modified_time_file_path = os.path.join(root, "_FEC_SOURCE_LAST_MODIFIED_AT")
                with open(last_modified_time_file_path, "r") as f:
                    last_modified_time = f.read().strip()
                for file in files:
                    if file.endswith(".fec"):
                        filing_date = os.path.basename(root)
                        with open(os.path.join(root, file), "rb") as f:
                            with FastFEC() as fastfec:
                                for form_type, line in fastfec.parse(f, include_filing_id=file[:-4]):
                                    line = OrderedDict(
                                        list(line.items())[:1]
                                        + [("fec_filing_date", filing_date)]
                                        + [("_FEC_SOURCE_LAST_MODIFIED_AT", last_modified_time)]
                                        + list(line.items())[1:]
                                    )
                                    yield line

    def do_sync(self):
        s3 = s3fs.S3FileSystem(anon=True)
        for file_path in self.get_files_to_download():
            self.download_and_unzip(s3, file_path)
        for line in self.parse_fec_files(self.config["local_dir"]):
            self.write_record("fec_filing", line)

def main():
    tap = FECFilingTap()
    tap.run()

if __name__ == "__main__":
    main()