"""Alternate oracle and matrix posts using confirmed queue order, not date parity."""
from datetime import datetime,timezone

def next_format(memory):
    ordered=[]
    for index,post in enumerate(memory.data['posts'].values()):
        delivery=post.get('deliveries',{}).get('tiktok',{})
        if delivery.get('status') not in ('accepted','published'):continue
        receipt=delivery.get('receipt',{})
        if receipt.get('provider')!='postwire' or not receipt.get('run_at'):continue
        ordered.append((datetime.fromisoformat(receipt['run_at'].replace('Z','+00:00')),index,post.get('content',{}).get('type')))
    latest=max(ordered)[2] if ordered else None
    return 'matrix' if latest in (None,'oracle_pick') else 'oracle'

def choice_count(memory):
    count=sum(p.get('content',{}).get('type')=='oracle_pick' and p.get('status')!='rejected' for p in memory.data['posts'].values())
    return (3,5,4,6)[count%4]
