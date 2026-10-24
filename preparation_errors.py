"""Safe diagnostics and recoverable preparation classification; no send retries."""
import urllib.error
from urllib.parse import urlsplit
from source_library import SourceUnavailable


def temporary(error):
    return isinstance(error,(SourceUnavailable,urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ConnectionError))


def diagnostic(error):
    result={'type':type(error).__name__,'retryable':temporary(error)}
    status=getattr(error,'code',None) or getattr(error,'status',None)
    if status:result['http_status']=status
    url=getattr(error,'url',None)
    if isinstance(url,str):
        parsed=urlsplit(url);result['host']=parsed.hostname
        # Never log query strings, authorization headers or response bodies.
    return result
