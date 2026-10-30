"""Private progress reports derived from saved records, in Markdown and formatted PDF."""
from collections import defaultdict
from datetime import datetime
from html import escape
from io import BytesIO
import unicodedata
from zoneinfo import ZoneInfo
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from .engine import BY_ID,SKILLS
from .achievements import achievements
FONT_DIR=Path(__file__).parent/'assets/fonts'
pdfmetrics.registerFont(TTFont('ReportSans',str(FONT_DIR/'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('ReportSans-Bold',str(FONT_DIR/'DejaVuSans-Bold.ttf')))

def report_data(profile,history):
    names={s['id']:s['name'] for s in SKILLS};latest={};evidence=defaultdict(int);groups=defaultdict(list);sessions=defaultdict(list)
    for a in history:
        q=BY_ID.get(a.question_id)
        if not q:continue
        latest[a.skill]=a.mastery_after;evidence[a.skill]+=1;groups[q['subject']].append(a);sessions[a.session_id].append(a)
    return {'name':profile.name if profile else 'Learner','grade':profile.grade if profile else None,'goal':profile.goal if profile else '', 'generated':datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d %B %Y, %H:%M IST'),'attempts':len(history),'correct':sum(bool(a.correct) for a in history),'xp':len(history)*5+sum(bool(a.correct) for a in history)*10,'subjects':[{'subject':subject,'attempts':len(rows),'correct':sum(bool(a.correct) for a in rows)} for subject,rows in sorted(groups.items())],'skills':[{'id':id,'name':names.get(id,id),'mastery':p,'attempts':evidence[id]} for id,p in sorted(latest.items(),key=lambda item:item[1])],'sessions':[{'date':rows[0].created_at[:10],'subject':BY_ID.get(rows[0].question_id,{}).get('subject',''),'attempts':len(rows),'correct':sum(bool(a.correct) for a in rows)} for _,rows in list(sessions.items())[-15:][::-1]],'badges':[b for b in achievements(history) if b['earned']]}

def markdown_report(data):
    def clean(value):return escape(str(value)).replace('|','/').replace('\n',' ')
    lines=['# MistakeDNA AI - Private Progress Report','',f"**Learner:** {clean(data['name'])}",f"**Class:** {data['grade'] or 'Not set'} - CBSE",f"**Generated:** {data['generated']}",'',f"**Learning goal:** {clean(data['goal']) or 'Not set'}",'', '## Learning summary','',f"- Recorded answers: {data['attempts']}",f"- Correct answers: {data['correct']}",f"- Raw accuracy: {round(data['correct']/data['attempts']*100) if data['attempts'] else 'Not assessed'}{'%' if data['attempts'] else ''}",f"- Earned XP: {data['xp']}",'','## Subject performance','','| Subject | Answers | Correct | Raw accuracy |','|---|---:|---:|---:|']
    for s in data['subjects']:lines.append(f"| {s['subject']} | {s['attempts']} | {s['correct']} | {s['correct']/s['attempts']:.0%} |")
    if not data['subjects']:lines+=['','No answers recorded yet.']
    lines+=['','## Skill estimates','','These are illustrative Bayesian estimates, not grades, confidence in a diagnosis, or a measure of intelligence.','','| Skill | Estimated mastery | Evidence |','|---|---:|---:|']
    for s in data['skills']:lines.append(f"| {clean(s['name'])} | {s['mastery']:.0%} | {s['attempts']} attempts |")
    lines+=['','## Recommended next practice','']
    if data['skills']:
        for s in data['skills'][:5]:lines.append(f"- Revisit **{clean(s['name'])}**, work through an explanation, then try a fresh question. Current estimate: {s['mastery']:.0%} from {s['attempts']} attempts.")
    else:lines.append('Start a diagnostic in a chapter with available questions to establish your first evidence.')
    lines+=['','## Recent assessment activity','','| Date | Subject | Recorded answers | Correct |','|---|---|---:|---:|']
    for s in data['sessions']:lines.append(f"| {s['date']} | {s['subject']} | {s['attempts']} | {s['correct']} |")
    lines+=['','## Earned achievements','']
    lines += [f"- **{b['name']}** ({b['subject']}): {b['description']}" for b in data['badges']] or ['No subject badges earned yet.']
    lines+=['','## Interpretation and privacy','','One incorrect answer does not prove a misconception. Repeated questions provide limited evidence of transfer. Estimates use uncalibrated model assumptions and should guide practice rather than high-stakes decisions. Quiz correctness is determined by stored answers, never by the language model.','','This report contains private learning information. It was generated only from this signed-in learner’s saved records. No improvement, diagnosis or predicted exam rank has been invented.','']
    return '\n'.join(lines)

def pdf_report(data):
    buffer=BytesIO();styles=getSampleStyleSheet();
    for style in styles.byName.values():style.fontName='ReportSans-Bold' if 'Heading' in style.name or style.name=='Title' else 'ReportSans'
    navy=colors.HexColor('#17213b');purple=colors.HexColor('#6651b8');muted=colors.HexColor('#607089')
    styles.add(ParagraphStyle(name='ReportTitle',fontName='ReportSans-Bold',fontSize=23,leading=28,textColor=navy,spaceAfter=10))
    styles.add(ParagraphStyle(name='SmallNote',fontName='ReportSans',fontSize=8.3,leading=12,textColor=muted,spaceAfter=8))
    styles['Heading2'].textColor=purple;styles['Heading2'].spaceBefore=18;styles['Heading2'].spaceAfter=9
    styles['BodyText'].fontSize=9.2;styles['BodyText'].leading=14
    def safe(value):
        value=str(value).replace('Δ','Delta ').replace('→',' -> ').replace('≤',' <= ').replace('≥',' >= ').replace('−','-').replace('’',"'").replace('–','-').replace('—','-')
        return escape(unicodedata.normalize('NFKD',value).encode('ascii','replace').decode())
    def para(value,style='BodyText'):return Paragraph(safe(value),styles[style])
    def table(rows,widths):
        cells=[[para(c) for c in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef0f8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8f9fc')]),('VALIGN',(0,0),(-1,-1),'TOP'),('BOX',(0,0),(-1,-1),.4,colors.HexColor('#dce1ec')),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#dce1ec')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        return t
    width=A4[0]-88
    story=[para('MistakeDNA AI','ReportTitle'),para('PRIVATE LEARNING PROGRESS REPORT','SmallNote'),para(data['name'],'Heading1'),para(f"CBSE Class {data['grade'] or 'not set'}  |  Generated {data['generated']}",'SmallNote'),para('Learning goal: '+(data['goal'] or 'Not set')),Spacer(1,13)]
    accuracy=f"{data['correct']/data['attempts']:.0%}" if data['attempts'] else 'Not assessed'
    story +=[table([['Recorded answers','Correct answers','Raw accuracy','Earned XP'],[data['attempts'],data['correct'],accuracy,data['xp']]],[width/4]*4),para('Subject performance','Heading2')]
    story +=[table([['Subject','Answers','Correct','Raw accuracy']]+[[s['subject'],s['attempts'],s['correct'],f"{s['correct']/s['attempts']:.0%}"] for s in data['subjects']],[width*.43,width*.19,width*.18,width*.2])] if data['subjects'] else [para('No answers have been recorded yet. Complete a diagnostic to start your report.')]
    story +=[para('Skill estimates and evidence','Heading2'),para('Illustrative Bayesian estimates are separate from raw scores. Few attempts imply limited evidence; these are not calibrated probabilities of ability.','SmallNote')]
    if data['skills']:story.append(table([['Concept / skill','Estimated mastery','Recorded attempts']]+[[s['name'],f"{s['mastery']:.0%}",s['attempts']] for s in data['skills']],[width*.55,width*.25,width*.2]))
    else:story.append(para('No skills assessed yet.'))
    story +=[para('Recommended next practice','Heading2')]
    if data['skills']:
        for s in data['skills'][:5]:story.append(para(f"{s['name']}: revisit the explanation, practise the reasoning, then use a fresh question. Current estimate {s['mastery']:.0%}; {s['attempts']} recorded attempts."))
    else:story.append(para('Choose a class, subject and chapter with available questions, then take your first diagnostic.'))
    if data['sessions']:story.append(KeepTogether([para('Recent assessment activity','Heading2'),table([['Date (UTC)','Subject','Answers','Correct']]+[[s['date'],s['subject'],s['attempts'],s['correct']] for s in data['sessions']],[width*.23,width*.39,width*.19,width*.19])]))
    else:story.extend([para('Recent assessment activity','Heading2'),para('No assessment activity recorded.')])
    story +=[para('Earned subject achievements','Heading2')]
    if data['badges']:
        for b in data['badges']:story.append(para(f"{b['subject']} - {b['name']}: {b['description']}"))
    else:story.append(para('No subject achievements earned yet.'))
    story +=[para('How to interpret this report','Heading2'),para('One incorrect answer does not prove a misconception. Repeated questions provide limited evidence of transfer. No learning improvement, diagnosis or exam rank is inferred without supporting records. Scores use deterministic grading; language-model output cannot change them.','SmallNote'),para('Privacy: generated from the signed-in learner\'s records only. Treat this download as private learning information.','SmallNote')]
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#dce1ec'));canvas.line(44,41,A4[0]-44,41);canvas.setFillColor(muted);canvas.setFont('ReportSans',8);canvas.drawString(44,28,'MistakeDNA AI | Private report');canvas.drawRightString(A4[0]-44,28,'Page '+str(doc.page));canvas.restoreState()
    document=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=42,bottomMargin=57,title='MistakeDNA AI - Private Progress Report',author='MistakeDNA AI')
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
