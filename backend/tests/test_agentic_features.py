import unittest
from app.api.agentic_core import CAREER_DOCS, retrieve, tool_catalog

class AgenticFeatureTests(unittest.TestCase):
    def test_rag_retrieves_relevant_document(self):
        results = retrieve('React TypeScript frontend developer', 4)
        self.assertTrue(results)
        titles = ' '.join(x['title'].lower() for x in results)
        self.assertTrue('frontend' in titles or 'software' in titles or 'career' in titles)

    def test_tool_catalog_has_mcp_tools(self):
        names = {x['name'] for x in tool_catalog()}
        self.assertIn('get_student_profile', names)
        self.assertIn('search_career_knowledge', names)
        self.assertIn('analyze_skill_gap', names)

    def test_local_knowledge_base_exists(self):
        self.assertGreaterEqual(len(CAREER_DOCS), 5)
        self.assertTrue(all(d.get('title') and d.get('text') for d in CAREER_DOCS))

if __name__ == '__main__':
    unittest.main()
