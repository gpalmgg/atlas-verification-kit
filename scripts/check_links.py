#!/usr/bin/env python3
"""Concurrent link-health sweep over every community URL in the DB.
Writes research/link-health.json: {url: status} where status is an HTTP code or 'dead'.
403/406/429 are treated as LIKELY-ALIVE (bot-blocks), not dead — we only flag 000/404/410/5xx as broken.
"""
import json, os, concurrent.futures, urllib.request, ssl
ROOT=os.path.join(os.path.dirname(__file__),'..')
rows=json.load(open(os.path.join(ROOT,'communities-database.json')))['entries']
urls=sorted({(r.get('url') or '').strip() for r in rows if (r.get('url') or '').strip()})
# verified TLS on purpose: an expired/invalid cert is itself a broken-link signal worth surfacing
ctx=ssl.create_default_context()
def check(u):
    try:
        url=u if u.startswith('http') else 'https://'+u
        req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'Mozilla/5.0 (compatible; linkcheck/1.0)'})
        with urllib.request.urlopen(req,timeout=10,context=ctx) as r: return u,r.status
    except urllib.error.HTTPError as e:
        # some servers reject HEAD; retry GET on 405
        if e.code in (405,403):
            try:
                req2=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
                with urllib.request.urlopen(req2,timeout=10,context=ctx) as r: return u,r.status
            except Exception: return u,e.code
        return u,e.code
    except Exception: return u,'dead'
res={}
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
    for u,st in ex.map(check,urls): res[u]=st
BROKEN={'dead',404,410,500,502,503,504,000,'000'}
broken={u:s for u,s in res.items() if s in BROKEN or s=='dead' or (isinstance(s,int) and s>=500)}
out=os.path.join(ROOT,'research','link-health.json')
json.dump({'checked':len(res),'broken':len(broken),'status':res,'broken_urls':broken},
          open(out,'w'),ensure_ascii=False,indent=0)
print(f"checked {len(res)} urls — {len(broken)} broken (000/404/410/5xx). wrote {out}")
