import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import compare_presence_models as compare

class PresenceModelComparisonTests(unittest.TestCase):
    def test_paired_round_folds_hold_both_conditions_together(self):
        rows=[]
        for session in (1,2):
            for round_number in (1,2):
                for label in (0,1):
                    rows.append({'session':session,'round':round_number,'label':label})
        folds=compare.folds_for(rows,'paired_round')
        self.assertEqual(len(folds),4)
        for _, test, train in folds:
            self.assertEqual(len(test),2)
            self.assertEqual({r['label'] for r in test},{0,1})
            test_group={(r['session'],r['round']) for r in test}
            train_groups={(r['session'],r['round']) for r in train}
            self.assertTrue(test_group.isdisjoint(train_groups))

    def test_session_folds_hold_out_entire_session(self):
        rows=[{'session':s,'round':r,'label':y} for s in (1,2) for r in (1,2) for y in (0,1)]
        for name,test,train in compare.folds_for(rows,'session'):
            held=int(name.rsplit('_',1)[1])
            self.assertEqual({r['session'] for r in test},{held})
            self.assertNotIn(held,{r['session'] for r in train})

if __name__=='__main__': unittest.main()
