# power_drop.py: DC resistance and drop between pads of each power rail, from tracks and vias only (no zones). Run from the project folder.
# Effective DC resistance between pads of a net, from tracks + vias (no zones exist).
import sys, math
sys.path.insert(0,"tools")
import place_tidy as T
from sexpr import parse, children, child
root=parse(open("mindspark_rev1.kicad_pcb").read())
RHO=1.72e-8; TH={"F.Cu":35e-6,"B.Cu":35e-6,"In1.Cu":15.2e-6,"In2.Cu":15.2e-6}
def nn(n):
    x=child(n,"net"); return str(x[1]) if x else ""
pads={}  # (ref,pin)->list of (bbox,layers)
for f in children(root,"footprint"):
    p=T.Part(f)
    for pd,pts in zip(children(f,"pad"),p.pads()):
        ls=[str(a) for a in (child(pd,"layers") or [])[1:]]
        lay={"F.Cu","B.Cu","In1.Cu","In2.Cu"} if "*.Cu" in ls else {p.side}
        pads.setdefault((p.ref,str(pd[1])),[]).append((T.bbox(pts),lay,nn(pd)))
def analyse(net, a, bs, I=None):
    nodes={}; edges=[]
    def node(k):
        if k not in nodes: nodes[k]=len(nodes)
        return nodes[k]
    def key(x,y,l): return (round(x,3),round(y,3),l)
    raw=[]
    for s in children(root,"segment"):
        if nn(s)!=net: continue
        st,en=child(s,"start"),child(s,"end"); l=str(child(s,"layer")[1]); w=float(child(s,"width")[1])
        raw.append(((float(st[1]),float(st[2])),(float(en[1]),float(en[2])),l,w))
    vpts=[]
    for v in children(root,"via"):
        if nn(v)!=net: continue
        at=child(v,"at"); vpts.append((float(at[1]),float(at[2])))
    def isect(a,b,c,d):
        den=(b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0])
        if abs(den)<1e-12: return None
        t=((c[0]-a[0])*(d[1]-c[1])-(c[1]-a[1])*(d[0]-c[0]))/den
        u=((c[0]-a[0])*(b[1]-a[1])-(c[1]-a[1])*(b[0]-a[0]))/den
        if -1e-6<=t<=1+1e-6 and -1e-6<=u<=1+1e-6: return (a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
    X=[]
    for i in range(len(raw)):
        for j in range(i+1,len(raw)):
            if raw[i][2]==raw[j][2]:
                q=isect(raw[i][0],raw[i][1],raw[j][0],raw[j][1])
                if q: X.append((q,raw[i][2]))
    for p1,p2,l,w in raw:
        cand=[q for q,L in X if L==l]+[q for P1,P2,L,_ in raw if L==l for q in (P1,P2)]+vpts
        L2=math.dist(p1,p2); ts=[0.0,1.0]
        if L2>1e-6:
            ux,uy=(p2[0]-p1[0])/L2,(p2[1]-p1[1])/L2
            for q in cand:
                t=((q[0]-p1[0])*ux+(q[1]-p1[1])*uy)
                if 1e-4<t<L2-1e-4 and abs((q[0]-p1[0])*uy-(q[1]-p1[1])*ux)<w/2: ts.append(t/L2)
        ts=sorted(set(ts))
        pts=[(p1[0]+(p2[0]-p1[0])*t,p1[1]+(p2[1]-p1[1])*t) for t in ts]
        for qa,qb in zip(pts,pts[1:]):
            Lm=math.dist(qa,qb)*1e-3; R=RHO*max(Lm,1e-6)/(w*1e-3*TH[l])
            edges.append((node(key(*qa,l)),node(key(*qb,l)),max(R,2e-5)))
        # snap split points that are not exact endpoints of other tracks
        for q in pts[1:-1]:
            for P1,P2,L,_ in raw:
                if L!=l: continue
                for e in (P1,P2):
                    if math.dist(e,q)<w/2: edges.append((node(key(*e,l)),node(key(*q,l)),1e-6))
            for v in vpts:
                if math.dist(v,q)<w/2: edges.append((node(key(*v,l)),node(key(*q,l)),1e-6))
    vias=[]
    for v in children(root,"via"):
        if nn(v)!=net: continue
        at=child(v,"at"); x,y=float(at[1]),float(at[2]); vias.append((x,y))
        ks=[node(key(x,y,l)) for l in TH]
        for k in ks[1:]: edges.append((ks[0],k,0.7e-3))
        # connect track endpoints that land on the via (within radius)
        r=float(child(v,"size")[1])/2
        for k,i in list(nodes.items()):
            if abs(k[0]-x)<=r and abs(k[1]-y)<=r: edges.append((ks[["F.Cu","B.Cu","In1.Cu","In2.Cu"].index(k[2])] if False else node(key(x,y,k[2])),i,1e-6))
    # pads: tie every endpoint inside a pad's bbox to a pad node
    for (ref,pin),lst in pads.items():
        for bb,lay,pn in lst:
            if pn!=net: continue
            pk=("PAD",ref,pin); 
            for k,i in list(nodes.items()):
                if k[0]=="PAD": continue
                if k[2] in lay and bb[0]-0.01<=k[0]<=bb[2]+0.01 and bb[1]-0.01<=k[1]<=bb[3]+0.01:
                    edges.append((node(pk),i,1e-6))
    ks=list(nodes.items())
    for x in range(len(ks)):
        for y in range(x+1,len(ks)):
            A,B=ks[x][0],ks[y][0]
            if A[0]!="PAD" and B[0]!="PAD" and A[2]==B[2] and abs(A[0]-B[0])<0.05 and abs(A[1]-B[1])<0.05: edges.append((ks[x][1],ks[y][1],1e-6))
    par=list(range(len(nodes)))
    def f(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    real=[]
    for i,j,R in edges:
        if R<1e-5: par[f(i)]=f(j)
        else: real.append((i,j,R))
    ia=nodes.get(("PAD",)+a)
    if ia is None: print(" ",net,"source pad has no copper",a); return
    ra=f(ia)
    comp=sorted({f(i) for i in range(len(nodes))}); idx={c:k for k,c in enumerate(comp)}
    n=len(comp); G=[[0.0]*n for _ in range(n)]
    for i,j,R in real:
        p,q=idx[f(i)],idx[f(j)]
        if p==q: continue
        g=1/R; G[p][p]+=g; G[q][q]+=g; G[p][q]-=g; G[q][p]-=g
    s=idx[ra]
    for k in range(n): G[k][k]+=1e-9
    G[s][s]+=1e9   # tie source to reference
    # LU without pivoting (diagonally dominant Laplacian + ground)
    for k in range(n):
        piv=G[k][k]; rowk=G[k]
        for r in range(k+1,n):
            if G[r][k]!=0:
                m=G[r][k]/piv; G[r][k]=m; rr=G[r]
                for c in range(k+1,n):
                    if rowk[c]!=0: rr[c]-=m*rowk[c]
    def solve(bv):
        y=bv[:]
        for r in range(n):
            y[r]-=sum(G[r][c]*y[c] for c in range(r) if G[r][c]!=0)
        x=[0.0]*n
        for r in range(n-1,-1,-1):
            x[r]=(y[r]-sum(G[r][c]*x[c] for c in range(r+1,n) if G[r][c]!=0))/G[r][r]
        return x
    for b in bs:
        ib=nodes.get(("PAD",)+b)
        if ib is None: print(f"  {net} -> {b[0]}.{b[1]}: pad has no copper (unrouted)"); continue
        e=[0.0]*n; e[idx[f(ib)]]=1.0
        R=solve(e)[idx[f(ib)]]
        if R>10: print(f"  {net} {a[0]}.{a[1]} -> {b[0]}.{b[1]}: NOT CONNECTED"); continue
        extra=f"   drop@{I}A={R*I*1000:.0f} mV, loss={R*I*I*1000:.0f} mW" if I else ""
        print(f"  {net} {a[0]}.{a[1]} -> {b[0]}.{b[1]}: {R*1000:.1f} mOhm{extra}")
print("VBUS"); analyse("VBUS_MAIN",("J101","A4"),[("U103","7"),("D101","1"),("C101","1")],3)
analyse("VBUS_MAIN",("J101","A9"),[("U103","7")],3)
analyse("VBUS_ESP",("J102","A4"),[("U103","2"),("D102","1"),("C103","1")],3)
analyse("VBUS_ESP",("J102","A9"),[("U103","2")],3)
print("+5V from U103 OUT pin 1")
analyse("+5V",("U103","1"),[("U103","8"),("C106","1"),("U201","4"),("U202","4"),("U801","1"),("U502","1"),("U602","5")],1)
print("+5V_LED"); analyse("+5V_LED",("U801","6"),[("C815","1")]+[(f"D80{i}","1") for i in range(1,10)]+[(f"D81{i}","1") for i in range(0,3)],1.5)
print("+5V_AMP"); analyse("+5V_AMP",("U502","6"),[("C511","1"),("U503","7"),("U503","8")],1.2)
print("+0V9 from L201.2 (core 0.3 A typ / 1 A max)")
analyse("+0V9",("L201","2"),[("C203","1"),("C204","1"),("U301","61"),("U301","62"),("U301","63"),("U301","64"),("FB301","1")],1)
print("+3V3 from L202.2")
analyse("+3V3",("L202","2"),[("C207","1"),("U203","1"),("C601","1"),("U301","8"),("U301","38"),("U301","52"),("U301","30"),("U401","8")],0.6)
print("+1V8 from U203.5")
analyse("+1V8",("U203","5"),[("C209","1"),("U301","17"),("U301","26"),("U301","31")],0.06)
