"""Train an MNIST MLP and export portable NumPy weights."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import argparse, json, urllib.request
import numpy as np
from sklearn.neural_network import MLPClassifier
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=ROOT/'data'/'mnist.npz')
    args=parser.parse_args()
    if not args.data.exists():
        args.data.parent.mkdir(parents=True,exist_ok=True)
        print('Downloading MNIST...',flush=True)
        temporary=args.data.with_suffix('.part')
        urllib.request.urlretrieve('https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz',temporary)
        temporary.replace(args.data)
    with np.load(args.data,allow_pickle=False) as data:
        x=data['x_train'].reshape(-1,784).astype(np.float32)/255
        y=data['y_train']
        xt=data['x_test'].reshape(-1,784).astype(np.float32)/255
        yt=data['y_test']
    model=MLPClassifier(hidden_layer_sizes=(128,64),batch_size=256,max_iter=25,early_stopping=True,n_iter_no_change=4,random_state=42,verbose=True)
    with threadpool_limits(limits=2):
        model.fit(x,y)
        accuracy=float(model.score(xt,yt))
    weights={f'w{i}':w.astype(np.float32) for i,w in enumerate(model.coefs_)}
    weights.update({f'b{i}':b.astype(np.float32) for i,b in enumerate(model.intercepts_)})
    np.savez_compressed(ROOT/'model.npz',**weights)
    metrics={'dataset':'MNIST','training_samples':len(y),'test_samples':len(yt),'test_accuracy':accuracy,'iterations':model.n_iter_,'seed':42}
    (ROOT/'model_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__':
    main()
