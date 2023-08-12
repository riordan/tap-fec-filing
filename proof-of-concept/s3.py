import s3fs
import re
from datetime import datetime
import io
import zipfile
import logging
import os

START_DATE = '20230701'
END_DATE = None
LOCALDIR = 'output/fec/'

# Setup logging
logging.basicConfig(level=logging.INFO)

def download_and_unzip(s3, file_path, local_dir):
    logging.info(f'Starting download and unzip of file: {file_path}')
    with s3.open(file_path, 'rb') as s3_file:
        with io.BytesIO(s3_file.read()) as byte_stream:
            with zipfile.ZipFile(byte_stream) as z:
                zip_folder = os.path.join(local_dir, os.path.splitext(os.path.basename(file_path))[0])
                os.makedirs(zip_folder, exist_ok=True)
                z.extractall(zip_folder)
                logging.info(f'Completed download and unzip of file: {file_path} to {zip_folder}')

                # Get last modified time
                info = s3.info(file_path)
                last_modified = info.get('LastModified').isoformat()

                # Write to file
                with open(os.path.join(zip_folder, "_LAST_MODIFIED_ON_FEC_SOURCE"), "w") as f:
                    f.write(last_modified)


def run_application(start_date, end_date):
    s3 = s3fs.S3FileSystem(anon=True, endpoint_url='https://s3-us-gov-west-1.amazonaws.com')

    file_paths = s3.ls('cg-519a459a-0ea3-42c2-b7bc-fa1143481f74/bulk-downloads/electronic')

    start_date = datetime.strptime(start_date, '%Y%m%d') if start_date else None
    end_date = datetime.strptime(end_date, '%Y%m%d') if end_date else None

    pattern = re.compile(r'\d{8}\.zip$')

    filtered_file_paths = [
        path for path in file_paths
        if pattern.search(path)
        and (start_date is None or datetime.strptime(path[-12:-4], '%Y%m%d') >= start_date)
        and (end_date is None or datetime.strptime(path[-12:-4], '%Y%m%d') < end_date)
    ]

    local_dir = LOCALDIR

    for path in filtered_file_paths:
        download_and_unzip(s3, path, local_dir)

def main():
    run_application(START_DATE, END_DATE)

if __name__ == "__main__":
    main()
