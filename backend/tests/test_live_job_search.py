import unittest
from app.services.job_search import (_normalise_remotive, _normalise_himalayas, _normalise_remoteok, _normalise_jobsforce, _role_matches, _work_mode_matches)

class LiveJobSearchNormalisationTests(unittest.TestCase):
    def test_remotive_keeps_attribution_and_link(self):
        job = _normalise_remotive({"id": 9, "title": "Backend Engineer", "company_name": "Remote Co",
            "candidate_required_location": "Worldwide", "url": "https://remotive.com/job/9",
            "description": "<p>Python API</p>", "salary": "$70k"})
        self.assertEqual(job["source"], "Remotive")
        self.assertTrue(job["remote"])
        self.assertEqual(job["url"], "https://remotive.com/job/9")
        self.assertIn("Python API", job["description"])


    def test_himalayas_normalisation(self):
        job = _normalise_himalayas({"guid": "abc", "title": "Python Developer",
            "companyName": "Example", "locationRestrictions": ["IN"],
            "applicationLink": "https://example.com/apply", "description": "<p>Python</p>"})
        self.assertEqual(job["source"], "Himalayas")
        self.assertEqual(job["location"], "India")
        self.assertEqual(job["url"], "https://example.com/apply")

    def test_remoteok_normalisation(self):
        job = _normalise_remoteok({"id": "123", "position": "Backend Developer",
            "company": "Example", "url": "https://remoteok.com/123", "tags": ["python"]})
        self.assertEqual(job["source"], "Remote OK")
        self.assertEqual(job["title"], "Backend Developer")

    def test_jobsforce_work_modes_and_company_attribution(self):
        job = _normalise_jobsforce({"id": "x1", "title": "Python Developer",
            "hiring": {"type": "agency", "display": "Confidential client"},
            "location": {"city": "Pune", "state": "Maharashtra", "country": "India", "remote": False},
            "work_mode": "hybrid", "url": "https://jobsforceindia.com/jobs/x1"})
        self.assertEqual(job["source"], "JobsForce India")
        self.assertEqual(job["work_mode"], "hybrid")
        self.assertIn("Confidential", job["company"])


    def test_work_mode_filter_is_strict(self):
        remote = {"source": "Remotive", "remote": True, "work_mode": "remote"}
        hybrid = {"source": "JobsForce India", "remote": False, "work_mode": "hybrid"}
        office = {"source": "JobsForce India", "remote": False, "work_mode": "onsite"}
        unknown = {"source": "Arbeitnow", "remote": False, "work_mode": "Not specified"}
        self.assertTrue(_work_mode_matches(remote, "remote"))
        self.assertFalse(_work_mode_matches(remote, "hybrid"))
        self.assertTrue(_work_mode_matches(hybrid, "hybrid"))
        self.assertFalse(_work_mode_matches(hybrid, "onsite"))
        self.assertTrue(_work_mode_matches(office, "onsite"))
        self.assertFalse(_work_mode_matches(unknown, "onsite"))
        self.assertTrue(_work_mode_matches(unknown, "all"))

    def test_domain_filter_separates_roles(self):
        self.assertTrue(_role_matches("Machine Learning Engineer", "AI/ML Engineer"))
        self.assertFalse(_role_matches("Frontend Developer", "Backend Developer"))

if __name__ == "__main__": unittest.main()
