"""Train MistakeDNA TinyLM from RANDOM weights. PyTorch is used only for training.
No transformers library, pretrained weights, tokenizer or model hub is used.
"""
import argparse,json,math,re,time,hashlib,unicodedata
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from build_corpus import build,ROOT

def pieces(text):
    return re.findall(r'<[a-z]+>|[a-z]+(?:\x27[a-z]+)?|[0-9]+(?:\.[0-9]+)?|[^\w\s]',unicodedata.normalize('NFKC',text).lower())
class Block(nn.Module):
    def __init__(self,w,h,context):
        super().__init__();self.h=h;self.n1=nn.LayerNorm(w);self.qkv=nn.Linear(w,3*w);self.proj=nn.Linear(w,w);self.n2=nn.LayerNorm(w);self.fc=nn.Linear(w,4*w);self.out=nn.Linear(4*w,w)
    def forward(self,x):
        b,t,w=x.shape;v=self.n1(x);q,k,v=self.qkv(v).chunk(3,dim=-1)
        q,k,v=[a.view(b,t,self.h,w//self.h).transpose(1,2) for a in (q,k,v)]
        attention=F.scaled_dot_product_attention(q,k,v,is_causal=True)
        x=x+self.proj(attention.transpose(1,2).contiguous().view(b,t,w))
        return x+self.out(F.gelu(self.fc(self.n2(x)),approximate='tanh'))
class TinyLM(nn.Module):
    def __init__(self,vocab,w=64,h=4,layers=2,context=192):
        super().__init__();self.token=nn.Embedding(vocab,w);self.position=nn.Embedding(context,w);self.blocks=nn.ModuleList([Block(w,h,context) for _ in range(layers)]);self.norm=nn.LayerNorm(w)
    def forward(self,x):
        y=self.token(x)+self.position(torch.arange(x.shape[1],device=x.device))
        for block in self.blocks:y=block(y)
        return self.norm(y)@self.token.weight.T

def main():
    p=argparse.ArgumentParser();p.add_argument('--steps',type=int,default=2200);p.add_argument('--threads',type=int,default=2);p.add_argument('--seed',type=int,default=29);args=p.parse_args()
    torch.set_num_threads(args.threads);torch.manual_seed(args.seed);np.random.seed(args.seed)
    examples=build();vocab=['<pad>','<bos>','<eos>','<answer>','<unk>']+sorted(set(t for e in examples for t in pieces(e['prompt']+' '+e['response']))-{'<pad>','<bos>','<eos>','<answer>','<unk>'})
    index={v:i for i,v in enumerate(vocab)};context=192
    seqs=[];labels=[]
    for e in examples:
        prefix=[index[t] for t in pieces(e['prompt'])];completion=[index[t] for t in pieces(e['response'])]+[2];tokens=prefix+completion
        if len(tokens)>context:raise ValueError('Training example exceeds context')
        x=tokens[:-1];y=tokens[1:]
        y[:len(prefix)-1]=[-100]*(len(prefix)-1)
        seqs.append(x);labels.append(y)
    maxlen=max(map(len,seqs));inputs=torch.tensor([x+[0]*(maxlen-len(x)) for x in seqs]);targets=torch.tensor([x+[-100]*(maxlen-len(x)) for x in labels])
    model=TinyLM(len(vocab),context=context);optimizer=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.01)
    start=time.perf_counter();initial=None
    for step in range(args.steps):
        batch=torch.randint(len(examples),(16,));logits=model(inputs[batch]);loss=F.cross_entropy(logits.reshape(-1,len(vocab)),targets[batch].reshape(-1),ignore_index=-100)
        optimizer.zero_grad(set_to_none=True);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step()
        for group in optimizer.param_groups:group['lr']=.0002+.0018*.5*(1+math.cos(math.pi*(step+1)/args.steps))
        if initial is None:initial=float(loss.detach())
        if step%200==0 or step==args.steps-1:print(json.dumps({'step':step+1,'loss':round(float(loss.detach()),5),'seconds':round(time.perf_counter()-start,1)}),flush=True)
    model.eval()
    with torch.no_grad():
        loss=float(F.cross_entropy(model(inputs).reshape(-1,len(vocab)),targets.reshape(-1),ignore_index=-100))
        exact=0;samples=[]
        for e in examples:
            tokens=[index[t] for t in pieces(e['prompt'])];out=[]
            for _ in range(140):
                nxt=int(model(torch.tensor([tokens]))[0,-1].argmax())
                if nxt==2:break
                tokens.append(nxt);out.append(vocab[nxt])
                if len(tokens)>=context:break
            expected=pieces(e['response']);ok=out==expected;exact+=int(ok)
            samples.append({'skill':e['skill'],'mode':e['mode'],'exact':ok,'generated_tokens':out})
    target=ROOT/'backend/app/offline_model';weights=target/'weights.npz'
    np.savez_compressed(weights,**{k:v.detach().numpy().astype(np.float32) for k,v in model.state_dict().items()})
    report={'architecture':'custom decoder-only causal transformer','pretrained':False,'initialization':'random; no existing model weights or tokenizer','parameters':sum(v.numel() for v in model.parameters()),'vocabulary_size':len(vocab),'width':64,'heads':4,'layers':2,'context':context,'seed':args.seed,'steps':args.steps,'training_examples':len(examples),'training_loss_initial':initial,'training_loss_final':loss,'training_perplexity':math.exp(loss),'training_prompt_exact_matches':exact,'training_prompt_count':len(examples),'held_out_evaluation':'None. Exact matches measure memorization on training prompts, not generalization or educational effectiveness.','training_seconds':round(time.perf_counter()-start,1),'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'corpus_sha256':hashlib.sha256((target/'corpus.json').read_bytes()).hexdigest(),'vocab':vocab}
    (target/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'training/sample_generations.json').write_text(json.dumps(samples,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='vocab'}),flush=True)
if __name__=='__main__':main()
