"""Pure helpers for Agentic AI tools and local TF-IDF retrieval."""
import re

CAREER_DOCS = [
 {"title":"Software Developer", "text":"Software developer roles commonly require programming, data structures and algorithms, object-oriented programming, Git, testing, APIs, databases, debugging and project experience."},
 {"title":"Data Analyst", "text":"Data analyst roles commonly require SQL, spreadsheets, Python, statistics, data cleaning, visualization, dashboards and communicating insights."},
 {"title":"Machine Learning Engineer", "text":"Machine learning roles commonly require Python, statistics, linear algebra, data preparation, model evaluation, scikit-learn, deployment and software engineering."},
 {"title":"Cybersecurity Analyst", "text":"Cybersecurity roles commonly require networking, Linux, security fundamentals, logs, vulnerability assessment, incident response, scripting and risk awareness."},
 {"title":"Cloud Engineer", "text":"Cloud engineering roles commonly require Linux, networking, scripting, cloud services, containers, CI/CD, monitoring, security and infrastructure automation."},
 {"title":"Frontend Developer", "text":"Frontend developers commonly need HTML, CSS, JavaScript, TypeScript, React, accessibility, responsive design, API integration and testing."},
 {"title":"Backend Developer", "text":"Backend developers commonly need Python or another server language, REST APIs, authentication, databases, SQL, validation, testing, logging and deployment."},
 {"title":"Resume guidance", "text":"A strong resume should be accurate, concise, tailored to the role, and include education, skills, projects, experience and measurable outcomes only when truthful. Avoid invented claims."},
 {"title":"Interview preparation", "text":"Interview preparation includes explaining projects clearly, practicing data structures, reviewing core concepts, using STAR for behavioral questions and asking clarifying questions."},
 {"title":"Learning roadmap", "text":"A useful learning roadmap prioritizes foundational skills first, then role-specific skills, hands-on projects, testing, documentation and interview practice. Review progress regularly."},
]

def tool_catalog():
    return [
      {"name":"get_student_profile","description":"Return the authenticated student's saved career profile summary.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
      {"name":"list_career_roles","description":"List supported career roles and required skills.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
      {"name":"get_learning_tasks","description":"Return the student's saved learning roadmap tasks.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
      {"name":"search_career_knowledge","description":"Retrieve relevant career guidance documents from the local RAG knowledge base.","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"],"additionalProperties":False}},
      {"name":"analyze_skill_gap","description":"Analyze the student's skill gap for a career role.","inputSchema":{"type":"object","properties":{"target_role":{"type":"string"}},"required":["target_role"],"additionalProperties":False}},
    ]


def retrieve(query: str, top_k=4):
    """Local TF-IDF retrieval (RAG retrieval stage) with deterministic fallback."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        texts=[d['title']+' '+d['text'] for d in CAREER_DOCS]
        vect=TfidfVectorizer(stop_words='english', ngram_range=(1,2))
        matrix=vect.fit_transform(texts+[query])
        sims=cosine_similarity(matrix[-1],matrix[:-1]).ravel()
        ids=sorted(range(len(sims)),key=lambda i:float(sims[i]),reverse=True)[:top_k]
        result=[]
        for i in ids:
            if sims[i] > 0: result.append({"title":CAREER_DOCS[i]['title'],"text":CAREER_DOCS[i]['text'],"score":round(float(sims[i]),3)})
        return result or [{"title":"General career guidance","text":"Add a target role or specific skills to your question for more relevant guidance. Build foundations, complete projects, and keep your resume truthful.","score":0.0}]
    except Exception:
        terms=set(re.findall(r'[a-z0-9]+',query.lower()))
        scored=[]
        for d in CAREER_DOCS:
            words=set(re.findall(r'[a-z0-9]+',(d['title']+' '+d['text']).lower()))
            score=len(terms & words)/max(1,len(terms))
            if score: scored.append({"title":d['title'],"text":d['text'],"score":round(score,3)})
        return sorted(scored,key=lambda x:x['score'],reverse=True)[:top_k] or [{"title":"General guidance","text":"Build foundational skills, create projects, and practice interviews.","score":0.0}]

