"""Custom TinyLM inference using NumPy only. No network, torch or pretrained assets.
Weights were trained from random initialization by training/train.py.
"""
import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from threading import Lock
import numpy as np

class ModelUnavailable(RuntimeError):
    pass

def pieces(text):
    return re.findall(r'<[a-z]+>|[a-z]+(?:\x27[a-z]+)?|[0-9]+(?:\.[0-9]+)?|[^\w\s]',unicodedata.normalize('NFKC',text).lower())

def detokenize(tokens):
    text=' '.join(tokens)
    text=re.sub(r'\s+([.,?!:;])',r'\1',text)
    text=text[:1].upper()+text[1:]
    text=re.sub(r'([.!?]\s+)([a-z])',lambda match:match.group(1)+match.group(2).upper(),text)
    for token,replacement in [('kp','Kp'),('kc','Kc'),('rt','RT')]:
        text=re.sub(r'\b'+token+r'\b',replacement,text,flags=re.IGNORECASE)
    return text

class TinyLM:
    def __init__(self,directory):
        folder=Path(directory)
        try:
            self.manifest=json.loads((folder/'manifest.json').read_text())
            weight_path=folder/'weights.npz'
            if hashlib.sha256(weight_path.read_bytes()).hexdigest()!=self.manifest['weights_sha256']:
                raise ValueError('Model checksum mismatch')
            if hashlib.sha256((folder/'corpus.json').read_bytes()).hexdigest()!=self.manifest['corpus_sha256']:
                raise ValueError('Curriculum checksum mismatch')
            with np.load(weight_path,allow_pickle=False) as loaded:
                self.w={k:loaded[k] for k in loaded.files}
            self.vocab=self.manifest['vocab'];self.index={t:i for i,t in enumerate(self.vocab)}
            self.h=self.manifest['heads'];self.layers=self.manifest['layers'];self.context=self.manifest['context']
            self.cards={(e['skill'],e['mode']):e for e in json.loads((folder/'corpus.json').read_text())['examples']}
            self.lock=Lock()
            self.logits([1,3]) # Verify dimensions/loadability without generating any student record.
        except (OSError,ValueError,KeyError,TypeError,IndexError) as error:
            raise ModelUnavailable('The bundled offline model is missing or invalid. Reinstall its original weights and manifest.') from error

    def norm(self,x,prefix):
        mean=x.mean(axis=-1,keepdims=True);variance=((x-mean)**2).mean(axis=-1,keepdims=True)
        return (x-mean)/np.sqrt(variance+1e-5)*self.w[prefix+'.weight']+self.w[prefix+'.bias']

    def linear(self,x,prefix):
        return x@self.w[prefix+'.weight'].T+self.w[prefix+'.bias']

    def logits(self,ids):
        t=len(ids)
        if t>self.context:raise ValueError('Context limit exceeded')
        x=self.w['token.weight'][ids]+self.w['position.weight'][:t]
        width=x.shape[-1];d=width//self.h
        for i in range(self.layers):
            p=f'blocks.{i}'
            q,k,v=np.split(self.linear(self.norm(x,p+'.n1'),p+'.qkv'),3,axis=-1)
            q,k,v=[a.reshape(t,self.h,d).transpose(1,0,2) for a in (q,k,v)]
            scores=(q@k.transpose(0,2,1))/np.sqrt(np.float32(d))
            scores=np.where(np.triu(np.ones((t,t),dtype=bool),1)[None,:,:],-np.inf,scores)
            probabilities=np.exp(scores-scores.max(axis=-1,keepdims=True));probabilities/=probabilities.sum(axis=-1,keepdims=True)
            attention=(probabilities@v).transpose(1,0,2).reshape(t,width)
            x=x+self.linear(attention,p+'.proj')
            hidden=self.linear(self.norm(x,p+'.n2'),p+'.fc')
            hidden=.5*hidden*(1+np.tanh(np.sqrt(np.float32(2/np.pi))*(hidden+.044715*hidden**3)))
            x=x+self.linear(hidden,p+'.out')
        return self.norm(x,'norm')@self.w['token.weight'].T

    def generate(self,skill,mode,max_new_tokens=140):
        if (skill,mode) not in self.cards:raise ValueError('Unsupported curriculum request')
        prompt=f'<bos> {skill} {mode} <answer>'
        ids=[self.index.get(t,4) for t in pieces(prompt)];out=[]
        # One bounded CPU generation at a time. No network calls or shared user context.
        with self.lock:
            for _ in range(min(max_new_tokens,140)):
                nxt=int(np.argmax(self.logits(ids)[-1]))
                if nxt==2:break
                ids.append(nxt);out.append(self.vocab[nxt])
                if len(ids)>=self.context:break
        expected=self.cards[(skill,mode)]['response']
        valid=out==pieces(expected)
        # Exact curriculum validation is intentionally conservative. An imperfect neural
        # completion is not shown as trusted teaching. The fallback is explicitly labeled.
        return {'text':detokenize(out) if valid else expected,'engine':'custom_tinylm' if valid else 'authored_reference_fallback','validated':valid,'generated_tokens':len(out)}

    def public_info(self):
        return {k:self.manifest[k] for k in ['architecture','parameters','vocabulary_size','width','heads','layers','context','pretrained','training_examples','training_prompt_exact_matches','training_prompt_count','held_out_evaluation','weights_sha256']}

@lru_cache(maxsize=2)
def get_model(directory):
    return TinyLM(directory)
