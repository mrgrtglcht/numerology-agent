"""One owner-requested correction of an existing Telegram message, never a new send."""
import copy
from datetime import datetime,timezone
from agent import required,request_json
from content_memory import ContentMemory,body,digest

STATE='state/telegram-title-fix-4.json'
OWNER='cloud-telegram-2026-10-28/article'
OLD_TITLE='4 аркан хозяин: твой характер по центру матрицы'
NEW_TITLE='4 аркан — император: твой характер по центру матрицы'

def apply(store):
    state=store.read_state(STATE)
    if state and state.get('stage')=='complete':return
    if state:
        print('::warning::Правка названия Telegram требует сверки; повтор изменения остановлен.')
        return
    memory=ContentMemory(store=store)
    record=memory.data['posts'].get(OWNER)
    if not record:return
    delivery=record.get('deliveries',{}).get('telegram',{})
    if delivery.get('status')!='published' or delivery.get('receipt',{}).get('message_id')!=10:return
    config=copy.deepcopy(record.get('content',{}))
    if config.get('title')!=OLD_TITLE or config.get('arcana_number')!=4:return
    if digest(body(config))!=record['fingerprint']:
        raise ValueError('Сохранённый пост Telegram изменён; правка остановлена.')
    config['title']=NEW_TITLE
    config['caption']=config['caption'].replace('ее часто называют образом хозяина или императора','ее образ — император').replace('внутренний хозяин','внутренний император')
    for slide in config.get('slides',[]):
        if 'body' in slide:slide['body']=config['caption']
    text=config['title']+'\n\n'+config['caption']
    channel=required('TELEGRAM_CHANNEL_ID')
    if channel!='@quantafate':raise ValueError('Правка предназначена только для канала quantafate.')
    state={'stage':'editing','owner':OWNER,'message_id':10,'previous_title':OLD_TITLE,
           'previous_fingerprint':record['fingerprint'],'expected_text_hash':digest(text)}
    store.save_state(STATE,state)
    # No automatic write retry: an unknown result is preserved for review.
    result=request_json('Telegram','https://api.telegram.org/bot'+required('TELEGRAM_BOT_TOKEN')+'/editMessageText',
      {'chat_id':channel,'message_id':10,'text':text,'link_preview_options':{'is_disabled':True}})
    message=result.get('result')
    if not result.get('ok') or not isinstance(message,dict) or message.get('message_id')!=10 or message.get('text')!=text:
        raise ValueError('Telegram не подтвердил исправление; нужна сверка.')
    record.update(content=config,title=NEW_TITLE,body=body(config),fingerprint=digest(body(config)))
    record['editorial_correction']={'previous_title':OLD_TITLE,'reason':'canonical arcana name: emperor',
                                    'edited_at':datetime.now(timezone.utc).isoformat()}
    memory.save()
    store.save_state(STATE,{**state,'stage':'complete','verified':True})
    print('Telegram: название 4 аркана исправлено в сообщении 10.')
