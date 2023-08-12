import os
from collections import OrderedDict
import re
import json
from datetime import date, datetime
from fastfec import FastFEC
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

FEC_INPUT_DIRECTORY = "output/fec/"
JSONL_OUTPUT_DIRECTORY = "output/jsonl/"


def sanitize_filename(filename):
    sanitized_filename = filename.replace("/", "__").upper()
    sanitized_filename = "".join(
        [c for c in sanitized_filename if c.isalpha() or c.isdigit() or c == " "]
    ).rstrip()

    return sanitized_filename


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def process_fec_files(input_directory):
    date_dir_pattern = re.compile(r"\d{8}")  # matches directories that represent dates
    for root, dirs, files in os.walk(input_directory):
        # check if the current directory matches the date pattern
        if date_dir_pattern.match(os.path.basename(root)):
            last_modified_time_file_path = os.path.join(root, "_LAST_MODIFIED_ON_FEC_SOURCE")
            with open(last_modified_time_file_path, "r") as f:
                last_modified_time = f.read().strip()

            for file in files:
                if file.endswith(".fec"):
                    filing_date = os.path.basename(
                        root
                    )  # the date is just the name of the current directory
                    logging.info(f"Processing file: {file}")
                    with open(
                        os.path.join(root, file), "rb"
                    ) as f:  # the file is directly under root
                        with FastFEC() as fastfec:
                            for form_type, line in fastfec.parse(
                                f, include_filing_id=file[:-4]
                            ):
                                # Insert 'fec_filing_date' and '_FEC_SOURCE_LAST_MODIFIED_AT' into 'line'
                                line = OrderedDict(
                                    list(line.items())[:1]
                                    + [("fec_filing_date", filing_date)]
                                    + [("_FEC_SOURCE_LAST_MODIFIED_AT", last_modified_time)]
                                    + list(line.items())[1:]
                                )

                                json_obj = json.dumps(line, cls=DateTimeEncoder)

                                # Ensure output directory exists
                                os.makedirs(JSONL_OUTPUT_DIRECTORY, exist_ok=True)
                                output_file_path = os.path.join(
                                    JSONL_OUTPUT_DIRECTORY, "electronicfiling.jsonl"
                                )

                                with open(output_file_path, "a") as output_file:
                                    output_file.write(json_obj + "\n")


def main():
    process_fec_files(FEC_INPUT_DIRECTORY)


if __name__ == "__main__":
    main()
