from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE='https://cbseacademic.nic.in/web_material/CurriculumMain27/'
SOURCE={9:{'Mathematics':'SecPart1/Maths_SecP1IX_2026-27.pdf','Social Science':'SecPart1/SocialScience_SecP1IX_2026-27.pdf','Science':'SecPart1/ScienceSt_SecP1_2026-27.pdf'},10:{'Mathematics':'SecPart1/Maths_SecP1X_2026-27.pdf','Social Science':'SecPart1/SocialScience_SecP1X_2026-27.pdf','Science':'SecPart1/Science_SecP1_2026-27.pdf'}}
def slug(text):return re.sub('[^a-z0-9]+','-',text.lower()).strip('-')
def build():
 chapters=[]
 for line in (ROOT/'content/catalog.txt').read_text().splitlines():
  if not line.strip() or line.startswith('#'):continue
  grade,subject,strand,title,topics=line.split('|');grade=int(grade)
  id=f'g{grade}-{slug(subject)}-{slug(strand)}-{slug(title)}'
  source=BASE+(SOURCE[grade][subject if subject in ('Mathematics','Social Science') else 'Science'] if grade<11 else 'SecPart2/'+({'Mathematics':'Maths','Social Science':'Geography' if strand.startswith('Geography') else 'History' if strand=='History' else 'Economics' if strand=='Economics' else 'PoliticalScience'}.get(subject,subject))+'_SecP2_2026-27.pdf')
  chapters.append({'id':id,'grade':grade,'subject':subject,'strand':strand,'title':title,'topics':[{'id':id+'-'+str(i+1),'title':topic,'status':'outline'} for i,topic in enumerate(topics.split(';'))],'source':source,'assessment':'Formative enrichment' if strand=='Formative enrichment' else 'Check official source for assessment scope','coverage':'outline'})
 assert len({c['id'] for c in chapters})==len(chapters)
 data={'session':'2026-27','curriculum':'CBSE','scope':'Standard Mathematics; Science grouped into Chemistry/Physics/Biology; SST includes History/Geography/Political Science/Economics. Advanced-level variants are not included.','status':'Curriculum outline with explicit lesson/question readiness, not a claim that every textbook point is taught or assessed.','sources_index':'https://cbseacademic.nic.in/curriculum_2027.html','chapters':chapters}
 (ROOT/'backend/app/data/catalog.json').write_text(json.dumps(data,indent=2)+'\n')
 print('Catalog:',len(chapters),'chapters / units;',sum(len(c['topics']) for c in chapters),'topic labels')
if __name__=='__main__':build()
