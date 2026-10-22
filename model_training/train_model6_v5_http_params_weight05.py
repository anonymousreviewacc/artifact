"""Reproducible candidate training for PLGenN Model 6.

All inputs and outputs are resolved beneath this script's directory. This script
does not import, edit, build, or install the Android application.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import pickle
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
from sklearn.metrics import (classification_report, confusion_matrix,
                             precision_recall_fscore_support, accuracy_score,
                             f1_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "00_data"
RUN_DIR = ROOT / "candidate_v5_http_params_weight05_family_split_20261010"
MODEL_DIR = RUN_DIR / "01_model"
EVAL_DIR = RUN_DIR / "02_evaluation"
FIG_DIR = RUN_DIR / "03_figures"
LOG_DIR = RUN_DIR / "04_logs"
for folder in (MODEL_DIR, EVAL_DIR, FIG_DIR, LOG_DIR):
    folder.mkdir(parents=True, exist_ok=True)

SOURCE_DATA = DATA_DIR / "original_89256_dataset.json"
SUPPLEMENT = DATA_DIR / "supplemental_curated_payloads_v4_http_params.json"
SEED = 45
SEQ_LEN = 100
VOCAB_SIZE = 20_000
BATCH_SIZE = 256
MAX_EPOCHS = 15
VAL_FRACTION = 0.20

# Preserve the class order used by the existing Model 5 TFLite output.
CATEGORY_NAMES = [
    "SQL", "XSS", "IDOR", "CMD", "PATH", "SSRF", "LFI",
    "OPEN_REDIRECT", "XXE", "GRAPHQL", "API_ABUSE", "RFI"
]
CATEGORY_TO_ID = {name: i for i, name in enumerate(CATEGORY_NAMES)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_family(payload: str) -> str:
    """Approximate a template family; it is a conservative heuristic, not provenance."""
    s = unquote(str(payload)).strip().lower()
    s = re.sub(r"https?://", lambda m: m.group(0) + "<HOST>", s)
    s = re.sub(r"(?i)(https?://<HOST>)(?:\[[^\]]+\]|[^/\s:?#]+)", r"\1", s)
    s = re.sub(r"(?i)(https?://<HOST>)(?::\d+)", r"\1:<PORT>", s)
    s = re.sub(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", "<UUID>", s)
    s = re.sub(r"\b0x[0-9a-f]+\b", "<HEX>", s)
    s = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>", s)
    s = re.sub(r"\b\d{5,}\b", "<LONGNUM>", s)
    s = re.sub(r"\b\d+\b", "<N>", s)
    s = re.sub(r"\s+", " ", s)
    return s


def compute_ltig(payload: str) -> list[float]:
    tokens = str(payload).split()
    if not tokens:
        return [0.0] * 8
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    node_score = sum(np.sqrt(v) for v in freq.values())
    node_density = node_score / max(len(payload), 1)
    unique_nodes = len(freq)
    token_count = len(tokens)
    adjacent_pairs = max(0, token_count - 1)
    pairset = {tokens[i] + "_" + tokens[i + 1] for i in range(token_count - 1)}
    unique_pairs = len(pairset)
    repetition_ratio = sum(freq.values()) / max(unique_nodes, 1)
    graph_density = unique_pairs / max(token_count, 1)
    return [node_density, (unique_nodes / 2) / 50, unique_nodes / 50,
            token_count / 100, adjacent_pairs / 100, unique_pairs / 100,
            repetition_ratio / 10, graph_density]


def load_records():
    original = json.loads(SOURCE_DATA.read_text(encoding="utf-8"))
    supplemental_obj = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))
    supplemental = supplemental_obj["records"]
    # Group repeated text before splitting. Keep category labels (there are no
    # cross-category exact-text collisions in the inspected original corpus).
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in original:
        cat = str(row["category"]).upper().strip()
        if cat in CATEGORY_TO_ID and str(row.get("payload", "")).strip():
            grouped[(cat, str(row["payload"]))].append(row)

    records = []
    original_duplicate_groups = 0
    ambiguous_obf = 0
    ambiguous_pattern = 0
    for (cat, payload), rows in grouped.items():
        if len(rows) > 1:
            original_duplicate_groups += 1
        pats = Counter(str(r.get("pattern", "OTHER")).upper().strip() for r in rows)
        obfs = {str(r.get("obfuscation", "")).upper().strip() for r in rows}
        if len(pats) == 1:
            pattern, pattern_mask = next(iter(pats)), 1.0
        else:
            # No reliable tie-breaker exists for inconsistent labels.
            pattern, pattern_mask = pats.most_common(1)[0][0], 0.0
            ambiguous_pattern += 1
        if len(obfs) == 1:
            obf, obf_mask = next(iter(obfs)), 1.0
        else:
            # Same text occurs under multiple execution-profile labels. Exclude
            # it from obfuscation-head loss and scoring, while retaining it for
            # category and pattern learning.
            obf, obf_mask = "BASIC", 0.0
            ambiguous_obf += 1
        records.append({
            "payload": payload, "category": cat, "pattern": pattern,
            "obfuscation": obf, "obf_mask": obf_mask,
            "pattern_mask": pattern_mask, "source": "original_89256",
        })

    supplemental_added = 0
    supplemental_duplicates = 0
    seen_payloads = {r["payload"] for r in records}
    for row in supplemental:
        payload = str(row["payload"]).strip()
        cat = str(row["category"]).upper().strip()
        pat = str(row["pattern"]).upper().strip()
        if cat not in CATEGORY_TO_ID or not payload:
            raise ValueError(f"Invalid supplemental category or empty payload: {row}")
        if payload in seen_payloads:
            supplemental_duplicates += 1
            continue
        records.append({
            "payload": payload, "category": cat, "pattern": pat,
            "obfuscation": str(row.get("obfuscation", "BASIC")).upper(),
            "obf_mask": float(row.get("obf_mask", 0.0)),
            "pattern_mask": float(row.get("pattern_mask", 1.0)),
            "source": str(row.get("source", "curated_supplemental")),
        })
        seen_payloads.add(payload)
        supplemental_added += 1

    if not records:
        raise RuntimeError("No usable training records")
    return records, {
        "original_rows": len(original),
        "original_unique_category_payloads": len(grouped),
        "original_duplicate_payload_groups": original_duplicate_groups,
        "original_rows_removed_by_dedup": len(original) - len(grouped),
        "unique_payloads_with_conflicting_obfuscation_labels": ambiguous_obf,
        "unique_payloads_with_conflicting_pattern_labels": ambiguous_pattern,
        "supplemental_records_in_source_file": len(supplemental),
        "supplemental_exact_duplicates_omitted": supplemental_duplicates,
        "supplemental_records_added": supplemental_added,
        "raw_rows_before_exact_dedup_including_supplement": len(original) + len(supplemental),
        "total_unique_records_after_merge": len(records),
    }


def choose_group_fold(labels: np.ndarray, groups: np.ndarray, n_splits: int,
                      target_fraction: float, random_state: int):
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    candidates = []
    all_ids = np.arange(len(labels))
    class_count = np.bincount(labels, minlength=len(CATEGORY_NAMES))
    for fold, (train, val) in enumerate(splitter.split(all_ids, labels, groups)):
        val_count = np.bincount(labels[val], minlength=len(CATEGORY_NAMES))
        frac_error = abs(len(val) / len(labels) - target_fraction)
        coverage_penalty = int(np.sum(val_count == 0)) * 2.0
        count_error = np.mean(np.abs(val_count / np.maximum(class_count, 1) - target_fraction))
        # Prefer all classes represented, then the requested held-out fraction.
        score = coverage_penalty + frac_error + count_error
        candidates.append((score, fold, train, val, val_count))
    candidates.sort(key=lambda x: x[0])
    score, fold, train, val, val_count = candidates[0]
    if np.any(val_count == 0):
        missing = [CATEGORY_NAMES[i] for i, c in enumerate(val_count) if c == 0]
        raise RuntimeError(f"Family split omitted categories at {target_fraction:.3f} fraction: {missing}")
    return train, val, {"selected_fold": fold, "split_score": float(score),
                        "complement_rows": len(train), "heldout_rows": len(val),
                        "heldout_fraction": len(val) / len(labels),
                        "heldout_support": {CATEGORY_NAMES[i]: int(v) for i, v in enumerate(val_count)}}


def make_splits(labels: np.ndarray, groups: np.ndarray):
    outer_train_dev, test_idx, outer = choose_group_fold(
        labels, groups, n_splits=5, target_fraction=0.20, random_state=20261015)
    inner_train, dev_local, inner = choose_group_fold(
        labels[outer_train_dev], groups[outer_train_dev], n_splits=8,
        target_fraction=0.125, random_state=20261016)
    train_idx = outer_train_dev[inner_train]
    dev_idx = outer_train_dev[dev_local]
    train_groups, dev_groups, test_groups = map(lambda ix: set(groups[ix]),
                                                (train_idx, dev_idx, test_idx))
    if train_groups & dev_groups or train_groups & test_groups or dev_groups & test_groups:
        raise RuntimeError("Family leakage detected across train/development/test")
    details = {
        "method": "outer StratifiedGroupKFold(5) test holdout; inner StratifiedGroupKFold(8) development holdout",
        "outer_test_fold": outer, "inner_development_fold": inner,
        "train_rows": int(len(train_idx)), "development_rows": int(len(dev_idx)),
        "test_rows": int(len(test_idx)),
        "train_fraction": float(len(train_idx) / len(labels)),
        "development_fraction": float(len(dev_idx) / len(labels)),
        "test_fraction": float(len(test_idx) / len(labels)),
        "train_groups": int(len(train_groups)), "development_groups": int(len(dev_groups)),
        "test_groups": int(len(test_groups)),
        "test_support": {CATEGORY_NAMES[i]: int(v) for i, v in enumerate(np.bincount(labels[test_idx], minlength=len(CATEGORY_NAMES)))},
    }
    return train_idx, dev_idx, test_idx, details


def class_sample_weights(y: np.ndarray, mask: np.ndarray | None = None):
    weights = np.ones(len(y), dtype=np.float32)
    active = np.ones(len(y), dtype=bool) if mask is None else mask.astype(bool)
    counts = Counter(y[active].tolist())
    if not counts:
        return np.zeros(len(y), dtype=np.float32), {}
    active_count = int(active.sum())
    raw = {k: (active_count / (len(counts) * v)) ** 0.5
           for k, v in counts.items()}
    scale = np.mean(list(raw.values()))
    raw = {k: v / scale for k, v in raw.items()}
    for i, label in enumerate(y):
        weights[i] = raw.get(int(label), 1.0) if active[i] else 0.0
    return weights, {str(k): float(v) for k, v in raw.items()}


def write_csv(path: Path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_family_ci(y_true, y_pred, groups, replicates=300):
    rng = np.random.default_rng(SEED)
    unique = np.unique(groups)
    group_to_idx = {g: np.flatnonzero(groups == g) for g in unique}
    values = np.full((replicates, len(CATEGORY_NAMES)), np.nan)
    macro = np.full(replicates, np.nan)
    for b in range(replicates):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([group_to_idx[g] for g in sampled])
        _, _, f1s, _ = precision_recall_fscore_support(
            y_true[idx], y_pred[idx], labels=np.arange(len(CATEGORY_NAMES)),
            zero_division=0
        )
        values[b] = f1s
        macro[b] = float(np.mean(f1s))
    out = []
    for i, name in enumerate(CATEGORY_NAMES):
        out.append({"class": name, "f1_ci95_low": float(np.nanpercentile(values[:, i], 2.5)),
                    "f1_ci95_high": float(np.nanpercentile(values[:, i], 97.5))})
    out.append({"class": "MACRO_F1", "f1_ci95_low": float(np.nanpercentile(macro, 2.5)),
                "f1_ci95_high": float(np.nanpercentile(macro, 97.5))})
    return out


class DevelopmentMacroF1(tf.keras.callbacks.Callback):
    """Select the checkpoint using category macro-F1 on development families."""
    def __init__(self, x_dev, y_dev):
        super().__init__()
        self.x_dev = x_dev
        self.y_dev = y_dev

    def on_epoch_end(self, epoch, logs=None):
        outputs = self.model.predict(self.x_dev, batch_size=BATCH_SIZE, verbose=0)
        pred = outputs["category"].argmax(axis=1)
        score = float(f1_score(self.y_dev, pred, average="macro", zero_division=0))
        if logs is not None:
            logs["val_category_macro_f1"] = score
        print(f" - val_category_macro_f1: {score:.4f}")


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    tf.keras.utils.set_random_seed(SEED)
    try:
        tf.config.threading.set_intra_op_parallelism_threads(4)
        tf.config.threading.set_inter_op_parallelism_threads(2)
    except RuntimeError:
        pass

    records, audit = load_records()
    if not SOURCE_DATA.is_file() or not SUPPLEMENT.is_file():
        raise FileNotFoundError("Required input files are missing")
    payloads = np.asarray([r["payload"] for r in records], dtype=object)
    y_cat = np.asarray([CATEGORY_TO_ID[r["category"]] for r in records], dtype=np.int32)
    pattern_encoder = LabelEncoder().fit([r["pattern"] for r in records])
    obf_encoder = LabelEncoder().fit([r["obfuscation"] for r in records if r["obf_mask"] > 0])
    y_pat = pattern_encoder.transform([r["pattern"] for r in records]).astype(np.int32)
    y_obf = np.zeros(len(records), dtype=np.int32)
    obf_indices = [i for i, r in enumerate(records) if r["obf_mask"] > 0]
    if obf_indices:
        encoded_obf = obf_encoder.transform([records[i]["obfuscation"] for i in obf_indices])
        y_obf[np.asarray(obf_indices)] = encoded_obf
    pat_mask = np.asarray([r["pattern_mask"] for r in records], dtype=np.float32)
    obf_mask = np.asarray([r["obf_mask"] for r in records], dtype=np.float32)
    family = np.asarray([canonical_family(p) for p in payloads], dtype=object)
    groups = np.asarray([hashlib.sha1(g.encode("utf-8")).hexdigest()[:16] for g in family], dtype=object)

    train_idx, dev_idx, test_idx, split = make_splits(y_cat, groups)
    # The vocabulary and numerical scaler are fitted on training only.
    # Match Model 5's punctuation-filtering Tokenizer behavior rather than
    # treating most complete payload strings as one token.
    tokenizer = Tokenizer(num_words=VOCAB_SIZE, oov_token="<UNK>")
    tokenizer.fit_on_texts(payloads[train_idx].tolist())
    X_text = pad_sequences(tokenizer.texts_to_sequences(payloads.tolist()),
                           maxlen=SEQ_LEN, padding="pre", truncating="pre")
    raw_ltig = np.asarray([compute_ltig(p) for p in payloads], dtype=np.float32)
    scaler = StandardScaler().fit(raw_ltig[train_idx])
    X_ltig = scaler.transform(raw_ltig).astype(np.float32)

    y_cat_train, y_cat_dev = y_cat[train_idx], y_cat[dev_idx]
    y_pat_train, y_pat_dev = y_pat[train_idx], y_pat[dev_idx]
    y_obf_train, y_obf_dev = y_obf[train_idx], y_obf[dev_idx]
    pat_train_mask, pat_dev_mask = pat_mask[train_idx], pat_mask[dev_idx]
    obf_train_mask, obf_dev_mask = obf_mask[train_idx], obf_mask[dev_idx]
    w_cat_train, cw_cat = class_sample_weights(y_cat_train)
    w_pat_train, cw_pat = class_sample_weights(y_pat_train, pat_train_mask)
    w_obf_train, cw_obf = class_sample_weights(y_obf_train, obf_train_mask)
    w_cat_dev, _ = class_sample_weights(y_cat_dev)
    w_pat_dev, _ = class_sample_weights(y_pat_dev, pat_dev_mask)
    w_obf_dev, _ = class_sample_weights(y_obf_dev, obf_dev_mask)

    # Preserve the Model 5 embedding + LTIG + three-head architecture.
    text_input = tf.keras.Input(shape=(SEQ_LEN,), dtype="int32", name="text_input")
    emb = tf.keras.layers.Embedding(VOCAB_SIZE, 128, name="embedding")(text_input)
    pooled = tf.keras.layers.GlobalAveragePooling1D(name="text_pool")(emb)
    ltig_input = tf.keras.Input(shape=(8,), dtype="float32", name="ltig_input")
    merged = tf.keras.layers.Concatenate(name="fusion")([pooled, ltig_input])
    x = tf.keras.layers.Dense(256, activation="relu", name="dense_256")(merged)
    x = tf.keras.layers.Dropout(0.4, name="dropout_04")(x)
    x = tf.keras.layers.Dense(128, activation="relu", name="dense_128")(x)
    x = tf.keras.layers.Dropout(0.3, name="dropout_03")(x)
    out_cat = tf.keras.layers.Dense(len(CATEGORY_NAMES), activation="softmax", name="category")(x)
    out_pat = tf.keras.layers.Dense(len(pattern_encoder.classes_), activation="softmax", name="pattern")(x)
    out_obf = tf.keras.layers.Dense(len(obf_encoder.classes_), activation="softmax", name="obfuscation")(x)
    model = tf.keras.Model([text_input, ltig_input],
                           {"category": out_cat, "pattern": out_pat, "obfuscation": out_obf},
                           name="PLGenN_Model6")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss={"category": "sparse_categorical_crossentropy",
              "pattern": "sparse_categorical_crossentropy",
              "obfuscation": "sparse_categorical_crossentropy"},
        loss_weights={"category": 1.0, "pattern": 0.4, "obfuscation": 0.4},
        metrics={"category": ["accuracy"], "pattern": ["accuracy"], "obfuscation": ["accuracy"]},
    )
    callbacks = [
        DevelopmentMacroF1([X_text[dev_idx], X_ltig[dev_idx]], y_cat_dev),
        tf.keras.callbacks.EarlyStopping(monitor="val_category_macro_f1", mode="max",
                                         patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_category_loss", factor=0.5,
                                              patience=2, min_lr=1e-5, mode="min", verbose=1),
        tf.keras.callbacks.CSVLogger(str(LOG_DIR / "epoch_history.csv")),
    ]
    y_train = {"category": y_cat_train, "pattern": y_pat_train, "obfuscation": y_obf_train}
    sw_train = {"category": w_cat_train, "pattern": w_pat_train, "obfuscation": w_obf_train}
    y_dev = {"category": y_cat_dev, "pattern": y_pat_dev, "obfuscation": y_obf_dev}
    sw_dev = {"category": w_cat_dev, "pattern": w_pat_dev, "obfuscation": w_obf_dev}

    config = {
        "model": "PLGenN Model 6 candidate",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED, "sequence_length": SEQ_LEN, "vocabulary_limit": VOCAB_SIZE,
        "batch_size": BATCH_SIZE, "max_epochs": MAX_EPOCHS,
        "architecture": "Model 5 embedding + 8 LTIG features + 12-category/pattern/obfuscation heads",
        "category_order": CATEGORY_NAMES,
        "pattern_labels": pattern_encoder.classes_.tolist(),
        "obfuscation_labels": obf_encoder.classes_.tolist(),
        "split_method": "outer StratifiedGroupKFold(5) test holdout; inner StratifiedGroupKFold(8) development holdout; test used once after epoch selection",
        "family_grouping": "heuristic canonicalization of URL host, numeric IDs, IPs, hex values, and whitespace; not verified source/family metadata",
        "preprocessing_fit": "tokenizer and StandardScaler fit on training partition only",
        "balancing": "normalized inverse-frequency sample weights raised to 0.5, training partition only; no row duplication",
        "class_weight_exponent": 0.5,
        "tokenizer": "Keras Tokenizer default punctuation filters, matching Model 5 preprocessing",
        "loss_weights": {"category": 1.0, "pattern": 0.4, "obfuscation": 0.4},
        "checkpoint_selection": "development-family category macro-F1; final test partition not used for epoch selection",
        "independence_caveat": "the source corpus was previously used in Model 5 and exploratory Model 6 runs; this is a family-held-out evaluation for this fit, not an untouched external confirmation set",
        "ambiguous_obfuscation": "same exact payload with conflicting profile labels is masked from obfuscation-head loss and evaluation",
        "test_family_bootstrap_replicates": 300,
        "tensorflow": tf.__version__, "numpy": np.__version__,
        "input_sha256": sha256(SOURCE_DATA), "supplement_sha256": sha256(SUPPLEMENT),
        "audit": audit, "split": split,
        "training_class_counts": {CATEGORY_NAMES[i]: int(v) for i, v in enumerate(np.bincount(y_cat_train, minlength=len(CATEGORY_NAMES)))},
        "development_class_counts": {CATEGORY_NAMES[i]: int(v) for i, v in enumerate(np.bincount(y_cat_dev, minlength=len(CATEGORY_NAMES)))},
        "test_class_counts": {CATEGORY_NAMES[i]: int(v) for i, v in enumerate(np.bincount(y_cat[test_idx], minlength=len(CATEGORY_NAMES)))},
        "class_weight_category": cw_cat, "class_weight_pattern": cw_pat, "class_weight_obfuscation": cw_obf,
    }
    (EVAL_DIR / "run_config_and_data_audit.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    split_rows = []
    subset = np.full(len(records), "train", dtype=object)
    subset[dev_idx] = "development"
    subset[test_idx] = "test"
    for i, row in enumerate(records):
        split_rows.append({"row_id": i, "subset": subset[i], "category": row["category"],
                           "source": row["source"], "family_group": groups[i],
                           "pattern_label_mask": int(pat_mask[i] > 0),
                           "obfuscation_label_mask": int(obf_mask[i] > 0)})
    write_csv(EVAL_DIR / "family_split_manifest.csv", split_rows)

    print(f"Training Model 6 candidate on {len(train_idx):,} records; development={len(dev_idx):,}; untouched test={len(test_idx):,}; families={len(np.unique(groups)):,}")
    print("Category support (train):", {CATEGORY_NAMES[i]: int(v) for i, v in enumerate(np.bincount(y_cat_train, minlength=len(CATEGORY_NAMES)))})
    print(f"Obfuscation-head labeled training rows: {int(obf_train_mask.sum()):,}/{len(train_idx):,}")
    history = model.fit(
        [X_text[train_idx], X_ltig[train_idx]], y_train,
        sample_weight=sw_train,
        validation_data=([X_text[dev_idx], X_ltig[dev_idx]], y_dev, sw_dev),
        epochs=MAX_EPOCHS, batch_size=BATCH_SIZE, callbacks=callbacks,
        verbose=2,
    )

    predictions = model.predict([X_text[test_idx], X_ltig[test_idx]], batch_size=BATCH_SIZE, verbose=0)
    cat_prob = predictions["category"]
    pat_prob = predictions["pattern"]
    obf_prob = predictions["obfuscation"]
    cat_pred = cat_prob.argmax(axis=1)
    pat_pred = pat_prob.argmax(axis=1)
    obf_pred = obf_prob.argmax(axis=1)
    y_cat_test, y_pat_test, y_obf_test = y_cat[test_idx], y_pat[test_idx], y_obf[test_idx]
    pat_test_mask, obf_test_mask = pat_mask[test_idx], obf_mask[test_idx]
    cat_report = classification_report(y_cat_test, cat_pred, labels=np.arange(len(CATEGORY_NAMES)),
                                       target_names=CATEGORY_NAMES, digits=4, zero_division=0, output_dict=True)
    cat_text = classification_report(y_cat_test, cat_pred, labels=np.arange(len(CATEGORY_NAMES)),
                                     target_names=CATEGORY_NAMES, digits=4, zero_division=0)
    (EVAL_DIR / "category_classification_report.txt").write_text(cat_text, encoding="utf-8")
    pat_sel = pat_test_mask > 0
    obf_sel = obf_test_mask > 0
    pat_text = classification_report(y_pat_test[pat_sel], pat_pred[pat_sel],
                                     labels=np.arange(len(pattern_encoder.classes_)),
                                     target_names=pattern_encoder.classes_.tolist(), digits=4, zero_division=0)
    obf_text = classification_report(y_obf_test[obf_sel], obf_pred[obf_sel],
                                     labels=np.arange(len(obf_encoder.classes_)),
                                     target_names=obf_encoder.classes_.tolist(), digits=4, zero_division=0)
    (EVAL_DIR / "pattern_head_report.txt").write_text(pat_text, encoding="utf-8")
    (EVAL_DIR / "obfuscation_head_report.txt").write_text(obf_text, encoding="utf-8")

    # Category results with family-cluster bootstrap intervals.
    test_groups = groups[test_idx]
    ci_rows = bootstrap_family_ci(y_cat_test, cat_pred, test_groups)
    report_rows = []
    for i, name in enumerate(CATEGORY_NAMES):
        item = cat_report[name]
        ci = next(x for x in ci_rows if x["class"] == name)
        report_rows.append({"class": name, "precision": item["precision"], "recall": item["recall"],
                            "f1": item["f1-score"], "support": int(item["support"]),
                            "f1_ci95_low_family_bootstrap": ci["f1_ci95_low"],
                            "f1_ci95_high_family_bootstrap": ci["f1_ci95_high"]})
    write_csv(EVAL_DIR / "category_metrics_with_family_bootstrap_ci.csv", report_rows)
    write_csv(EVAL_DIR / "family_bootstrap_ci.csv", ci_rows)

    test_rows = []
    for local_i, global_i in enumerate(test_idx):
        row = records[global_i]
        test_rows.append({"payload": row["payload"], "true_category": row["category"],
                         "predicted_category": CATEGORY_NAMES[int(cat_pred[local_i])],
                         "category_confidence": float(cat_prob[local_i].max()),
                         "correct": bool(y_cat_test[local_i] == cat_pred[local_i]),
                         "family_group": groups[global_i], "source": row["source"],
                         "pattern_true": row["pattern"],
                         "pattern_predicted": pattern_encoder.classes_[int(pat_pred[local_i])],
                         "obfuscation_true": row["obfuscation"] if row["obf_mask"] else "AMBIGUOUS_OR_UNLABELED",
                         "obfuscation_predicted": obf_encoder.classes_[int(obf_pred[local_i])],
                         "obfuscation_in_metric": bool(row["obf_mask"])})
    write_csv(EVAL_DIR / "test_predictions.csv", test_rows)

    # Figures and tabular epoch evidence.
    hist = pd.DataFrame(history.history)
    hist.to_csv(LOG_DIR / "epoch_history_final.csv", index=False)
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for key, label in [("category_accuracy", "Category"), ("pattern_accuracy", "Pattern"), ("obfuscation_accuracy", "Obfuscation")]:
        if key in hist:
            axes[0].plot(hist.index + 1, hist[key], marker=".", label=f"{label} train")
        valkey = "val_" + key
        if valkey in hist:
            axes[0].plot(hist.index + 1, hist[valkey], linestyle="--", label=f"{label} validation")
    if "val_category_macro_f1" in hist:
        axes[0].plot(hist.index + 1, hist["val_category_macro_f1"], linestyle=":", linewidth=2.2,
                     label="Category validation macro-F1")
    axes[0].set(title="Model 6 multi-head accuracy by epoch", xlabel="Epoch", ylabel="Accuracy")
    axes[0].legend(fontsize=8)
    if "loss" in hist: axes[1].plot(hist.index + 1, hist["loss"], marker=".", label="Train joint loss")
    if "val_loss" in hist: axes[1].plot(hist.index + 1, hist["val_loss"], marker=".", label="Validation joint loss")
    axes[1].set(title="Model 6 joint loss by epoch", xlabel="Epoch", ylabel="Loss")
    axes[1].legend()
    fig.tight_layout(); fig.savefig(FIG_DIR / "01_training_history.png", dpi=220); plt.close(fig)

    cm = confusion_matrix(y_cat_test, cat_pred, labels=np.arange(len(CATEGORY_NAMES)), normalize="true")
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(cm, cmap="Blues", xticklabels=CATEGORY_NAMES, yticklabels=CATEGORY_NAMES,
                annot=True, fmt=".2f", vmin=0, vmax=1, ax=ax)
    ax.set(title="Model 6 test-set category confusion matrix (row-normalized)", xlabel="Predicted class", ylabel="True class")
    plt.xticks(rotation=45, ha="right"); plt.yticks(rotation=0); fig.tight_layout()
    fig.savefig(FIG_DIR / "02_category_confusion_matrix.png", dpi=240); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    supports = np.bincount(y_cat_test, minlength=len(CATEGORY_NAMES))
    f1s = np.asarray([cat_report[n]["f1-score"] for n in CATEGORY_NAMES])
    bars = ax.bar(CATEGORY_NAMES, f1s, color="#5267a8")
    ax.set_ylim(0, 1.05); ax.set_ylabel("F1-score"); ax.set_title("Test F1 by category with support")
    ax.set_xticks(np.arange(len(CATEGORY_NAMES)), CATEGORY_NAMES, rotation=40, ha="right")
    for bar, f1v, supp in zip(bars, f1s, supports):
        ax.text(bar.get_x() + bar.get_width()/2, min(f1v + .02, 1.01), f"n={supp}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG_DIR / "03_category_f1_support.png", dpi=220); plt.close(fig)

    pred_counts = Counter(CATEGORY_NAMES[int(x)] for x in cat_pred)
    true_counts = Counter(CATEGORY_NAMES[int(x)] for x in y_cat_test)
    ix = np.arange(len(CATEGORY_NAMES)); width = .38
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(ix - width/2, [true_counts[n] for n in CATEGORY_NAMES], width, label="True class")
    ax.bar(ix + width/2, [pred_counts[n] for n in CATEGORY_NAMES], width, label="Predicted class")
    ax.set_xticks(ix, CATEGORY_NAMES, rotation=40, ha="right"); ax.set_ylabel("Test examples")
    ax.set_title("True versus predicted category counts"); ax.legend(); fig.tight_layout()
    fig.savefig(FIG_DIR / "04_true_vs_predicted_counts.png", dpi=220); plt.close(fig)

    if pat_sel.any():
        pat_acc = accuracy_score(y_pat_test[pat_sel], pat_pred[pat_sel])
    else:
        pat_acc = float("nan")
    if obf_sel.any():
        obf_acc = accuracy_score(y_obf_test[obf_sel], obf_pred[obf_sel])
    else:
        obf_acc = float("nan")
    summary = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "test": {
            "category_accuracy": float(accuracy_score(y_cat_test, cat_pred)),
            "category_macro_f1": float(f1_score(y_cat_test, cat_pred, average="macro")),
            "category_weighted_f1": float(f1_score(y_cat_test, cat_pred, average="weighted")),
            "pattern_accuracy_on_unambiguous_labels": float(pat_acc),
            "obfuscation_accuracy_on_unambiguous_labels": float(obf_acc),
            "pattern_test_rows_scored": int(pat_sel.sum()),
            "obfuscation_test_rows_scored": int(obf_sel.sum()),
            "category_test_rows": int(len(test_idx)),
            "test_family_groups": int(len(np.unique(test_groups))),
            "category_macro_f1_family_bootstrap_ci95": next(x for x in ci_rows if x["class"] == "MACRO_F1"),
        },
        "data_audit": audit,
        "split": split,
        "notes": [
            "The original 89,256-row corpus and supplemental source records are merged, then exact duplicate payload strings are removed before the family split.",
            "The final test split groups heuristic canonical template families; the corpus lacks row-level source provenance, so this is not a source-aware split.",
            "The supplemental PATT SSRF, IDOR, and GraphQL examples have class/pattern labels but no execution-profile label; they are excluded from obfuscation-head loss.",
            "HttpParamsDataset attack rows were added only for SQL, XSS, CMD, and PATH. Its source labels do not provide the model's structural-pattern or obfuscation labels, so those two heads are masked for these rows.",
            "The HTTP parameter dataset documents that its examples were assembled from sqlmap, XSSYA, Vega Scanner, FuzzDB, and CSIC2010; source-family provenance is not available for each row.",
            "Ambiguous profile labels for identical original payloads are masked for the obfuscation head.",
            "These classifier metrics do not measure PSR, IMR, ECR, exploit confirmation, or generator behavior.",
        ],
    }
    (EVAL_DIR / "model6_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (EVAL_DIR / "model6_summary.txt").write_text(
        "MODEL 6 CANDIDATE - CLASSIFIER EVALUATION\n\n"
        f"Category accuracy: {summary['test']['category_accuracy']:.4f}\n"
        f"Category macro-F1: {summary['test']['category_macro_f1']:.4f}\n"
        f"Category weighted-F1: {summary['test']['category_weighted_f1']:.4f}\n"
        f"Pattern accuracy (unambiguous labels): {pat_acc:.4f}\n"
        f"Obfuscation accuracy (unambiguous labels): {obf_acc:.4f}\n"
        f"Category test n: {len(test_idx)}\n"
        f"Obfuscation test n scored: {int(obf_sel.sum())}\n\n"
        "Interpretation: classifier-only metrics. They do not establish or update runtime PSR, IMR, or ECR.\n"
        "The split uses heuristic template-family groups, not verified source provenance.\n",
        encoding="utf-8")

    # Save artifacts with labels and preprocessing state. They are not installed
    # into or copied to the Android project.
    model.save(MODEL_DIR / "plgenn_model6_multitask.keras")
    with (MODEL_DIR / "pattern_encoder.pkl").open("wb") as f: pickle.dump(pattern_encoder, f)
    with (MODEL_DIR / "obfuscation_encoder.pkl").open("wb") as f: pickle.dump(obf_encoder, f)
    with (MODEL_DIR / "ltig_scaler.pkl").open("wb") as f: pickle.dump(scaler, f)
    (MODEL_DIR / "category_labels.json").write_text(json.dumps(CATEGORY_NAMES, indent=2), encoding="utf-8")
    (MODEL_DIR / "pattern_labels.json").write_text(json.dumps(pattern_encoder.classes_.tolist(), indent=2), encoding="utf-8")
    (MODEL_DIR / "obfuscation_labels.json").write_text(json.dumps(obf_encoder.classes_.tolist(), indent=2), encoding="utf-8")
    (MODEL_DIR / "vocab.txt").write_text("\n".join(tokenizer.index_word.get(i, "") for i in range(1, min(VOCAB_SIZE, len(tokenizer.word_index) + 1))) + "\n", encoding="utf-8")
    (MODEL_DIR / "tokenizer_word_index.json").write_text(json.dumps(tokenizer.word_index, ensure_ascii=False), encoding="utf-8")
    try:
        # Export a list-output view in the same category/pattern/obfuscation head order as Model 5.
        export_model = tf.keras.Model(model.inputs, [model.get_layer("category").output,
                                                     model.get_layer("pattern").output,
                                                     model.get_layer("obfuscation").output],
                                      name="PLGenN_Model6_export_ordered")
        converter = tf.lite.TFLiteConverter.from_keras_model(export_model)
        tflite = converter.convert()
        (MODEL_DIR / "plgenn_model6_multitask.tflite").write_bytes(tflite)
        config["tflite_export"] = "success"
    except Exception as exc:
        config["tflite_export"] = f"failed: {type(exc).__name__}: {exc}"
    config["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (EVAL_DIR / "run_config_and_data_audit.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("MODEL6_COMPLETE", json.dumps(summary["test"], sort_keys=True))
    print("Artifacts saved under", RUN_DIR)


if __name__ == "__main__":
    main()

