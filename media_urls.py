"""Allow current and pre-rename public media without widening the trusted owner."""
PREFIXES=tuple('https://raw.githubusercontent.com/mrgrtglcht/'+name+'/' for name in ('numerology-agent','quantafate-agent'))

def trusted_media_url(url):
    return isinstance(url,str) and url.startswith(PREFIXES)

