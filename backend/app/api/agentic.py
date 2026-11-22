"""Agentic AI lab: transparent agent runs, tool registry, local RAG, memory, and MCP-compatible tools endpoint.

This is a lightweight, dependency-minimal MCP Streamable HTTP-compatible endpoint for initialize,
notifications/initialized, tools/list and tools/call. It exposes only safe, read-only demo tools.
"""
from __future__ import annotations
import json, time
from collections import defaultdict, deque
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.deps import current_user
from app.db.session import get_db
from app.models import Profile, CareerRecommendation, LearningTask, ResumeAnalysis
from app.agents.catalog import ROLES
from app.agents.skill_gap_agent import candidate_skills, skill_gap_report
from app.agents.resume_agent import parse_resume, score_resume
from app.api.agentic_core import CAREER_DOCS, retrieve, tool_catalog

router = APIRouter()
# In-process short-term memory; cleared on backend restart. User IDs isolate each history.
_STM: dict[int, deque] = defaultdict(lambda: deque(maxlen=12))
_TASK_MEMORY: dict[int, dict] = defaultdict(dict)

class AgentRunIn(BaseModel):
    task: str = Field(min_length=3, max_length=2000)
    target_role: str = ""

class RagQueryIn(BaseModel):
    question: str = Field(min_length=3, max_length=1500)

class ToolCallIn(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)

class MemoryIn(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=1000)


def profile_data(u, db):
    p = db.scalar(select(Profile).where(Profile.user_id == u.id))
    if not p: return {"career_goal":"", "degree":"", "branch":"", "skills":[], "projects":[], "interests":[]}
    return {"career_goal":p.career_goal or "", "degree":p.degree or "", "branch":p.branch or "", "college":p.college or "", "cgpa":p.cgpa, "skills":p.skills or [], "projects":p.projects or [], "certifications":p.certifications or [], "interests":p.interests or []}

def _skill_names(profile):
    out=[]
    for item in profile.get('skills',[]):
        if isinstance(item,str): out.append(item)
        elif isinstance(item,dict) and item.get('name'): out.append(item['name'])
    return out

def call_tool(name, args, u, db):
    profile=profile_data(u,db)
    if name == 'get_student_profile':
        return {"career_goal":profile.get('career_goal'),"degree":profile.get('degree'),"branch":profile.get('branch'),"skills":_skill_names(profile),"interests":profile.get('interests',[]),"projects_count":len(profile.get('projects',[]))}
    if name == 'list_career_roles':
        return [{"role":str(k),"details":v} for k,v in list(ROLES.items())[:50]]
    if name == 'get_learning_tasks':
        rows=db.scalars(select(LearningTask).where(LearningTask.user_id==u.id)).all()
        return [{"id":r.id,"task":r.task,"priority":r.priority,"category":r.category,"completed":r.completed} for r in rows]
    if name == 'search_career_knowledge':
        query=str(args.get('query','')).strip()
        if len(query)<2: raise HTTPException(400,'Provide a search query.')
        return retrieve(query,5)
    if name == 'analyze_skill_gap':
        role=str(args.get('target_role','')).strip()
        if not role: raise HTTPException(400,'target_role is required')
        return skill_gap_report(profile,None,None,role)
    raise HTTPException(404, f'Unknown tool: {name}')

@router.get('/agentic/status')
def agentic_status(u=Depends(current_user)):
    return {"agents":["Resume Agent","Skill Gap Agent","Coding Analytics Agent","Job Matching Agent","Interview Agent","Career Intelligence Agent","Learning Roadmap Agent"],"tools":tool_catalog(),"rag":{"enabled":True,"method":"TF-IDF local retrieval","documents":len(CAREER_DOCS)},"memory":{"short_term":"in-process per-user conversation/run history","task_memory":"per-user key-value memory; in-process"},"mcp":{"endpoint":"/mcp","transport":"HTTP JSON-RPC tool endpoint","tools":len(tool_catalog()),"auth":"Bearer token required for application tool calls"}}

