"""Offline dataset gate checks."""
import unittest
from audit_training_corpus import audit

def source():
    return {"title":"Real source", "license":"Reviewed permission",
            "review_status":"reviewed", "sha256":"a"*64}

def record(n, sid):
    return {"id":str(n), "text":f"Distinct question {n}", "source_id":sid,
            "case_id":str(n), "reviewed":True, "reviewer":"Reviewer",
            "labels":{"topic":"genetics"},
            "evidence":[{"source_id":sid,"passage_id":f"passage-{n}"}]}

class GateTests(unittest.TestCase):
    def test_pass_structure(self):
        self.assertTrue(audit([record(1,"s1"),record(2,"s2")],
                              {"s1":source(),"s2":source()})["ready_for_manual_training_review"])
    def test_unreviewed_fails(self):
        r1=record(1,"s1");r1["reviewed"]=False
        self.assertFalse(audit([r1,record(2,"s2")],
                               {"s1":source(),"s2":source()})["ready_for_manual_training_review"])
    def test_missing_evidence_fails(self):
        r1=record(1,"s1");r1["evidence"]=[]
        self.assertFalse(audit([r1,record(2,"s2")],
                               {"s1":source(),"s2":source()})["ready_for_manual_training_review"])
if __name__=="__main__": unittest.main()
