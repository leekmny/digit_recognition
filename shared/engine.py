"""Shared MNIST preprocessing and NumPy inference."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]

def normalize(image):
    """Convert a white-background drawing into a centered MNIST image."""
    gray = ImageOps.invert(image.convert('L'))
    a = np.asarray(gray)
    ys, xs = np.where(a > 35)
    if len(xs) < 8:
        raise ValueError('Draw one digit before recognizing.')
    crop = gray.crop((int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1))
    scale = 20 / max(crop.size)
    crop = crop.resize((max(1, round(crop.width*scale)), max(1, round(crop.height*scale))), Image.Resampling.LANCZOS)
    out = Image.new('L', (28,28))
    out.paste(crop, ((28-crop.width)//2, (28-crop.height)//2))
    a = np.asarray(out, dtype=np.float32)
    yy, xx = np.indices(a.shape)
    dx, dy = round(13.5-(xx*a).sum()/a.sum()), round(13.5-(yy*a).sum()/a.sum())
    centered = Image.new('L',(28,28))
    centered.paste(out,(dx,dy))
    return np.asarray(centered,dtype=np.float32)/255

class Recognizer:
    def __init__(self):
        path = ROOT/'model.npz'
        if not path.exists():
            raise RuntimeError('Model missing. Run train_model.py first.')
        with np.load(path, allow_pickle=False) as data:
            self.w = [data[f'w{i}'] for i in range(3)]
            self.b = [data[f'b{i}'] for i in range(3)]

    def probabilities(self, values):
        x = np.asarray(values,dtype=np.float32).reshape(-1,784)
        for i in range(3):
            x = x @ self.w[i] + self.b[i]
            if i < 2:
                x = np.maximum(x,0)
        x = np.exp(x-x.max(axis=1,keepdims=True))
        return x/x.sum(axis=1,keepdims=True)

    def predict(self, image):
        pixels = normalize(image)
        p = self.probabilities(pixels)[0]
        return {'digit':int(p.argmax()),'confidence':float(p.max()),'probabilities':p.tolist(),'pixels':(pixels*255).astype(int).tolist()}
