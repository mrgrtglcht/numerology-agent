"""Read Buffer history and update the journal; never creates or resends posts."""
import os
from check_buffer import query_buffer,load_key
from content_memory import ContentMemory

QUERY='''query MemoryPosts($input:PostsInput!,$after:String) {
 posts(first:100,after:$after,input:$input) {
  edges {node {id text status channelService externalLink sentAt assets {id}}}
  pageInfo {hasNextPage endCursor}
 }
}'''

def sync(channel_ids=None,memory=None):
    ids=channel_ids or [os.environ.get(n) for n in ('BUFFER_TIKTOK_CHANNEL_ID','BUFFER_PINTEREST_CHANNEL_ID') if os.environ.get(n)]
    if not ids: raise ValueError('Для чтения истории нужны ID каналов QuantaFate.')
    key=load_key();posts=[]
    orgs=query_buffer(key,'query MemoryOrgs {account {organizations {id}}}')['account']['organizations']
    for org in orgs:
        cursor=None
        for page in range(20):
            result=query_buffer(key,QUERY,{'input':{'organizationId':org['id'],'filter':{'channelIds':ids,
              'status':['draft','error','needs_approval','scheduled','sending','sent']}},'after':cursor})['posts']
            posts.extend(edge['node'] for edge in result['edges'])
            if not result['pageInfo']['hasNextPage']:break
            next_cursor=result['pageInfo']['endCursor']
            if not next_cursor or next_cursor==cursor:raise ValueError('История Buffer получена не полностью.')
            cursor=next_cursor
        else: raise ValueError('История больше лимита чтения; неполный импорт остановлен.')
    (memory or ContentMemory()).import_buffer(posts)
    print(f'История Buffer прочитана: {len(posts)}; опубликовано: {sum(p["status"]=="sent" for p in posts)}. Отправок не было.')
    return posts

if __name__=='__main__':sync()
