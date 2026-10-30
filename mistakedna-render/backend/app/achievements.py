"""Subject badges derived only from stored attempts. No synthetic progress."""
from .engine import BY_ID

def subject_stats(history,subject):
    rows=[a for a in history if BY_ID.get(a.question_id,{}).get('subject')==subject]
    skills={};seen={};recovered=set();improved=set()
    for a in rows:
        record=skills.setdefault(a.skill,{'total':0,'correct':0,'latest':.3,'missed_ids':set()})
        record['total']+=1;record['correct']+=bool(a.correct);record['latest']=a.mastery_after
        if not a.correct:record['missed_ids'].add(a.question_id)
        elif record['missed_ids']:
            recovered.add(a.skill)
            if a.question_id not in record['missed_ids']:improved.add(a.skill)
    return {'attempts':len(rows),'correct':sum(bool(a.correct) for a in rows),'sessions':len({a.session_id for a in rows}),'skills':len(skills),'mastered':sum(s['total']>=3 and s['correct']>=3 and s['latest']>=.8 for s in skills.values()),'recovered':len(recovered),'fresh_improvement':len(improved)}

def achievements(history):
    result=[]
    sets={
    'Mathematics':[
      ('math_first','First Equation','Record your first Mathematics answer.','attempts',1),
      ('math_precision','Precision Builder','Answer 10 Mathematics questions correctly.','correct',10),
      ('math_connections','Pattern Finder','Attempt 5 distinct Mathematics skills.','skills',5),
      ('math_return','Second Approach','Answer correctly in a Mathematics skill after a recorded error.','recovered',1),
      ('math_transfer','Fresh Solution','After an error, answer a different question in that Mathematics skill correctly.','fresh_improvement',1),
      ('math_mastery','Proof of Progress','Reach an 80% mastery estimate with at least 3 correct attempts in each of 3 Mathematics skills.','mastered',3),
    ],
    'Chemistry':[
      ('chem_first','First Reaction','Record your first Chemistry answer.','attempts',1),
      ('chem_precision','Reaction Ready','Answer 10 Chemistry questions correctly.','correct',10),
      ('chem_connections','Concept Bonds','Attempt 5 distinct Chemistry skills.','skills',5),
      ('chem_return','Catalyst for Change','Answer correctly in a Chemistry skill after a recorded error.','recovered',1),
      ('chem_transfer','New Evidence','After an error, answer a different question in that Chemistry skill correctly.','fresh_improvement',1),
      ('chem_mastery','Stable Understanding','Reach an 80% mastery estimate with at least 3 correct attempts in each of 3 Chemistry skills.','mastered',3),
    ]}
    for subject,badges in sets.items():
        stats=subject_stats(history,subject)
        for id,name,description,metric,target in badges:
            value=stats[metric]
            result.append({'id':id,'subject':subject,'name':name,'description':description,'earned':value>=target,'progress':min(value,target),'target':target})
    return result