@router.post('/agentic/run')
def agentic_run(x:AgentRunIn,u=Depends(current_user),db:Session=Depends(get_db)):
    task=x.task.strip(); prof=profile_data(u,db); target=x.target_role.strip() or prof.get('career_goal') or 'Software Developer'
    trace=[]
    trace.append({"step":1,"agent":"Career Intelligence Agent","action":"Read student profile","status":"completed","result":{"skills":_skill_names(prof),"target_role":target}})
    gap=skill_gap_report(prof,None,None,target)
    trace.append({"step":2,"agent":"Skill Gap Agent","action":"Compare profile against role requirements","status":"completed","result":gap})
    retrieved=retrieve(f'{task} {target} skills roadmap',3)
    trace.append({"step":3,"agent":"RAG Retrieval Tool","action":"Retrieve relevant career knowledge","status":"completed","result":retrieved})
    missing=[g.get('label', g.get('skill','')) for g in gap.get('gaps',[]) if isinstance(g,dict)] if isinstance(gap,dict) else []
    recommendations=[]
    for doc in retrieved[:2]: recommendations.append(doc['text'])
    if missing: recommendations.append('Prioritize these skills next: '+', '.join(missing[:6])+'.')
    recommendations.append('Build one small project for the target role, document your contribution, and review progress weekly.')
    answer=' '.join(dict.fromkeys(recommendations))
    run={"id":int(time.time()*1000),"task":task,"target_role":target,"answer":answer,"trace":trace,"tools_used":["get_student_profile","analyze_skill_gap","search_career_knowledge"],"created_at":time.time()}
    _STM[u.id].append({"role":"user","content":task,"at":time.time()}); _STM[u.id].append({"role":"assistant","content":answer,"at":time.time()})
    _TASK_MEMORY[u.id]['last_target_role']=target; _TASK_MEMORY[u.id]['last_task']=task
    return run

@router.post('/agentic/rag/query')
def rag_query(x:RagQueryIn,u=Depends(current_user)):
    docs=retrieve(x.question,4)
    context=' '.join(d['text'] for d in docs)
    answer=context + (' Suggested next step: identify one skill from the retrieved guidance and practice it through a small project.' if docs else '')
    return {"question":x.question,"answer":answer,"sources":[{"title":d['title'],"score":d['score']} for d in docs],"retrieval":"TF-IDF over bundled local career documents","llm_used":False}

@router.get('/agentic/memory')
def get_memory(u=Depends(current_user)):
    return {"short_term":list(_STM[u.id]),"task_memory":_TASK_MEMORY[u.id],"note":"Short-term and task memory are currently in-process; they reset when the backend restarts."}

@router.post('/agentic/memory')
def set_memory(x:MemoryIn,u=Depends(current_user)):
    _TASK_MEMORY[u.id][x.key]=x.value
    return {"ok":True,"task_memory":_TASK_MEMORY[u.id]}

@router.delete('/agentic/memory')
def clear_memory(u=Depends(current_user)):
    _STM[u.id].clear(); _TASK_MEMORY[u.id].clear(); return {"ok":True}

@router.post('/agentic/tools/call')
def tool_call(x:ToolCallIn,u=Depends(current_user),db:Session=Depends(get_db)):
    allowed={t['name'] for t in tool_catalog()}
    if x.tool not in allowed: raise HTTPException(404,'Tool not found')
    return {"tool":x.tool,"result":call_tool(x.tool,x.arguments,u,db)}

# MCP Streamable HTTP-style endpoint. Supports initialize, tools/list and tools/call.
# It intentionally exposes only the allow-listed read-only tools above.
@router.post('/mcp')
async def mcp_endpoint(request: Request, u=Depends(current_user), db:Session=Depends(get_db)):
    try: body=await request.json()
    except Exception: raise HTTPException(400,'Expected JSON-RPC request body')
    method=body.get('method'); params=body.get('params') or {}; rid=body.get('id')
    if method == 'notifications/initialized': return {"jsonrpc":"2.0","result":{}}
    if method == 'initialize':
        result={"protocolVersion":params.get('protocolVersion','2025-03-26'),"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":"careerpilot-mcp-tools","version":"1.0.0"}}
    elif method == 'ping': result={}
    elif method == 'tools/list': result={"tools":tool_catalog()}
    elif method == 'tools/call':
        name=params.get('name',''); args=params.get('arguments') or {}
        try:
            val=call_tool(name,args,u,db)
            result={"content":[{"type":"text","text":json.dumps(val,ensure_ascii=False,default=str)}],"structuredContent":{"result":val},"isError":False}
        except HTTPException as e:
            result={"content":[{"type":"text","text":str(e.detail)}],"isError":True}
    else:
        return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f'Method not found: {method}'}}
    return {"jsonrpc":"2.0","id":rid,"result":result}
