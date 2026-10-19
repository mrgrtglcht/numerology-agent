import copy
import json
import unittest
from datetime import date

import arcana_series as series
from matrix_rules import ARCANA,THEMES,allowed,domains,points,series_plan,valid_tail,reduce22
from carousel_auto import tail_numbers

class SeriesTests(unittest.TestCase):
    def test_all_32_points_match_existing_bot_reference(self):
        expected={'A':22,'C':4,'E':6,'G':5,'I':10,'I1':11,'I2':21,
          'B':8,'D':10,'F':11,'H':9,'A1':9,'A2':5,'C1':18,'C2':14,'E1':22,'E2':16,
          'G1':20,'G2':15,'B1':8,'B2':18,'D1':3,'D2':20,'F1':5,'F2':21,'H1':10,'H2':19,
          'F3':4,'FL':19,'FR':20,'A3':15,'C3':6}
        self.assertEqual(points(22,4,6),expected)

    def test_centre_exclusions_and_month_position(self):
        self.assertEqual([n for n in range(1,23) if n not in allowed('I')],[1,2,15,17,19,21])
        self.assertEqual(allowed('C'),list(range(1,13)))
        self.assertEqual(allowed('FR'),list(range(3,23)))
        self.assertEqual(allowed('G2'),[3,6,9,12,15,18,21])

    def test_every_allowed_position_value_has_a_real_birth_witness(self):
        for key,values in domains()['positions'].items():
            for value in values:
                d=date.fromisoformat(domains()['witnesses'][key][value])
                p=points(reduce22(d.day),d.month,reduce22(sum(map(int,str(d.year)))))
                self.assertEqual(p[key],value)

    def test_only_26_reachable_tails_are_accepted(self):
        self.assertEqual(len(domains()['tails']),26)
        self.assertTrue(valid_tail([15,5,8]))
        with self.assertRaises(ValueError): tail_numbers('1–2–3')

    def test_parts_cover_exact_domain_without_repeats(self):
        for theme in THEMES:
            plan=series_plan(theme)
            all_values=[n for p in plan['parts'] for n in p['arcana']]
            self.assertEqual(all_values,allowed(THEMES[theme]['position']))
            self.assertEqual(len(all_values),len(set(all_values)))
            self.assertTrue(all(len(p['arcana'])<=4 for p in plan['parts']))
        self.assertEqual(series_plan('profession')['total_parts'],5)
        self.assertEqual(series_plan('centre')['total_parts'],4)
        self.assertEqual(series_plan('facts')['total_parts'],6)

    def fixture(self):
        return {'selected':[{'id':'b1','focus':[.5,.5],'reason':'готический фон'}],
                'caption':'пример тематической серии.',
                'entries':[{'number':n,'paragraphs':['первый конкретный абзац.','второй конкретный абзац.']} for n in allowed('FR')]}

    def test_impossible_or_missing_arcana_are_rejected_before_render(self):
        plan=series_plan('profession')
        for change in ('impossible','missing','duplicate'):
            r=self.fixture()
            if change=='impossible': r['entries'][0]['number']=1
            elif change=='missing': r['entries'].pop()
            else: r['entries'][0]['number']=r['entries'][1]['number']
            with self.assertRaises(ValueError): series.validate_response(r,plan,[{'id':'b1'}])

    def test_composition_has_correct_position_cards_and_bot_final(self):
        plan=series_plan('profession')
        r=series.validate_response(self.fixture(),plan,[{'id':'b1'}])
        c=series.compose('profession',1,plan,r,[{'file':'b1.jpg','focus':[.5,.5]}])
        self.assertEqual(c['position'],'FR')
        self.assertEqual(c['example_points']['FR'],3)
        self.assertEqual([s['arcana_number'] for s in c['slides'] if s['layout']=='arcana'],[3,4,5,6])
        self.assertEqual([s['layout'] for s in c['slides']],['series_cover','location','arcana','arcana','arcana','arcana','bot'])
        c2=series.compose('profession',2,plan,r,[{'file':'b1.jpg','focus':[.5,.5]}])
        self.assertEqual(c2['part_arcana'],[7,8,9,10])
        self.assertEqual(c2['example_points']['FR'],7)

    def test_source_card_numbering_is_explicit(self):
        self.assertEqual(ARCANA[8],'справедливость')
        self.assertEqual(ARCANA[11],'сила')
        self.assertEqual(ARCANA[22],'шут')

    def test_random_theme_is_stable_for_resume(self):
        self.assertEqual(series.choose_theme('random','series-123'),series.choose_theme('random','series-123'))
        self.assertIn(series.choose_theme('random','series-123'),THEMES)

    def test_facts_do_not_invent_a_matrix_position(self):
        plan=series_plan('facts'); r=self.fixture()
        r['entries']=[{'number':n,'paragraphs':['образ для размышления.','другая грань символа.']} for n in range(1,23)]
        r=series.validate_response(r,plan,[{'id':'b1'}])
        c=series.compose('facts',1,plan,r,[{'file':'b1.jpg','focus':[.5,.5]}])
        self.assertIsNone(c['position'])
        self.assertNotIn('location',[s['layout'] for s in c['slides']])

