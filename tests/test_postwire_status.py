import copy
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import postwire as p
from agent import SafeError

class Memory:
    def __init__(self,status='accepted'):
        self.data={'posts':{'part':{'deliveries':{'tiktok':{'status':status,'receipt':{'provider':'postwire','id':'schedule-123'}}}}}}
        self.writes=[]
    def delivery(self,owner,platform,status,receipt):
        self.writes.append((status,receipt))
        self.data['posts'][owner]['deliveries'][platform]={'status':status,'receipt':receipt}

def completed(status='processing',ok=True):
    return {'scheduled':{'status':'done','results':[{'platform':'tiktok','ok':ok,'status':status,'id':'p_pub_url~v2.123'}]}}

class PostWireStatusTests(unittest.TestCase):
    def test_actual_done_worker_checks_tiktok_before_marking_published(self):
        m=Memory()
        with patch.object(p,'api',side_effect=[completed(),{'platform':'tiktok','id':'p_pub_url~v2.123','status':'publish_complete'}]) as api:
            p.sync(m)
        self.assertEqual(m.writes[0][0],'published')
        self.assertEqual(api.call_args_list[1].args[0],'/api/post/status?'+urlencode({'platform':'tiktok','id':'p_pub_url~v2.123'}))
        self.assertTrue(all(len(c.args)==1 and not c.kwargs for c in api.call_args_list))

    def test_processing_remains_accepted_and_next_poll_can_finish(self):
        m=Memory()
        with patch.object(p,'api',side_effect=[completed(),{'platform':'tiktok','status':'processing'},completed(),{'platform':'tiktok','status':'publish_complete'}]) as api:
            p.sync(m)
            self.assertEqual(m.writes[-1][0],'accepted')
            p.sync(m)
        self.assertEqual(m.writes[-1][0],'published')
        self.assertEqual(api.call_count,4)

    def test_queued_post_is_left_alone(self):
        m=Memory()
        with patch.object(p,'api',return_value={'scheduled':{'status':'queued'}}) as api:p.sync(m)
        self.assertEqual(m.writes,[])
        self.assertEqual(api.call_count,1)

    def test_published_confirmation_does_not_poll_or_resend(self):
        with patch.object(p,'api') as api:p.sync(Memory('published'))
        api.assert_not_called()

    def test_worker_done_does_not_hide_failure_or_missing_proof(self):
        for response in [completed(ok=False),{'scheduled':{'status':'done'}}, {'scheduled':{'status':'failed'}}]:
            m=Memory()
            with patch.object(p,'api',return_value=response) as api:
                with self.assertRaises(SafeError):p.sync(m)
            self.assertEqual(m.writes,[])
            self.assertEqual(api.call_count,1)

    def test_network_failure_or_unknown_status_cannot_become_published(self):
        for status in ['failed','unknown','send_to_user_inbox']:
            m=Memory()
            with patch.object(p,'api',side_effect=[completed(),{'platform':'tiktok','status':status}]):
                with self.assertRaises(SafeError):p.sync(m)
            self.assertEqual(m.writes,[])

    def test_wrong_platform_or_identity_stops_without_send(self):
        for outcome in [{'platform':'instagram','status':'publish_complete'}, {'platform':'tiktok','id':'other','status':'publish_complete'}]:
            m=Memory()
            with patch.object(p,'api',side_effect=[completed(),outcome]):
                with self.assertRaises(SafeError):p.sync(m)
            self.assertEqual(m.writes,[])

    def test_result_does_not_copy_private_account_fields(self):
        response=completed(status='publish_complete')
        response['scheduled']['results'][0]['account']={'email':'private@example.test'}
        m=Memory()
        with patch.object(p,'api',return_value=response):p.sync(m)
        self.assertNotIn('account',m.writes[0][1]['result'])

if __name__=='__main__':unittest.main()

