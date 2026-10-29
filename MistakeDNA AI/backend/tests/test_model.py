import json
from pathlib import Path
import numpy as np
import pytest
from app.config import settings
from app.offline_model.runtime import get_model,pieces,ModelUnavailable,TinyLM

def test_all_bundled_completions_are_generated_by_the_actual_weights():
    model=get_model(settings.offline_model_dir)
    successes=0
    for (skill,mode),card in model.cards.items():
        result=model.generate(skill,mode)
        assert result['engine']=='custom_tinylm',(skill,mode,result)
        assert pieces(result['text'])==pieces(card['response'])
        successes+=1
    assert successes==40
    assert model.manifest['held_out_evaluation'].startswith('None.')

def test_authored_fallback_is_explicit_when_neural_completion_is_not_checked():
    model=TinyLM(settings.offline_model_dir)
    # Zero allowed output length guarantees a failed match without faking a neural reply.
    result=model.generate('kp','explain',max_new_tokens=0)
    assert result['engine']=='authored_reference_fallback' and not result['validated']
    assert result['text']==model.cards[('kp','explain')]['response']

def test_checksum_protects_against_incomplete_model_artifacts(tmp_path):
    import shutil
    source=Path(settings.offline_model_dir)
    for name in ('manifest.json','corpus.json','weights.npz'):shutil.copy(source/name,tmp_path/name)
    with (tmp_path/'weights.npz').open('ab') as file:file.write(b'corrupt')
    with pytest.raises(ModelUnavailable):TinyLM(tmp_path)

def test_numpy_inference_matches_the_training_implementation():
    # Optional in the deployment-only test environment; PyTorch is not a runtime dependency.
    torch=pytest.importorskip('torch')
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'training'))
    from train import TinyLM as TrainingModel
    model=get_model(settings.offline_model_dir)
    training=TrainingModel(len(model.vocab));training.load_state_dict({k:torch.from_numpy(v.copy()) for k,v in model.w.items()});training.eval()
    ids=[model.index[t] for t in pieces('<bos> kp explain <answer>')]
    with torch.no_grad():expected=training(torch.tensor([ids]))[0].numpy()
    np.testing.assert_allclose(model.logits(ids),expected,atol=3e-5,rtol=3e-5)
