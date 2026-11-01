"""Real-ESRGAN (RRDBNet, x4 anime 6B) forward pass in numpy, tiled. usage: esrgan_np.py in.png out.png [alpha_mask.png]"""
import sys, time, numpy as np
from PIL import Image
from load_pth import load
import os
P = load(os.environ.get('W', 'RealESRGAN_x4plus_anime_6B.pth'))
P = P.get('params_ema', P.get('params', P))
NB = 1 + max(int(k.split('.')[1]) for k in P if k.startswith('body.'))
Wm = {}
for k in P:
    if k.endswith('.weight'):
        w = P[k]; Wm[k[:-7]] = (np.ascontiguousarray(w.transpose(2, 3, 1, 0).reshape(-1, w.shape[0])), P[k[:-7] + '.bias'])

def conv(x, name):
    w, b = Wm[name]
    H, W_, C = x.shape
    xp = np.pad(x, ((1, 1), (1, 1), (0, 0)), mode='constant')
    cols = np.concatenate([xp[dy:dy + H, dx:dx + W_] for dy in range(3) for dx in range(3)], axis=2)
    return (cols.reshape(-1, 9 * C) @ w + b).reshape(H, W_, -1)

def lr(x): return np.where(x > 0, x, 0.2 * x)

def rdb(x, p):
    x1 = lr(conv(x, p + 'conv1'))
    x2 = lr(conv(np.concatenate([x, x1], 2), p + 'conv2'))
    x3 = lr(conv(np.concatenate([x, x1, x2], 2), p + 'conv3'))
    x4 = lr(conv(np.concatenate([x, x1, x2, x3], 2), p + 'conv4'))
    x5 = conv(np.concatenate([x, x1, x2, x3, x4], 2), p + 'conv5')
    return x5 * 0.2 + x

def net(x):
    f = conv(x, 'conv_first'); b = f
    for i in range(NB):
        o = b
        for j in (1, 2, 3):
            o = rdb(o, 'body.%d.rdb%d.' % (i, j))
        b = o * 0.2 + b
    f = f + conv(b, 'conv_body')
    f = lr(conv(f.repeat(2, 0).repeat(2, 1), 'conv_up1'))
    f = lr(conv(f.repeat(2, 0).repeat(2, 1), 'conv_up2'))
    return conv(lr(conv(f, 'conv_hr')), 'conv_last')

if __name__ == '__main__':
    img = np.asarray(Image.open(sys.argv[1]).convert('RGB'), np.float32) / 255.
    mask = np.asarray(Image.open(sys.argv[3]).convert('L')) > 0 if len(sys.argv) > 3 else np.ones(img.shape[:2], bool)
    H, W_ = img.shape[:2]; T, PAD = 112, 10
    out = np.zeros((H * 4, W_ * 4, 3), np.float32)
    tiles = [(y, x) for y in range(0, H, T) for x in range(0, W_, T) if mask[max(0, y - 4):y + T + 4, max(0, x - 4):x + T + 4].any()]
    t0 = time.time()
    for i, (y, x) in enumerate(tiles):
        y0, x0, y1, x1 = max(0, y - PAD), max(0, x - PAD), min(H, y + T + PAD), min(W_, x + T + PAD)
        o = net(img[y0:y1, x0:x1])
        ty1, tx1 = min(H, y + T), min(W_, x + T)
        out[y * 4:ty1 * 4, x * 4:tx1 * 4] = o[(y - y0) * 4:(ty1 - y0) * 4, (x - x0) * 4:(tx1 - x0) * 4]
        if i % 10 == 0: print('tile %d/%d  %.0fs' % (i, len(tiles), time.time() - t0), flush=True)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(sys.argv[2])
    print('done', time.time() - t0)
