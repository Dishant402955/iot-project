#!/usr/bin/env python3
"""Train on one released laptop recording and test on the other."""
import argparse, json
from pathlib import Path
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, classification_report
from baseline import extract_features, make_model, CLASSES

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=Path('data/rfds-reference')); p.add_argument('--output',type=Path,default=Path('research/rfds-reproduction/outputs/cross_device_metrics.json')); a=p.parse_args()
    sessions=['walking_HP','walking_LENOVO']; results={}
    for train_name,test_name in [sessions,sessions[::-1]]:
        Xtr,ytr,_,_=extract_features(a.root/train_name/'csi.csv')
        Xte,yte,_,_=extract_features(a.root/test_name/'csi.csv')
        model=make_model().fit(Xtr,ytr); pred=model.predict(Xte)
        results[f'{train_name}_to_{test_name}']={
            'train_samples':int(len(ytr)),'test_samples':int(len(yte)),
            'accuracy':float(accuracy_score(yte,pred)),
            'balanced_accuracy':float(balanced_accuracy_score(yte,pred)),
            'classes':CLASSES,
            'confusion_matrix':confusion_matrix(yte,pred,labels=CLASSES).tolist(),
            'classification_report':classification_report(yte,pred,labels=CLASSES,output_dict=True,zero_division=0),
            'limitation':'Only one labelled session per device exists. This is a strict cross-recording transfer test, not a robust population estimate.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(results,indent=2)+'\n'); print(json.dumps(results,indent=2))
if __name__=='__main__': main()
