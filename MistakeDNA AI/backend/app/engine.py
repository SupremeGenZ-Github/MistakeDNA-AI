import json
import math
from pathlib import Path

CONTENT = json.loads((Path(__file__).parent / 'data/content.json').read_text())
QUESTIONS = CONTENT['questions']
SKILLS = CONTENT['skills']
BY_ID = {q['id']: q for q in QUESTIONS}

def public_question(q):
    return {k:v for k,v in q.items() if k not in ('answer','explanation','misconceptions')}

def grade(q, answer):
    if q['type'] == 'mcq':
        return answer == q['answer']
    try:
        return bool(answer.strip()) and math.isfinite(float(answer)) and abs(float(answer)-float(q['answer'])) <= q.get('tolerance', 1e-6)
    except ValueError:
        return False

def trace(prior, correct, difficulty, numerical=False):
    # Illustrative BKT, not trained or calibrated. Numerical questions use a lower guess rate.
    guess, slip, learn = (0.05 if numerical else 0.25), {1:.05,2:.1,3:.15}[difficulty], .08
    likelihood = prior * (1-slip if correct else slip)
    other = (1-prior) * (guess if correct else 1-guess)
    posterior = likelihood / (likelihood+other)
    return min(.995, max(.005, posterior+(1-posterior)*learn))

def select_questions(subject, mode, history, session_number=0):
    pool = [q for q in QUESTIONS if q['subject'] == subject]
    if mode == 'practice':
        estimates = {a.skill:a.mastery_after for a in history}
        seen = {a.question_id for a in history}
        # Rank weak skills, then include their immediate prerequisites if weak/unassessed.
        relevant = [s for s in SKILLS if s['subject'] == subject]
        ranked = sorted(relevant, key=lambda s: estimates.get(s['id'], .3))
        weakest = ranked[0]
        priority = [p for p in weakest['prerequisites'] if estimates.get(p,.3)<.65] + [weakest['id']]
        skill_order = list(dict.fromkeys(priority+[s['id'] for s in ranked]))
        return sorted(pool, key=lambda q:(skill_order.index(q['skill']), q['id'] in seen, q['difficulty']))[:5]
    # Rotate variants by session count; raw attempt parity would repeat completed 10-item tests.
    n = session_number % 2
    return (pool[n::2] + pool[1-n::2])[:10]
