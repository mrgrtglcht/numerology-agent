import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import os
from telegram_editor import check,history
from editor_recovery import validated

class TelegramEditorTests(unittest.TestCase):
    def test_previous_stock_opening_and_mechanical_ending_are_rejected(self):
        for text in ('продолжаем разговор о центре личной матрицы.','✦ продолжаем знакомство с арканами.',
                     'спокойное практическое наблюдение показывает, что надо отдыхать.'):
            with self.assertRaises(ValueError):check(text)

    def test_repeated_phrases_and_copied_long_passages_are_rejected(self):
        with self.assertRaises(ValueError):
            check('тебе важно находить время для себя. еще тебе важно находить время для отдыха. снова тебе важно находить время для друзей.')
        old='ты берешь на себя все задачи потому что тебе трудно доверить важное дело другому человеку.'
        with self.assertRaises(ValueError):check(old,[old])

    def test_natural_topic_terms_and_canonical_names_are_not_forbidden(self):
        text=('император в центре матрицы любит ясные договоренности. '
              'император в центре матрицы может брать лишнюю ответственность. '
              'император в центре матрицы не обязан решать все один. '
              'попросить помощи бывает сложнее, чем закончить работу самостоятельно.')
        self.assertEqual(check(text),text)

    def test_published_history_excludes_current_article_and_unpublished_drafts(self):
        class Memory:
            data={'posts':{
              'a':{'theme':'telegram_article','content':{'caption':'раньше','editorial_key':'a'},'deliveries':{'telegram':{'status':'published'}}},
              'b':{'theme':'telegram_article','content':{'caption':'черновик','editorial_key':'b'},'deliveries':{}},
              'c':{'theme':'telegram_article','content':{'caption':'текущий','editorial_key':'c'},'deliveries':{'telegram':{'status':'published'}}}}}
        self.assertEqual(history(Memory(),'c'),['раньше'])

    def test_editor_repair_is_saved_and_not_requested_twice(self):
        repair=Mock(return_value={'text':'иногда легче сделать все самому, чем попросить помощи.'})
        def validate(value):
            check(value['text']);return value
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'AUTO_EDITOR_REPAIR':'true'}):
            for _ in range(2):
                result=validated({'text':'продолжаем разговор о матрице.'},validate,Path(tmp),repair)
                self.assertTrue(result['text'].startswith('иногда'))
        repair.assert_called_once()
