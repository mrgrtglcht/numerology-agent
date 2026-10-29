import os
import unittest
from datetime import datetime
from unittest.mock import patch
from cloud_agent import scheduled_targets, ZONE

class HourlyQueueTests(unittest.TestCase):
    def test_hourly_checks_tiktok_without_early_telegram_post(self):
        with patch.dict(os.environ,{'ENABLE_TIKTOK_CLOUD':'true','ENABLE_TELEGRAM_CLOUD':'true'}):
            self.assertEqual(scheduled_targets(datetime(2026,10,29,12,17,tzinfo=ZONE),'17 * * * *'),['tiktok'])

    def test_hourly_catches_due_telegram_and_saved_preparation(self):
        with patch.dict(os.environ,{'ENABLE_TIKTOK_CLOUD':'true','ENABLE_TELEGRAM_CLOUD':'true'}):
            self.assertEqual(scheduled_targets(datetime(2026,10,28,19,17,tzinfo=ZONE),'17 * * * *'),['tiktok','telegram'])
            self.assertEqual(scheduled_targets(datetime(2026,10,29,12,17,tzinfo=ZONE),'17 * * * *',{'stage':'preparation_failed'}),['tiktok','telegram'])
            self.assertEqual(scheduled_targets(datetime(2026,10,29,12,17,tzinfo=ZONE),'17 * * * *',{'stage':'needs_review'}),['tiktok'])

    def test_delayed_old_events_and_disabled_targets(self):
        now=datetime(2026,10,29,12,17,tzinfo=ZONE)
        with patch.dict(os.environ,{'ENABLE_TIKTOK_CLOUD':'true','ENABLE_TELEGRAM_CLOUD':'true'}):
            self.assertEqual(scheduled_targets(now,'17 5,11 * * *'),['tiktok'])
            self.assertEqual(scheduled_targets(now,None),[])
        with patch.dict(os.environ,{'ENABLE_TIKTOK_CLOUD':'false','ENABLE_TELEGRAM_CLOUD':'false'}):
            self.assertEqual(scheduled_targets(now,'17 * * * *'),[])
