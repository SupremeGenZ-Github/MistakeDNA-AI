"""Original, narrow curriculum corpus. No pretrained text/tokenizer/model downloads."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CARDS={
'dynamic':[
'At equilibrium, both directions of a reversible reaction continue. Their rates are equal, so concentrations stay constant. Constant does not mean that reactant and product concentrations must be equal. A closed system is needed to maintain this balance.',
'Compare rates first. Equal rates can maintain different concentrations. Ask yourself whether the question describes speed or amount.',
'If the forward rate at equilibrium is four units per second, what must the reverse rate be? Explain why a constant concentration does not mean that the reaction has stopped.',
'Imagine two people moving beads between boxes at the same speed. The bead counts can stay steady while transfers continue. This illustrates equal rates, not necessarily equal numbers in the boxes.'
],
'mass':[
'Write product concentration terms above reactant concentration terms. Raise each term to its stoichiometric coefficient. Omit pure solids and pure liquids because their activities are taken as one. Include gaseous species and dissolved solutes when appropriate.',
'Check the side of the fraction and the powers separately. A coefficient becomes an exponent, not a multiplier outside the concentration term.',
'For A plus two B in equilibrium with C, what powers belong to A, B and C in the concentration expression? Would a pure solid appear as a variable concentration term?',
'Build the expression in three steps: products on top, reactants below, then coefficients as powers. Finally remove pure solid and pure liquid activities. Do not remove dissolved substances just because they are not gases.'
],
'kc':[
'Kc compares the equilibrium concentration terms for products and reactants at a specified temperature. For A in equilibrium with B, Kc equals the concentration of B divided by the concentration of A. Reversing a reaction takes the reciprocal of its equilibrium constant.',
'First confirm that the concentrations are equilibrium values. Then substitute them into the correctly balanced reaction expression before calculating.',
'For A in equilibrium with B, suppose the equilibrium concentration of B is three times that of A. What is Kc? What happens to the constant if the reaction is written in reverse?',
'Think of Kc as a ratio defined by a particular reaction. Reversing that reaction flips the ratio. Multiplying every reaction coefficient by a number raises the constant to that power. Temperature must stay the same for these comparisons.'
],
'kp':[
'Use Kp equals Kc times RT raised to delta n. Delta n is the sum of gaseous product coefficients minus the sum of gaseous reactant coefficients. Count gases only. When delta n is zero, Kp equals Kc.',
'Balance the reaction and list gaseous coefficients on each side. Subtract reactants from products. Do not use the total number of gas moles as delta n.',
'For nitrogen plus three hydrogen giving two ammonia, all gaseous, what is delta n? State which side you subtract from which before using the relationship between Kp and Kc.',
'Separate the mole count from the formula. First count gaseous product coefficients. Next count gaseous reactant coefficients. Take products minus reactants, keeping the sign. Only then use that result as the exponent on RT.'
],
'shift':[
'A system at equilibrium shifts to oppose a disturbance. Compression favors the side with fewer gaseous moles. Heating favors the endothermic direction. A catalyst speeds up reaching equilibrium but does not change the equilibrium composition or its constant.',
'Identify whether concentration, pressure or temperature changed. Then use that specific disturbance. A change in rate alone does not establish a change in equilibrium position.',
'If an exothermic forward reaction is heated, which direction absorbs the added heat? Does adding a catalyst change the final equilibrium composition? Explain the difference between position and rate.',
'Imagine heat as a product in an exothermic forward reaction. Adding heat favors the reverse direction. For pressure changes, count only gaseous coefficients. Keep these two tests separate: pressure and temperature do not use the same rule.'
],
'form':[
'A quadratic equation has the standard form a x squared plus b x plus c equals zero, where a is not zero. Expand brackets, combine like terms and move all terms to one side before identifying the coefficients.',
'Put zero on one side and simplify the other side. Check whether the squared terms cancel before deciding that the equation is quadratic.',
'If x times the term x plus three equals ten, what equation results after expanding and moving ten to the left? Identify a, b and c with their signs.',
'Coefficients belong to a simplified equation. First expand, then combine terms, then move everything to one side. The coefficient of x squared must be nonzero. A written squared term can disappear when like terms cancel.'
],
'factor':[
'Factor the quadratic into a product equal to zero. Set each factor equal to zero and solve both equations. Do not divide by x unless you have separately checked the possibility that x equals zero, because division can discard a valid root.',
'Find factors that match both the middle coefficient and the constant term. After factoring, remember that factor signs and root signs are different.',
'For two x squared minus eight x equals zero, factor out the common term. What two roots follow? Which root could be lost if you divide the original equation by x?',
'A product is zero when at least one factor is zero. Apply that rule to every factor. For x times the factor x minus four equal to zero, consider x equal to zero as well as x minus four equal to zero.'
],
'disc':[
'The discriminant is b squared minus four a c. A positive discriminant gives two distinct real roots. A zero discriminant gives equal real roots. A negative discriminant gives no real roots. Square the entire signed value of b.',
'Copy a, b and c with their signs. Use brackets when squaring a negative b. Calculate the discriminant before deciding the nature of the roots.',
'For x squared minus six x plus nine equals zero, what is b squared minus four a c? What does its sign tell you about the real roots?',
'The discriminant answers a nature question before you solve for roots. Positive means two different real roots, zero means equal real roots, and negative means no real roots. A negative coefficient squared gives a positive square.'
],
'formula':[
'The quadratic formula gives x equals negative b plus or minus the square root of b squared minus four a c, all divided by two a. Keep the entire numerator over the denominator. Evaluate both signs when real roots exist.',
'Write the formula before substituting. Check negative b, the sign inside the discriminant, and whether the whole numerator is divided by two a.',
'For two x squared plus x minus three equals zero, what are a, b and c? After calculating the discriminant, what denominator must divide the entire numerator?',
'Use three checkpoints: negative b at the start, b squared minus four a c under the root, and two a under the whole numerator. The plus and minus signs produce two candidates, which you can check by substitution.'
],
'model':[
'Choose a variable and translate the situation into an equation. Solve the quadratic, then check every root against the original context. A negative length or a value that violates a positive integer condition must be rejected even if it solves the equation.',
'Write down what the variable means, including its unit. After solving, return to that meaning before selecting the answer. The requested quantity may differ from the variable you found.',
'A rectangle has width x and length x plus three, with area forty. What equation describes its area? After solving it, how would you reject an impossible width?',
'Word problems have two checks: algebra and context. A root must solve the equation and make sense in the story. Substitute candidates into the original relationships, and report exactly the quantity requested with its unit.'
]}
MODES=['explain','hint','check','simple']
def build():
    content=json.loads((ROOT/'backend/app/data/content.json').read_text())
    examples=[]
    for skill in content['skills']:
        for mode,text in zip(MODES,CARDS[skill['id']]):
            examples.append({'skill':skill['id'],'subject':skill['subject'],'mode':mode,'prompt':f'<bos> {skill["id"]} {mode} <answer>','response':text})
    out=ROOT/'backend/app/offline_model/corpus.json'
    out.write_text(json.dumps({'provenance':'Original curriculum paragraphs authored for MistakeDNA. No scraped question bank or pretrained model outputs.','examples':examples},indent=2)+'\n')
    return examples
if __name__=='__main__':build()
