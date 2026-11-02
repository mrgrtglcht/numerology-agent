import unittest
from unittest.mock import Mock, patch
import sync_content_memory as history


class BufferMigrationTests(unittest.TestCase):
    def test_migrated_channels_never_contact_buffer_or_change_memory(self):
        memory=Mock()
        with patch.dict('os.environ',{'TIKTOK_PUBLISHER':'postwire','PINTEREST_PUBLISHER':'upload-post',
                'BUFFER_TIKTOK_CHANNEL_ID':'old-tiktok','BUFFER_PINTEREST_CHANNEL_ID':'old-pin'},clear=True), \
                patch.object(history,'load_key') as key, patch.object(history,'query_buffer') as query:
            self.assertEqual(history.sync(memory=memory),[])
            key.assert_not_called();query.assert_not_called();memory.import_buffer.assert_not_called()

    def test_explicit_legacy_import_still_reads_and_preserves_failure(self):
        with patch.dict('os.environ',{'TIKTOK_PUBLISHER':'postwire','PINTEREST_PUBLISHER':'upload-post'},clear=True), \
                patch.object(history,'load_key',return_value='test'), \
                patch.object(history,'query_buffer',side_effect=RuntimeError('Buffer HTTP 429')) as query:
            with self.assertRaisesRegex(RuntimeError,'429'):
                history.sync(channel_ids=['old-pin'],memory=Mock())
            query.assert_called_once()

    def test_active_buffer_channel_is_still_synced(self):
        memory=Mock()
        with patch.dict('os.environ',{'TIKTOK_PUBLISHER':'postwire','BUFFER_PINTEREST_CHANNEL_ID':'active-pin'},clear=True), \
                patch.object(history,'load_key',return_value='test'), \
                patch.object(history,'query_buffer',side_effect=[{'account':{'organizations':[{'id':'org'}]}},
                    {'posts':{'edges':[],'pageInfo':{'hasNextPage':False}}}]) as query:
            history.sync(memory=memory)
            self.assertEqual(query.call_args.args[2]['input']['filter']['channelIds'],['active-pin'])
            memory.import_buffer.assert_called_once_with([])
