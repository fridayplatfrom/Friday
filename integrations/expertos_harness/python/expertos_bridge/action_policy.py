"""Optional tiny neural browser-action proposal model, NEVER the browser executor.

Only reviewed, site-disjoint datasets can produce promotable candidates. A low
score always abstains. The network itself has no permissions to perform actions.
"""
import hashlib
import json
import math
from pathlib import Path
import re

LABELS = ("abstain", "extract", "fill_form", "navigate")
FEATURE_DIM = 1024


def vectorize(task: str, context: str):
    import torch
    words = re.findall(r"[a-z0-9]+", (task + " " + context).lower())[:600]
    values = torch.zeros(FEATURE_DIM)
    for word in words:
        digest = hashlib.blake2b(word.encode('utf-8'), digest_size=8).digest()
        values[int.from_bytes(digest, 'big') % FEATURE_DIM] += 1
    norm = values.norm().item()
    if norm:
        values /= norm
    return values


def validate_records(records, *, demo=False):
    if not isinstance(records, list) or len(records) < 6:
        raise ValueError('Need at least six labeled examples')
    splits = {k: [] for k in ('train', 'validation', 'test')}
    source_seen, case_seen, normalized = {}, {}, {}
    for row in records:
        for field in ('task', 'context', 'site_id', 'case_id', 'split', 'label'):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError(f'Missing {field}')
        if row['split'] not in splits or row['label'] not in LABELS:
            raise ValueError('Unrecognized split or action label')
        if not demo and (row.get('reviewed') is not True or not row.get('reviewer')):
            raise ValueError('Unreviewed action demonstrations cannot be promoted')
        split = row['split']
        site = row['site_id']
        case = row['case_id']
        key = ' '.join((row['task'] + ' ' + row['context']).casefold().split())
        for memo, index in ((source_seen,site), (case_seen,case), (normalized,key)):
            if index in memo and memo[index] != split and not demo:
                raise ValueError('Train/eval leakage across sites, cases or duplicate input')
            memo[index] = split
        splits[split].append(row)
    if any(not v for v in splits.values()):
        raise ValueError('Train, validation and test partitions must be nonempty')
    return splits


def _net():
    import torch
    from torch import nn
    return nn.Sequential(nn.Linear(FEATURE_DIM,64),nn.ReLU(),nn.Linear(64,len(LABELS)))


def train(records, output_dir, *, epochs=10, demo=False, seed=7):
    import torch
    if not isinstance(epochs, int) or epochs < 1 or epochs > 100:
        raise ValueError('Epochs must be 1..100')
    partitions = validate_records(records,demo=demo)
    torch.manual_seed(seed)
    model = _net()
    optimizer = torch.optim.Adam(model.parameters(),lr=0.002)
    criterion = torch.nn.CrossEntropyLoss()
    def xy(rows):
        x = torch.stack([vectorize(r['task'],r['context']) for r in rows])
        y = torch.tensor([LABELS.index(r['label']) for r in rows],dtype=torch.long)
        return x,y
    train_x,train_y=xy(partitions['train'])
    def score(rows):
        x,y=xy(rows)
        model.eval()
        with torch.no_grad():
            return float((model(x).argmax(-1)==y).float().mean().item())
    best, best_state = -1., None
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad()
        loss=criterion(model(train_x),train_y)
        loss.backward()
        optimizer.step()
        val=score(partitions['validation'])
        if val > best:
            best=val
            best_state={k:v.clone() for k,v in model.state_dict().items()}
    model.load_state_dict(best_state)
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=True)
    checkpoint=output/'policy.pt'
    torch.save(model.state_dict(),checkpoint)
    digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    report={'architecture':'expertos-browser-action-mlp-v1', 'labels':list(LABELS),
            'features':FEATURE_DIM,'experimental':True,'review_claimed':not demo,
            'weights_sha256':digest,'metrics':{
                'validation_accuracy':best,'test_accuracy':score(partitions['test']),
                'test_count':len(partitions['test'])},
            'limitations':'Small text-only action classifier. No autonomous browser permissions.'}
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def predict(path, task, context, *, allow_experimental=False, min_probability=0.8):
    import torch
    root=Path(path)
    meta=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if meta.get('architecture')!='expertos-browser-action-mlp-v1' or meta.get('labels')!=list(LABELS):
        raise ValueError('Unknown action-model architecture or label order')
    if meta.get('experimental') and not allow_experimental:
        return {'status':'model_disabled','action':None}
    if hashlib.sha256((root/'policy.pt').read_bytes()).hexdigest()!=meta.get('weights_sha256'):
        raise ValueError('Model weights checksum mismatch')
    model=_net()
    model.load_state_dict(torch.load(root/'policy.pt',weights_only=True,map_location='cpu'),strict=True)
    model.eval()
    x=vectorize(task,context)
    with torch.no_grad():
        probabilities=torch.softmax(model(x),0)
        top=int(probabilities.argmax().item())
        probability=float(probabilities[top].item())
    if LABELS[top]=='abstain' or probability<min_probability:
        return {'status':'abstained','action':None, 'raw_score':probability,
                'score_type':'uncalibrated_softmax', 'experimental':True}
    return {'status':'experimental_proposal','action':LABELS[top],
            'raw_score':probability,'score_type':'uncalibrated_softmax',
            'requires_deterministic_validation':True,'experimental':True}
