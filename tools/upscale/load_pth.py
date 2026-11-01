import zipfile, pickle, numpy as np
class _Stor:
    def __init__(s, key, dtype): s.key, s.dtype = key, dtype
def load(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    root = names[0].split('/')[0]
    pk = [n for n in names if n.endswith('data.pkl')][0]
    dmap = {'FloatStorage': np.float32, 'HalfStorage': np.float16, 'LongStorage': np.int64}
    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if name == '_rebuild_tensor_v2':
                def rb(st, off, size, stride, *a):
                    raw = np.frombuffer(z.read('%s/data/%s' % (root, st.key)), dtype=st.dtype)
                    n = int(np.prod(size)) if size else 1
                    return np.lib.stride_tricks.as_strided(raw[off:], shape=size, strides=[s * raw.itemsize for s in stride]).copy() if size else raw[off:off+1].copy()
                return rb
            if name in dmap: return dmap[name]
            if name == 'OrderedDict':
                import collections; return collections.OrderedDict
            return super().find_class(mod, name)
        def persistent_load(self, pid):
            _, typ, key, loc, n = pid
            return _Stor(key, typ if isinstance(typ, type) else np.float32)
    return U(z.open(pk)).load()
