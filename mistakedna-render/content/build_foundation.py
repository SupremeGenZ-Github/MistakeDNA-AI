from pathlib import Path
import json,random
ROOT=Path(__file__).resolve().parents[1]
def build():
 catalog=json.loads((ROOT/'backend/app/data/catalog.json').read_text());base=json.loads((ROOT/'backend/app/data/content.json').read_text())
 # Remove only prior generated foundation rows, preserving stable legacy question IDs.
 base['questions']=[q for q in base['questions'] if not q['id'].startswith('foundation-')]
 base['skills']=[s for s in base['skills'] if not s['id'].startswith('g')]
 for i,line in enumerate((ROOT/'content/foundation_questions.txt').read_text().splitlines()):
  if not line.strip() or line.startswith('#'):continue
  grade,subject,chapter_key,topic,stem,correct,wrong,explanation=line.split('|');grade=int(grade);topic=int(topic)
  matches=[c for c in catalog['chapters'] if c['grade']==grade and c['subject']==subject and chapter_key.lower() in c['title'].lower()]
  assert matches,(grade,subject,chapter_key)
  chapter=matches[0];entry=chapter['topics'][topic-1];id=entry['id']
  if not any(s['id']==id for s in base['skills']):base['skills'].append({'id':id,'name':entry['title'],'subject':subject,'grade':grade,'chapterId':chapter['id'],'description':explanation,'prerequisites':[]})
  options=[correct]+wrong.split(';');assert len(options)==4 and len(set(options))==4
  random.Random('MistakeDNA-'+str(i)).shuffle(options)
  base['questions'].append({'id':f'foundation-{i}','subject':subject,'grade':grade,'chapter':chapter['title'],'chapterId':chapter['id'],'topicId':id,'skill':id,'difficulty':1,'type':'mcq','prompt':stem,'options':options,'answer':str(options.index(correct)),'explanation':explanation,'hint':'Identify the concept in the question, check definitions and eliminate statements that contradict them.','misconceptions':{},'contentLevel':'foundation-checkpoint','reviewStatus':'authored; educator review recommended'})
 for s in base['skills']:
  if 'grade' not in s:
   s['grade']=11 if s['subject']=='Chemistry' else 10
   title='Equilibrium' if s['subject']=='Chemistry' else 'Quadratic Equations'
   chapter=next(c for c in catalog['chapters'] if c['grade']==s['grade'] and c['subject']==s['subject'] and c['title']==title)
   s['chapterId']=chapter['id']
 for q in base['questions']:
  if 'chapterId' not in q:
   skill=next(s for s in base['skills'] if s['id']==q['skill']);q['chapterId']=skill['chapterId'];q['topicId']=q['skill']
 legacy_topics={'dynamic':1,'mass':2,'kc':3,'kp':3,'shift':4,'form':1,'factor':2,'disc':3,'formula':4,'model':5}
 for q in base['questions']:
  if q['skill'] in legacy_topics:q['topicId']=q['chapterId']+'-'+str(legacy_topics[q['skill']])
 (ROOT/'backend/app/data/content.json').write_text(json.dumps(base,indent=2)+'\n')
 for chapter in catalog['chapters']:
  pool=[q for q in base['questions'] if q['chapterId']==chapter['id']]
  chapter['questionCount']=len(pool);chapter['coverage']='practice-checkpoints' if pool else 'outline'
  for topic in chapter['topics']:
   qs=[q for q in pool if q.get('topicId')==topic['id']]
   topic['questionCount']=len(qs);topic['status']='foundation-checkpoint' if qs else 'outline'
 (ROOT/'backend/app/data/catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 (ROOT/'frontend/lib/catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 (ROOT/'frontend/lib/curriculum.json').write_text(json.dumps(base['skills'],indent=2)+'\n')
 print('Question bank:',len(base['questions']),'questions;',len(base['skills']),'assessed skills; ready chapters:',sum(c['questionCount']>0 for c in catalog['chapters']))
if __name__=='__main__':build()
