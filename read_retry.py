"""Bounded retries for explicitly read-only network operations, never sends."""
import time
import urllib.error


def read_retry(operation):
    for attempt in range(3):
        try:return operation()
        except urllib.error.HTTPError as error:
            if error.code not in (408,429,500,502,503,504) or attempt==2:raise
        except (urllib.error.URLError,TimeoutError,ConnectionError):
            if attempt==2:raise
        time.sleep(2**attempt)
