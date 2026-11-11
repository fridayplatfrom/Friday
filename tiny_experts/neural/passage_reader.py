"""Question-conditioned, trainable extractive reader (no generative language model).

The network predicts start/end token positions or a null answer. Evidence is a
retrieved source passage, never a generated citation. A standalone experiment is
not a validated scientific model.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import math
import random
import re

import torch
from torch import nn

TOKENS = re.compile(r"\w+(?:[-'’]\w+)*|[^\w\s]", re.UNICODE)
SCHEMA = "extractive-reader-v1"


def tokenize(text):
    return [(m.group().casefold(), m.start(), m.end()) for m in TOKENS.finditer(text)]


def make_vocab(examples, max_words=8000):
    from collections import Counter
    counts = Counter(t for x in examples for field in ('question', 'passage')
                     for t, _, _ in tokenize(x[field]))
    return {'<pad>': 0, '<unk>': 1, **{word: i + 2 for i, (word, _) in
            enumerate(sorted(counts.items(), key=lambda p: (-p[1], p[0]))[:max_words - 2])}}


def verify_example(row, max_tokens=256, max_question=48):
    if not isinstance(row, dict):
        raise ValueError('Example must be a record')
    for key in ('id', 'question', 'passage', 'source_id', 'case_id', 'split'):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f'Missing {key}')
    if row['split'] not in {'train', 'validation', 'test'}:
        raise ValueError('split must be train, validation or test')
    question = tokenize(row['question']); passage = tokenize(row['passage'])
    if not question or not passage or len(question) > max_question or len(passage) > max_tokens:
        raise ValueError('Empty or overlong question/passage')
    value = row.get('answer_text')
    start = row.get('answer_start')
    if value is None:
        if start is not None:
            raise ValueError('Unanswerable examples must omit answer_start')
        return 0, 0
    if not isinstance(value, str) or not value or type(start) is not int:
        raise ValueError('Answer and exact start offset required')
    if row['passage'][start:start + len(value)] != value:
        raise ValueError('Answer span is absent or incorrect')
    end = start + len(value)
    first = next((i + 1 for i, (_, s, e) in enumerate(passage) if s <= start < e), None)
    last = next((i + 1 for i, (_, s, e) in enumerate(passage) if s < end <= e), None)
    if first is None or last is None or last < first:
        raise ValueError('Answer offset not aligned to tokenizer')
    return first, last


def validate_splits(rows, demo=False):
    if not isinstance(rows, list) or len(rows) < 3:
        raise ValueError('At least 3 examples required')
    ids = set(); cases = {}
    for row in rows:
        verify_example(row)
        if row['id'] in ids:
            raise ValueError('Duplicate example IDs')
        ids.add(row['id'])
        group = (row.get('source_family_id') or row['source_id'], row['case_id'])
        if group in cases and cases[group] != row['split']:
            raise ValueError('Case leakage across splits')
        cases[group] = row['split']
    groups = {kind: [x for x in rows if x['split'] == kind]
              for kind in ('train', 'validation', 'test')}
    if any(not v for v in groups.values()):
        raise ValueError('All three splits must be nonempty')
    sources = {kind: {(x.get('source_family_id') or x['source_id']) for x in v} for kind, v in groups.items()}
    if not demo and any(sources[a] & sources[b] for a, b in
                        (('train', 'validation'), ('train', 'test'), ('validation', 'test'))):
        raise ValueError('Independent evaluation requires source-family-disjoint splits')
    pairs = (('train', 'validation'), ('train', 'test'), ('validation', 'test'))
    revisions = {kind: {r['source_revision'] for r in subset
                        if isinstance(r.get('source_revision'), str) and r['source_revision']}
                 for kind, subset in groups.items()}
    if not demo and any(revisions[a] & revisions[b] for a, b in pairs):
        raise ValueError('Independent evaluation requires source-revision-disjoint splits')
    # Duplicate question/passage pairs can leak even if renamed as new sources.
    fingerprints = {kind: {
        hashlib.sha256((r['question'].strip().casefold() + '\\n' + r['passage'].strip().casefold()).encode('utf-8')).hexdigest()
        for r in subset
    } for kind, subset in groups.items()}
    if not demo and any(fingerprints[a] & fingerprints[b] for a, b in pairs):
        raise ValueError('Independent evaluation contains duplicated question/passage pairs across splits')
    return groups


def encode(row, vocab, *, max_passage=256, max_question=48):
    q = tokenize(row['question']); p = tokenize(row['passage'])
    if len(q) > max_question or len(p) > max_passage or not p or not q:
        raise ValueError('Input exceeds model token budget')
    qids = [vocab.get(t, 1) for t, _, _ in q]
    pids = [0] + [vocab.get(t, 1) for t, _, _ in p]
    return (qids + [0] * (max_question - len(qids)),
            pids + [0] * (max_passage + 1 - len(pids)),
            [False] + [True] * len(p))


class NeuralPassageReader(nn.Module):
    def __init__(self, vocab_size, embedding=48, hidden=48):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, embedding, padding_idx=0)
        self.encoder = nn.GRU(embedding, hidden, bidirectional=True, batch_first=True)
        self.qproj = nn.Linear(embedding, hidden * 2)
        self.scorer = nn.Sequential(nn.Linear(hidden * 6, hidden), nn.Tanh(), nn.Dropout(.08), nn.Linear(hidden, 2))
        self.null = nn.Linear(hidden * 4, 2)

    def forward(self, query, passage, valid):
        qembed = self.emb(query)
        qmask = (query != 0).unsqueeze(-1)
        q = (qembed * qmask).sum(dim=1) / qmask.sum(dim=1).clamp(min=1)
        encoded, _ = self.encoder(self.emb(passage))
        question = self.qproj(q)
        qrep = question.unsqueeze(1).expand_as(encoded)
        scores = self.scorer(torch.cat((encoded, qrep, encoded * qrep), dim=-1))
        masked = scores.masked_fill(~valid.unsqueeze(-1), -1e8)
        null_logits = self.null(torch.cat((question, encoded[:, 1:, :].mean(dim=1)), dim=-1))
        # Class 0 means no-answer; mask other padding positions.
        return torch.cat((null_logits.unsqueeze(1), masked[:, 1:]), dim=1).transpose(1, 2)


def tensorize(rows, vocab):
    values = [encode(row, vocab) for row in rows]
    q = torch.tensor([v[0] for v in values], dtype=torch.long)
    p = torch.tensor([v[1] for v in values], dtype=torch.long)
    m = torch.tensor([[True] + v[2][1:] + [False] * (256 - len(v[2]) + 1)
                      if len(v[2]) < 257 else [True] + v[2][1:] for v in values], dtype=torch.bool)
    labels = torch.tensor([verify_example(x) for x in rows], dtype=torch.long)
    return q, p, m, labels


def metric(model, rows, vocab):
    model.eval()
    q, p, m, labels = tensorize(rows, vocab)
    with torch.inference_mode():
        logits = model(q, p, m)
        predicted = logits.argmax(dim=-1)
        exact = (predicted == labels).all(dim=-1).tolist()
    no_answer_total = sum(1 for a, b in labels.tolist() if a == b == 0)
    return {'count': len(rows), 'span_exact_match': sum(exact) / len(exact),
            'span_correct': sum(exact), 'unanswerable_examples': no_answer_total,
            'answerable_examples': len(rows) - no_answer_total}


def train_reader(rows, output, *, epochs=90, seed=33, demo=False, overwrite=False,
                 embedding=48, hidden=48):
    splits = validate_splits(rows, demo=demo)
    if type(epochs) is not int or epochs < 1 or epochs > 1000:
        raise ValueError('epochs must be integer in 1..1000')
    torch.manual_seed(seed); random.seed(seed); torch.set_num_threads(1)
    vocab = make_vocab(splits['train'])
    model = NeuralPassageReader(len(vocab), embedding=embedding, hidden=hidden)
    optim = torch.optim.AdamW(model.parameters(), lr=.003, weight_decay=1e-4)
    q, p, m, labels = tensorize(splits['train'], vocab)
    vq, vp, vm, vl = tensorize(splits['validation'], vocab)
    best_loss = float('inf'); best_epoch = 0; patience = 0; best_state = None
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(q))
        for indices in order.split(8):
            optim.zero_grad(set_to_none=True)
            scores = model(q[indices], p[indices], m[indices])
            loss = nn.functional.cross_entropy(scores[:, 0], labels[indices, 0]) + \
                   nn.functional.cross_entropy(scores[:, 1], labels[indices, 1])
            if not torch.isfinite(loss):
                raise ValueError('Non-finite reader training loss')
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
        model.eval()
        with torch.inference_mode():
            val_scores = model(vq, vp, vm)
            val_loss = (nn.functional.cross_entropy(val_scores[:, 0], vl[:, 0]) +
                        nn.functional.cross_entropy(val_scores[:, 1], vl[:, 1])).item()
        if val_loss < best_loss - 1e-4:
            best_loss, best_epoch, patience = val_loss, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience += 1
            if patience >= 18:
                break
    model.load_state_dict(best_state)
    output = Path(output)
    if output.exists() and not overwrite:
        raise ValueError('Output directory already exists')
    output.mkdir(parents=True, exist_ok=True)
    def dump(name, value):
        (output / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    metrics = {name: metric(model, subset, vocab) for name, subset in splits.items()}
    dump('vocab.json', vocab)
    dump('metrics.json', metrics)
    torch.save(model.state_dict(), output / 'model.pt')
    hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
              for name in ('vocab.json', 'metrics.json', 'model.pt')}
    manifest = {'schema': SCHEMA, 'experimental': True, 'demo': bool(demo),
                'architecture': {'embedding': embedding, 'hidden': hidden, 'max_passage': 256, 'max_question': 48},
                'best_epoch': best_epoch, 'train_sources': sorted({r['source_id'] for r in splits['train']}),
                'validation_sources': sorted({r['source_id'] for r in splits['validation']}),
                'test_sources': sorted({r['source_id'] for r in splits['test']}),
                'artifacts': hashes, 'parameter_count': sum(x.numel() for x in model.parameters()),
                'limitations': 'Uncalibrated experimental model; not independently accepted for pathology diagnosis.'}
    dump('manifest.json', manifest)
    return {'manifest': manifest, 'metrics': metrics}


class PassageReaderBundle:
    def __init__(self, path, *, allow_experimental=False):
        path = Path(path)
        manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('schema') != SCHEMA:
            raise ValueError('Incompatible reader bundle')
        if manifest.get('experimental') and not allow_experimental:
            raise ValueError('Experimental reader is disabled by default')
        for name, expected in manifest['artifacts'].items():
            if hashlib.sha256((path / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Reader artifact checksum mismatch')
        self.vocab = json.loads((path / 'vocab.json').read_text(encoding='utf-8'))
        arch = manifest['architecture']
        self.model = NeuralPassageReader(len(self.vocab), embedding=arch['embedding'], hidden=arch['hidden'])
        self.model.load_state_dict(torch.load(path / 'model.pt', map_location='cpu', weights_only=True))
        self.model.eval()
        self.manifest = manifest

    def predict(self, question, passage, *, min_score=0.0):
        row = {'question': question, 'passage': passage}
        q, p, mask = encode(row, self.vocab)
        mask = [True] + mask[1:] + [False] * (257 - len(mask))
        with torch.inference_mode():
            logits = self.model(torch.tensor([q]), torch.tensor([p]), torch.tensor([mask]))
            probabilities = logits.softmax(dim=-1)
            starts = probabilities[0, 0]
            ends = probabilities[0, 1]
            if float(starts[0] * ends[0]) >= .5:
                return {'status': 'no_answer', 'answer': None, 'score_type': 'uncalibrated_span_product'}
            # Joint span search allows positions in increasing order, max 30 tokens.
            best = (0.0, 0, 0)
            valid_len = len(tokenize(passage))
            for start in range(1, valid_len + 1):
                hi = min(start + 30, valid_len + 1)
                values = starts[start] * ends[start:hi]
                candidate, offset = float(values.max()), int(values.argmax())
                if candidate > best[0]:
                    best = candidate, start, start + offset
            score, si, ei = best
            if score < min_score or score <= float(starts[0] * ends[0]):
                return {'status': 'no_answer', 'answer': None,
                        'score': score, 'score_type': 'uncalibrated_span_product'}
            tokens = tokenize(passage)
            lo, hi = tokens[si - 1][1], tokens[ei - 1][2]
            return {'status': 'experimental_answer', 'answer': passage[lo:hi],
                    'start': lo, 'end': hi, 'score': score,
                    'score_type': 'uncalibrated_span_product'}
