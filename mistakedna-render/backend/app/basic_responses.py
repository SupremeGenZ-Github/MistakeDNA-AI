"""Reliable offline basics. Authored responses and exact arithmetic, not neural output."""
import ast
import math
import operator
import re
from fractions import Fraction

FAQS=[
(r'^(hi|hello|hey|good morning|good afternoon|good evening|namaste)[!. ]*$', 'Hello! I can help you study Chemistry, Physics, Mathematics, Biology and Social Science. Choose your class and topic, or ask about practice, progress or basic arithmetic.'),
(r'^(how are you|how are you doing|how is it going)[?!. ]*$', 'I am ready to help you learn. Tell me the subject and concept you want to work on.'),
(r'^(thanks|thank you|thankyou|ty|thank you so much)[!. ]*$', 'You are welcome. Keep asking why, and use each mistake as a clue for your next practice session.'),
(r'^(bye|goodbye|see you|see you later)[!. ]*$', 'See you next time. Your saved learning records will be here when you sign in again.'),
(r'(who are you|what are you|your name|what is mistaken?dna|what is this app)', 'I am the MistakeDNA learning assistant. This app uses authored learning material, deterministic grading and a small custom offline neural model. I am not a general-purpose chatbot.'),
(r'(what can you do|how do i use|getting started|help me start|^help[?!. ]*$)', 'Start by choosing your class, subject and chapter. Read a lesson or start a diagnostic, submit your own answer, inspect the explanation, then use focused practice and your knowledge map. Content availability is shown explicitly.'),
(r'(what subjects|which subjects|subjects.*support)', 'The app supports Chemistry, Physics, Mathematics, Biology and Social Science for Classes 9–12. Social Science groups History, Geography, Political Science/Civics and Economics. Availability of lessons and scored questions is shown for each topic.'),
(r'(are you offline|need.*api key|internet.*model|external.*ai|send.*data|privacy)', 'Model inference runs on this app server without an external AI API or model download. A Render-hosted website still needs internet access from your browser. Account and progress data are stored in your configured database. A local installation can run without internet after setup.'),
(r'(how.*(practice|diagnostic)|start.*(practice|diagnostic))', 'Choose your class, subject and a chapter with available questions. Use Diagnostic Test to assess your starting point, then Practice Arena for focused exercises. Answers are graded using stored answer keys or deterministic numerical checks.'),
(r'(what.*mastery|how.*mastery|mastery.*mean)', 'Mastery is an illustrative Bayesian estimate based on recorded attempts. It is separate from your raw quiz score, is uncertain with few answers, and is not a measure of intelligence or a guaranteed exam result.'),
(r'(what.*(xp|achievement|badge)|how.*(xp|achievement|badge))', 'XP is calculated from recorded answers. Achievements use actual practice and mastery evidence. Mathematics and Chemistry have their own badge sets, so progress in one subject does not unlock the other subject’s badges.'),
(r'(forgot.*password|reset.*password)', 'This MVP does not include password-recovery email. Keep your password safe; do not share it in chat. Contact the person operating this deployment if you cannot access your account.'),
(r'^(what is |define )?(chemistry|physics|mathematics|maths?|biology|social science|sst)[?!. ]*$', None),
(r'^(tell me (a )?joke|a joke please)[?!. ]*$', 'Why did the student bring a ladder to the lesson? To reach a higher level of understanding.'),
]
DEFINITIONS={'chemistry':'Chemistry studies matter: its composition, structure, properties and the changes it undergoes.','physics':'Physics studies matter, energy, motion, forces and the laws describing their interactions.','mathematics':'Mathematics studies quantities, structures, patterns and logical relationships using precise definitions and reasoning.','math':'Mathematics studies quantities, structures, patterns and logical relationships using precise definitions and reasoning.','maths':'Mathematics studies quantities, structures, patterns and logical relationships using precise definitions and reasoning.','biology':'Biology is the study of living organisms and life processes, including cells, heredity, evolution and ecosystems.','social science':'Social Science studies human societies through History, Geography, Political Science and Economics.','sst':'SST means Social Science: History, Geography, Political Science/Civics and Economics.'}
OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow}
def arithmetic(message):
    expression=message.lower().strip().rstrip('?= .')
    expression=re.sub(r'^(what is|what\x27s|calculate|compute|solve|evaluate)\s+','',expression)
    expression=expression.replace('×','*').replace('÷','/').replace('^','**')
    for phrase,sign in [('multiplied by','*'),('divided by','/'),('plus','+'),('minus','-'),('times','*')]:expression=re.sub(r'\b'+phrase+r'\b',sign,expression)
    if len(expression)>120 or not re.fullmatch(r'[0-9.\s()+*/-]+',expression) or not re.search(r'[+*/-]',expression):return None
    try:
        tree=ast.parse(expression,mode='eval')
        if sum(1 for _ in ast.walk(tree))>40:return 'That expression is too large for the basic calculator.'
        def visit(node):
            if isinstance(node,ast.Constant) and type(node.value) in (int,float):
                if not math.isfinite(node.value) or abs(node.value)>10**12:raise ValueError()
                return Fraction(str(node.value))
            if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                v=visit(node.operand);return v if isinstance(node.op,ast.UAdd) else -v
            if isinstance(node,ast.BinOp) and type(node.op) in OPS:
                left,right=visit(node.left),visit(node.right)
                if isinstance(node.op,ast.Pow) and (right.denominator!=1 or abs(right)>12):raise ValueError()
                result=OPS[type(node.op)](left,right)
                if abs(result)>10**100 or result.denominator>10**100:raise ValueError()
                return result
            raise ValueError()
        value=visit(tree.body)
        result=str(value.numerator) if value.denominator==1 else f'{value} (approximately {float(value):.8g})'
        return f'{expression} = {result}. This answer was calculated exactly with rational arithmetic, not generated by the language model.'
    except ZeroDivisionError:return 'Division by zero is undefined. Please check the denominator.'
    except (ValueError,SyntaxError,OverflowError,TypeError):return 'I can calculate short arithmetic expressions with +, -, *, /, brackets and small integer powers.'

def basic_reply(message):
    lower=' '.join(message.lower().strip().replace('’',"'").split())
    answer=arithmetic(lower)
    if answer:return {'reply':answer,'engine':'exact_arithmetic','notice':'Deterministic calculation; no neural model or external service was used.'}
    for pattern,response in FAQS:
        match=re.search(pattern,lower)
        if match:
            if response is None:response=DEFINITIONS[match.group(2)]
            return {'reply':response,'engine':'authored_basic_response','notice':'Authored offline basic response; not generated by TinyLM.'}
    return None
