"""Offline tutor. A lexical router selects a skill; the custom LM generates its lesson.
Routing and language generation are deliberately separate and disclosed to users.
"""
import re
from fastapi import HTTPException
from .engine import BY_ID,SKILLS,CATALOG
from .basic_responses import basic_reply
from .offline_model.runtime import get_model,ModelUnavailable

ALIASES={
'dynamic':['dynamic','equilibrium','equal rates','reversible','constant concentration'],
'mass':['mass action','expression','coefficients','pure solid','pure liquid','stoichiometric'],
'kc':['kc','constant','reciprocal','reverse reaction','concentration ratio'],
'kp':['kp','delta n','gaseous moles','gas moles','rt','mole difference'],
'shift':['chatelier','pressure','temperature','compression','catalyst','exothermic','endothermic','shift'],
'form':['standard form','quadratic form','degree','coefficient','expand','simplify'],
'factor':['factor','factorisation','factorization','zero root','divide by x','product equal'],
'disc':['discriminant','nature of roots','real roots','equal roots','b squared'],
'formula':['formula','denominator','two a','2a','plus or minus'],
'model':['word problem','rectangle','length','width','consecutive','positive integer','area']}

def route(subject,message,history,attempts):
    eligible={s['id'] for s in SKILLS if s['subject']==subject}
    lower=message.lower();scores={skill:sum(2+len(term.split()) for term in terms if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',lower)) for skill,terms in ALIASES.items() if skill in eligible}
    if 'kp' in scores and re.search(r'(?<!\w)kp(?!\w)',lower):scores['kp']+=5
    if not scores:return None,'explain'
    best=max(scores,key=scores.get)
    if scores[best]>0:skill=best
    elif re.search(r'\b(again|simpler|hint|check|test|explain more)\b',lower) and history:
        previous=next((m['content'] for m in reversed(history) if m['role']=='user'),None)
        if previous:
            result=route(subject,previous,[],[])
            skill=result[0]
        else:skill=None
    elif re.search(r'\b(my|recent|mistakes|wrong|practice)\b',lower):
        recent=[a for a in attempts if a.skill in eligible and not a.correct]
        skill=recent[-1].skill if recent else None
    else:skill=None
    mode='hint' if 'hint' in lower else 'check' if any(word in lower for word in ('test me','quiz me','check me','ask me')) else 'simple' if any(word in lower for word in ('simple','again','easier')) else 'explain'
    return skill,mode

def offline_reply(settings,body,attempts):
    basic=basic_reply(body.message)
    if basic:return basic
    selected_chapter=next((c for c in CATALOG['chapters'] if c['id']==body.chapterId and c['subject']==body.subject and (body.grade is None or c['grade']==body.grade)),None)
    if selected_chapter:
        available=[s for s in SKILLS if s.get('chapterId')==selected_chapter['id']]
        if available and body.subject not in ('Chemistry','Mathematics') or (available and selected_chapter['title'] not in ('Equilibrium','Quadratic Equations')):
            terms=set(re.findall(r'[a-z]+',body.message.lower()))
            ranked=sorted(available,key=lambda s:-len(terms & set(re.findall(r'[a-z]+',s['name'].lower()))))
            return {'reply':'\n\n'.join(s['name']+': '+s['description'] for s in ranked[:3]),'topic':selected_chapter['title'],'engine':'authored_curriculum_response','notice':'Original authored foundation notes. These are not neural output or a complete chapter lesson.'}
        if not available:
            return {'reply':'This chapter is mapped in the curriculum, but a checked lesson and question bank are not available yet. Topics: '+', '.join(t['title'] for t in selected_chapter['topics'])+'.','engine':'scope_message','notice':'Curriculum outline only; not a completed lesson. Official source: '+selected_chapter['source']}
    if not selected_chapter:
        ignored={'what','is','the','how','explain','me','give','simple','please','of','a','to','can','you','in','and','about'}
        def terms(value):return {t[:-1] if t.endswith('s') and len(t)>4 else t for t in re.findall(r'[a-z]+',value.lower())}-ignored
        wanted=terms(body.message)
        candidates=[s for s in SKILLS if s['subject']==body.subject and (body.grade is None or s.get('grade')==body.grade) and s['id'].startswith('g')]
        ranked=sorted(candidates,key=lambda s:-(2*len(wanted & terms(s['name']))+len(wanted & terms(s.get('chapterId','').replace('-',' ')))))
        if ranked and wanted & (terms(ranked[0]['name'])|terms(ranked[0].get('chapterId','').replace('-',' '))):
            found=ranked[0]
            return {'reply':found['name']+': '+found['description'],'engine':'authored_curriculum_response','topic':found['name'],'notice':'Original authored foundation explanation. This is not neural output or complete topic coverage.'}
    if not settings.offline_ai_enabled:
        raise HTTPException(503,'The local tutor is disabled. Guided practice remains available.')
    try:model=get_model(settings.offline_model_dir)
    except ModelUnavailable as exc:raise HTTPException(503,str(exc)) from None
    skill,mode=route(body.subject,body.message,body.history,attempts)
    if skill and body.grade is not None and not any(s['id']==skill and s.get('grade')==body.grade for s in SKILLS):skill=None
    if not skill:
        topics=', '.join(s['name'] for s in SKILLS if s['subject']==body.subject)
        return {'reply':'My tiny local model is limited to the bundled chapter topics. Please name one of these concepts: '+topics+'. I cannot answer general questions reliably.','engine':'scope_message','notice':'Offline scope guidance; this message is authored, not model-generated.','model':model.public_info()}
    result=model.generate(skill,mode)
    title=next(s['name'] for s in SKILLS if s['id']==skill)
    relevant=[a for a in attempts if a.skill==skill]
    evidence=None
    if relevant:
        a=relevant[-1]
        evidence={'question':BY_ID[a.question_id]['prompt'],'correct':bool(a.correct),'hypothesis':a.hypothesis,'note':'A single answer does not establish a cause.'}
    return {'reply':result['text'],'engine':result['engine'],'topic':title,'mode':mode,'evidence':evidence,'notice':('Generated by the custom offline TinyLM and matched to its authored lesson. This is a memorized lesson completion, not general reasoning.' if result['validated'] else 'The model completion did not match its checked lesson; showing an explicitly authored reference instead.'),'model':model.public_info()}
