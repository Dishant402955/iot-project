#!/usr/bin/env python3
"""Compare small classifiers using development sessions only; never reads Session 3."""
from __future__ import annotations
import argparse, hashlib, json, warnings
from pathlib import Path
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC, SVC
import analyze_presence_development as dev

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSIONS = tuple(ROOT / name for name in dev.ALLOWED_SESSION_FILES)


def load_rows(paths):
    dev.validate_development_sessions(tuple(paths))
    rows=[]
    for path in paths:
        rows.extend(dev.load_session(path, dev.session_id_for_path(path)))
    return rows


MODEL_CONFIGURATIONS = {
    'nearest_centroid': 'Training-fold standardization; squared-Euclidean nearest class centroid.',
    'logistic_regression': {'C': 0.1, 'class_weight': 'balanced', 'max_iter': 3000, 'random_state': 42, 'scaler': 'StandardScaler in fold pipeline'},
    'linear_svm': {'C': 0.1, 'class_weight': 'balanced', 'max_iter': 10000, 'random_state': 42, 'scaler': 'StandardScaler in fold pipeline'},
    'rbf_svm': {'C': 0.5, 'kernel': 'rbf', 'gamma': 'scale', 'class_weight': 'balanced', 'scaler': 'StandardScaler in fold pipeline'},
    'random_forest': {'n_estimators': 250, 'max_depth': 2, 'min_samples_leaf': 2, 'max_features': 'sqrt', 'class_weight': 'balanced', 'random_state': 42},
    'extra_trees': {'n_estimators': 250, 'max_depth': 2, 'min_samples_leaf': 2, 'max_features': 'sqrt', 'class_weight': 'balanced', 'random_state': 42},
    'gradient_boosting': {'n_estimators': 30, 'learning_rate': 0.03, 'max_depth': 1, 'min_samples_leaf': 3, 'random_state': 42},
    'small_mlp': {'hidden_layer_sizes': [8], 'alpha': 1.0, 'learning_rate_init': 0.003, 'max_iter': 5000, 'tol': 0.0001, 'early_stopping': False, 'random_state': 42, 'scaler': 'StandardScaler in fold pipeline'},
}

def make_models():
    # Fixed, conservative configurations: no hyperparameter search against outer folds.
    return {
        'nearest_centroid': None,
        'logistic_regression': make_pipeline(StandardScaler(), LogisticRegression(C=0.1, class_weight='balanced', max_iter=3000, random_state=42)),
        'linear_svm': make_pipeline(StandardScaler(), LinearSVC(C=0.1, class_weight='balanced', random_state=42, max_iter=10000)),
        'rbf_svm': make_pipeline(StandardScaler(), SVC(C=0.5, kernel='rbf', gamma='scale', class_weight='balanced')),
        'random_forest': RandomForestClassifier(n_estimators=250, max_depth=2, min_samples_leaf=2, max_features='sqrt', class_weight='balanced', random_state=42, n_jobs=1),
        'extra_trees': ExtraTreesClassifier(n_estimators=250, max_depth=2, min_samples_leaf=2, max_features='sqrt', class_weight='balanced', random_state=42, n_jobs=1),
        'gradient_boosting': GradientBoostingClassifier(n_estimators=30, learning_rate=0.03, max_depth=1, min_samples_leaf=3, random_state=42),
        'small_mlp': make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(8,), alpha=1.0, learning_rate_init=0.003, max_iter=5000, early_stopping=False, random_state=42, tol=1e-4)),
    }


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0,1]).ravel().tolist()
    return {'n_batches':len(y),'tp':int(tp),'tn':int(tn),'fp':int(fp),'fn':int(fn),
            'accuracy':float(accuracy_score(y,pred)), 'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
            'sensitivity':float(recall_score(y,pred,zero_division=0)),
            'specificity':float(tn/(tn+fp)) if tn+fp else 0.0,
            'precision':float(precision_score(y,pred,zero_division=0)), 'f1':float(f1_score(y,pred,zero_division=0))}


def folds_for(rows, mode):
    if mode == 'paired_round':
        keys=sorted({(r['session'],r['round']) for r in rows})
        return [(f'session_{s}_round_{rd}', [r for r in rows if (r['session'],r['round'])== (s,rd)], [r for r in rows if (r['session'],r['round']) != (s,rd)]) for s,rd in keys]
    sessions=sorted({r['session'] for r in rows})
    return [(f'test_session_{s}', [r for r in rows if r['session']==s], [r for r in rows if r['session']!=s]) for s in sessions]


def evaluate(rows, mode):
    results={}
    for name, estimator in make_models().items():
        truth=[]; predicted=[]; fold_metrics=[]
        convergence_warning_total = 0
        for fold_name, test, train in folds_for(rows, mode):
            x_train=np.vstack([r['median_profile'] for r in train]); y_train=np.asarray([r['label'] for r in train],dtype=int)
            x_test=np.vstack([r['median_profile'] for r in test]); y_test=np.asarray([r['label'] for r in test],dtype=int)
            if name == 'nearest_centroid':
                _, pred=dev.nearest_centroid_scores(train,test)
            else:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always', ConvergenceWarning)
                    estimator.fit(x_train,y_train)
                    pred=estimator.predict(x_test).astype(int)
                warning_count=sum(issubclass(w.category, ConvergenceWarning) for w in caught)
                convergence_warning_total += warning_count
            if name == 'nearest_centroid':
                warning_count=0
            truth.extend(y_test.tolist()); predicted.extend(pred.tolist())
            fold_metrics.append({'fold':fold_name,'convergence_warning_count':int(warning_count),**metrics(y_test,pred)})
        results[name]={'pooled':metrics(np.asarray(truth),np.asarray(predicted)),'folds':fold_metrics,'convergence_warning_count':convergence_warning_total}
    return results


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--session',type=Path,action='append',help='Allowlisted development JSONL; repeat for each session')
    ap.add_argument('--output',type=Path,default=ROOT/'docs'/'PRESENCE_MODEL_COMPARISON_20261122.json')
    args=ap.parse_args(); paths=tuple(p.resolve() for p in (args.session or DEFAULT_SESSIONS))
    # Validate allowlisted filenames before touching file contents.
    dev.validate_development_sessions(paths)
    rows=load_rows(paths)
    report={'scope':'Development-only model comparison; consumed held-out Session 3 was not accessed.',
      'sessions':[{'session_id':dev.session_id_for_path(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
      'data':{'attempts':sum(r['attempts'] for r in rows),'valid_profiles':sum(r['valid_profiles'] for r in rows),'batch_examples':len(rows),'paired_round_groups':len({(r['session'],r['round']) for r in rows}),'features_per_batch':52},
      'method':'One example per acquisition batch: per-tone median across valid CSI profiles. Paired ABSENT/PRESENT batches from the same physical session-round are held out together. All preprocessing is inside each training-fold pipeline. Fixed conservative configurations; no outer-fold hyperparameter tuning.',
      'model_configurations':MODEL_CONFIGURATIONS,
      'grouped_leave_one_session_round_out':evaluate(rows,'paired_round'),
      'leave_one_development_session_out':evaluate(rows,'session'),
      'versions':{'numpy':np.__version__},'held_out_session_3_accessed':False}
    import sklearn
    report['versions']['scikit_learn']=sklearn.__version__
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'data':report['data'],'grouped':{k:v['pooled'] for k,v in report['grouped_leave_one_session_round_out'].items()},'session_transfer':{k:v['pooled'] for k,v in report['leave_one_development_session_out'].items()},'output':str(args.output),'held_out_session_3_accessed':False},indent=2))

if __name__=='__main__': main()
