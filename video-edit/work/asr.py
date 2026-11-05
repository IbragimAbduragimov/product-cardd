import sherpa_onnx, numpy as np, wave, sys
d='models/sherpa-onnx-nemo-transducer-giga-am-russian-2024-10-24/'
rec=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=d+'encoder.int8.onnx',decoder=d+'decoder.onnx',joiner=d+'joiner.onnx',tokens=d+'tokens.txt',model_type='nemo_transducer',num_threads=3)
w=wave.open(sys.argv[1]); sr=w.getframerate(); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
# resample to 16k
import math
idx=np.arange(0,len(x),sr/16000); x16=np.interp(idx,np.arange(len(x)),x).astype(np.float32)
phr=[tuple(map(float,p.split('-'))) for p in sys.argv[2].split()]
for a,b in phr:
    s=rec.create_stream(); s.accept_waveform(16000,x16[int(max(0,a-0.15)*16000):int((b+0.15)*16000)]); rec.decode_stream(s)
    r=s.result
    print(f'{a:7.2f}-{b:7.2f}  {r.text}')
    if r.timestamps and any(c.isdigit() for c in r.text): pass
