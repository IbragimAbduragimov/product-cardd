"""Spectral repair of short creak/click bursts: inside each burst window every STFT bin is clamped
to the level of the same bin just before/after the burst (voice and room tone keep their spectrum,
the broadband crack above it is removed). Phase is kept, windows are cross-faded."""
import numpy as np, wave, sys
def load(p):
    w=wave.open(p); sr=w.getframerate(); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float64)/32768; return x,sr
def save(p,x,sr):
    w=wave.open(p,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
N,H=1024,128
win=np.hanning(N)
def stft(x):
    n=1+(len(x)-N)//H; fr=np.stack([x[i*H:i*H+N]*win for i in range(n)]); return np.fft.rfft(fr,axis=1)
def istft(S,length):
    fr=np.fft.irfft(S,N,axis=1)*win; y=np.zeros(length); wsum=np.zeros(length)
    for i,f in enumerate(fr): y[i*H:i*H+N]+=f; wsum[i*H:i*H+N]+=win**2
    return y/np.maximum(wsum,1e-8)
x,sr=load(sys.argv[1]); out=sys.argv[2]
bursts=[tuple(map(float,b.split(':'))) for b in sys.argv[3:]]
y=x.copy()
for t0,t1 in bursts:
    a=int((t0-0.35)*sr); b=int((t1+0.35)*sr); seg=y[a:b].copy()
    S=stft(seg); mag=np.abs(S); tt=(np.arange(len(S))*H+N/2)/sr+a/sr
    inb=(tt>=t0-0.012)&(tt<=t1+0.012)
    pre=(tt>=t0-0.10)&(tt<t0-0.02); post=(tt>t1+0.02)&(tt<=t1+0.10)
    ref=np.minimum(np.median(mag[pre],0),np.median(mag[post],0))*1.15
    g=np.ones_like(mag)
    g[inb]=np.minimum(1,ref[None,:]/np.maximum(mag[inb],1e-9))
    # smooth gain in time so edges are inaudible
    k=np.hanning(7); k/=k.sum()
    g=np.apply_along_axis(lambda c: np.convolve(c,k,mode='same'),0,g)
    r=istft(S*g,len(seg))
    fade=np.ones(len(seg)); L=int(0.05*sr); fade[:L]=np.linspace(0,1,L); fade[-L:]=np.linspace(1,0,L)
    y[a:b]=y[a:b]*(1-fade)+r*fade
save(out,y,sr)
