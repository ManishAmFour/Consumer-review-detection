"""
tokenizer.py
------------
Minimal, dependency-light tokenizer for the text branch.

Design choices (all explicit, none hidden):
- Whitespace + punctuation-aware regex tokenization (no external tokenizer
  library required -- keeps the pipeline reproducible and dependency-light).
- Vocabulary is fit ONLY on the training split (enforced by caller passing
  only training texts to `fit`).
- Special tokens: <pad>=0, <unk>=1.
- Sequences are padded/truncated to a fixed max_seq_len (256 per spec).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Dict, List, Optional

PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"
PAD_ID = 0
UNK_ID = 1

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?|[^\sa-z0-9]", re.IGNORECASE)


def normalize_text(text: str, lowercase: bool = True) -> str:
    if text is None:
        text = ""
    text = str(text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"http\S+|www\.\S+", " <url> ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if lowercase:
        text = text.lower()
    return text


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text)


class Tokenizer:
    def __init__(
        self,
        max_seq_len: int = 256,
        lowercase: bool = True,
        min_token_freq: int = 1,
        vocab_size_cap: Optional[int] = None,
    ):
        self.max_seq_len = max_seq_len
        self.lowercase = lowercase
        self.min_token_freq = min_token_freq
        self.vocab_size_cap = vocab_size_cap
        self.token2id: Dict[str, int] = {PAD_TOKEN: PAD_ID, UNK_TOKEN: UNK_ID}
        self.id2token: Dict[int, str] = {PAD_ID: PAD_TOKEN, UNK_ID: UNK_TOKEN}
        self._fitted = False

    # ------------------------------------------------------------------
    def fit(self, texts: List[str]) -> "Tokenizer":
        """
        Build vocabulary. `texts` MUST be the TRAINING split only -- the
        caller is responsible for that split boundary; this class does not
        know about splits and will happily overfit its vocab to whatever
        it's given, by design (so misuse is visible, not hidden).
        """
        counter: Counter = Counter()
        for t in texts:
            norm = normalize_text(t, self.lowercase)
            counter.update(tokenize(norm))

        items = [(tok, freq) for tok, freq in counter.items() if freq >= self.min_token_freq]
        items.sort(key=lambda x: (-x[1], x[0]))  # freq desc, then lexicographic (deterministic)

        if self.vocab_size_cap is not None:
            items = items[: self.vocab_size_cap]

        next_id = 2
        for tok, _freq in items:
            if tok not in self.token2id:
                self.token2id[tok] = next_id
                self.id2token[next_id] = tok
                next_id += 1

        self._fitted = True
        return self

    # ------------------------------------------------------------------
    @property
    def vocab_size(self) -> int:
        return len(self.token2id)

    def encode(self, text: str) -> List[int]:
        norm = normalize_text(text, self.lowercase)
        toks = tokenize(norm)
        ids = [self.token2id.get(t, UNK_ID) for t in toks]
        ids = ids[: self.max_seq_len]
        attn_len = len(ids)
        if len(ids) < self.max_seq_len:
            ids = ids + [PAD_ID] * (self.max_seq_len - len(ids))
        return ids, attn_len  # attn_len used to build the mask for masked-mean pooling

    def encode_batch(self, texts: List[str]):
        ids_batch, lens = [], []
        for t in texts:
            ids, length = self.encode(t)
            ids_batch.append(ids)
            lens.append(length)
        return ids_batch, lens

    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        payload = {
            "max_seq_len": self.max_seq_len,
            "lowercase": self.lowercase,
            "min_token_freq": self.min_token_freq,
            "vocab_size_cap": self.vocab_size_cap,
            "token2id": self.token2id,
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Tokenizer":
        with open(path, "r") as f:
            payload = json.load(f)
        tok = cls(
            max_seq_len=payload["max_seq_len"],
            lowercase=payload["lowercase"],
            min_token_freq=payload["min_token_freq"],
            vocab_size_cap=payload["vocab_size_cap"],
        )
        tok.token2id = {k: int(v) for k, v in payload["token2id"].items()}
        tok.id2token = {v: k for k, v in tok.token2id.items()}
        tok._fitted = True
        return tok


if __name__ == "__main__":
    # Tiny self-test (no dataset required) -- validates tokenizer logic only.
    sample_train = [
        "The food was Amazing!! Best pizza in town :)",
        "Terrible service, cold food, never coming back.",
    ]
    tok = Tokenizer(max_seq_len=16).fit(sample_train)
    ids, length = tok.encode("Amazing pizza, terrible unknown_word_xyz!")
    print("vocab_size:", tok.vocab_size)
    print("ids:", ids)
    print("real_length (pre-pad):", length)
    assert len(ids) == 16
    print("Tokenizer self-test passed.")
