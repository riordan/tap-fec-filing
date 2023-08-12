# Proof-of-Concept of FEC parser Meltano Tap
This is a dumb proof of concept, but it gets the job done. It downloads the zipfiles from S3, uses fastfec to parse them, then puts a big old jsonl out at the end.

JSONL/dictionary is how Singer SDK expects data outputs so this may be sufficient but 🤷.


## Improvements to make
1. [ ] Include print filings along with electronic
2. [ ] Logging with timestamps
3. [ ] Logging outputs include date when processing a .fec
4. [ ] Logging outputs include a summary when done processing a .fec
5. [ ] Parallel processing within a given date (e.g. keep ordered using an output queue)
6. [ ] Write to tempfiles rather than hardcoded local directories
