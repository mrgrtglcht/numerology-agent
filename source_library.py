"""Bounded, dated evidence excerpts; never invented facts or copied instructions."""
import copy
import hashlib
import json
from pathlib import Path

PATH=Path(__file__).resolve().parent/'assets/research/library.json'


class SourceUnavailable(OSError):
    def __init__(self,url,error):
        self.url=url;self.status=getattr(error,'code',None)
        super().__init__('Research source temporarily unavailable; preparation saved.')


def lookup(url,group):
    from web_research import safe
    if not safe(url):raise ValueError('Unapproved research URL.')
    if not PATH.exists():return None
    library=json.loads(PATH.read_text(encoding='utf-8'))
    if library.get('version')!=1:raise ValueError('Unknown evidence library version.')
    record=copy.deepcopy(library['records'].get(url))
    if record is None:return None
    expected=record.pop('record_sha256',None)
    actual=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if expected!=actual or record['url']!=url:raise ValueError('Evidence library checksum mismatch.')
    text=record['excerpts'].get(group)
    if not text:return None
    if not record.get('checked_at') or len(text)>850:raise ValueError('Invalid evidence excerpt.')
    return {**{k:record[k] for k in ('url','title','sha256','checked_at')},
      'excerpt':text,'links':record.get('links',[]),'evidence_mode':'verified_library'}
