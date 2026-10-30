from io import BytesIO
from types import SimpleNamespace
import pytest
from pypdf import PdfReader
from app.basic_responses import basic_reply
from app.achievements import achievements
from app.engine import CATALOG,QUESTIONS,BY_ID,SKILLS,select_questions
from app.reports import report_data,pdf_report,markdown_report

def test_five_subjects_have_real_questions_for_every_grade_and_catalog_ids_are_consistent():
    expected={'Chemistry','Physics','Mathematics','Biology','Social Science'}
    assert len(CATALOG['chapters'])==320
    assert sum(len(c['topics']) for c in CATALOG['chapters'])==1349
    chapters={c['id']:c for c in CATALOG['chapters']}
    assert len(chapters)==len(CATALOG['chapters'])
    for grade in (9,10,11,12):
        assert {q['subject'] for q in QUESTIONS if q['grade']==grade}==expected
        for subject in expected:
            pool=select_questions(subject,'diagnostic',[],grade_level=grade)
            assert pool and all(q['subject']==subject and q['grade']==grade for q in pool)
            practice=select_questions(subject,'practice',[],grade_level=grade)
            assert practice and len(practice)<=5
    for q in QUESTIONS:
        assert q['chapterId'] in chapters
        assert chapters[q['chapterId']]['grade']==q['grade']
    for c in CATALOG['chapters']:
        actual=sum(q['chapterId']==c['id'] for q in QUESTIONS)
        assert c['questionCount']==actual
        assert bool(actual)==(c['coverage']=='practice-checkpoints')

def test_basic_responses_arithmetic_and_scope_do_not_use_models():
    for message in ['Hi','HELLO!','How are you?','Thank you','What can you do?','What subjects do you support?','What is physics?','What is SST?','Are you offline?','How do I start practice?']:
        result=basic_reply(message);assert result and result['engine']=='authored_basic_response',message
    for message,expected in [('what is 2+3?','5'),('calculate 1/3 + 1/6','1/2'),('2^3','8'),('0.1 plus 0.2','3/10')]:
        result=basic_reply(message);assert result['engine']=='exact_arithmetic' and expected in result['reply']
    assert 'undefined' in basic_reply('1/0')['reply']
    assert basic_reply('import os; delete files') is None
    assert basic_reply('What is the weather tomorrow?') is None
    assert 'too large' in basic_reply('+'.join(['1']*20))['reply']

def test_chapter_grade_filtering_and_outline_only_sessions(account):
    ready=next(c for c in CATALOG['chapters'] if c['grade']==9 and c['subject']=='Biology' and c['questionCount'])
    result=account.post('/api/learning',json={'action':'start','subject':'Biology','grade':9,'chapterId':ready['id'],'mode':'diagnostic'})
    assert result.status_code==200,result.text
    assert all(q['chapterId']==ready['id'] and q['grade']==9 for q in result.json()['questions'])
    empty=next(c for c in CATALOG['chapters'] if c['questionCount']==0)
    result=account.post('/api/learning',json={'action':'start','subject':empty['subject'],'grade':empty['grade'],'chapterId':empty['id'],'mode':'practice'})
    assert result.status_code==409 and 'no checked questions' in result.text

def test_new_subject_notes_are_explicitly_authored_and_generic_help_works(account):
    ready=next(c for c in CATALOG['chapters'] if c['grade']==10 and c['subject']=='Physics' and c['questionCount'])
    r=account.post('/api/tutor',json={'subject':'Physics','grade':10,'chapterId':ready['id'],'message':'Explain this chapter'})
    assert r.status_code==200 and r.json()['engine']=='authored_curriculum_response'
    r=account.post('/api/tutor',json={'subject':'Biology','grade':9,'message':'hello'})
    assert r.status_code==200 and r.json()['engine']=='authored_basic_response'
    r=account.post('/api/tutor',json={'subject':'Social Science','grade':12,'message':'What is 7 times 8?'})
    assert r.status_code==200 and '56' in r.json()['reply']

def test_math_and_chemistry_badges_are_isolated_and_fresh_improvement_is_distinct():
    def a(question,correct,mastery=.4):
        q=BY_ID[question]
        return SimpleNamespace(question_id=question,skill=q['skill'],session_id='session-'+question,correct=correct,mastery_after=mastery)
    rows=[a('m1',0),a('m1',1)]
    badges={b['id']:b for b in achievements(rows)}
    assert badges['math_first']['earned'] and badges['math_return']['earned']
    assert not badges['math_transfer']['earned'] and not badges['chem_first']['earned']
    rows.append(a('m2',1)) # Same legacy standard-form skill, a different question.
    badges={b['id']:b for b in achievements(rows)}
    assert badges['math_transfer']['earned'] and not badges['chem_first']['earned']
    rows.append(a('c1',1))
    assert next(b for b in achievements(rows) if b['id']=='chem_first')['earned']

def test_private_pdf_and_markdown_reports_are_downloadable_and_do_not_mix_users(account,clients):
    other=clients[1]
    assert other.get('/api/report').status_code==401
    pdf=account.get('/api/report?format=pdf')
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
    assert 'application/pdf' in pdf.headers['content-type'] and pdf.headers['cache-control']=='no-store'
    reader=PdfReader(BytesIO(pdf.content));text='\n'.join(p.extract_text() for p in reader.pages)
    assert 'QA Learner' in text and 'No answers have been recorded' in text
    md=account.get('/api/report?format=md')
    assert md.status_code==200 and '# MistakeDNA' in md.text and '## Skill estimates' in md.text
    assert account.get('/api/report?format=html').status_code==400
