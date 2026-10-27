"""Replace the 6 u/uu alternate signs (messy in v1.008) with clean outlines
from Noto Sans Kannada (same x400/y350 contrast mix and 1.03 frame as v1.008),
extending the buried start of the stroke straight along its own tangents."""
import math
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
VF='/home/claude/ref/gf/ofl/notosanskannada/NotoSansKannada[wdth,wght].ttf'
TARGET={'uvowelsignaltknda':-466,'uuvowelsignaltknda':-466,'uvowelsignalt2knda':-372,'uuvowelsignalt2knda':-372,'uvowelsignlaknda':-191,'uuvowelsignlaknda':-191}
def inst(w):
    f=instancer.instantiateVariableFont(TTFont(VF),{'wght':w,'wdth':100}); scale_upem(f,1030); f['head'].unitsPerEm=1000; return f
fx,fy=inst(400),inst(350)
f=TTFont('v1008.ttf'); G=f['glyf']
def unit(v):
    l=math.hypot(*v); return (v[0]/l,v[1]/l)
for n,tx in TARGET.items():
    a,b=fx['glyf'][n],fy['glyf'][n]
    assert not a.isComposite()
    pts=[(x,y2) for (x,_),(_,y2) in zip(a.coordinates,b.coordinates)]; fl=[q&1 for q in a.flags]
    ends=list(a.endPtsOfContours)
    # find the leftmost cap: consecutive on-curve pair with min mean x
    s=0; best=None
    for ci,e in enumerate(ends):
        idx=list(range(s,e+1)); m=len(idx)
        for k in range(m):
            i,j=idx[k],idx[(k+1)%m]
            if fl[i] and fl[j]:
                mx=(pts[i][0]+pts[j][0])/2
                if best is None or mx<best[0]: best=(mx,ci,k,idx)
        s=e+1
    _,ci,k,idx=best; m=len(idx)
    iA,iB=idx[k],idx[(k+1)%m]; iP,iN=idx[(k-1)%m],idx[(k+2)%m]
    A,B=pts[iA],pts[iB]
    tA=unit((A[0]-pts[iP][0],A[1]-pts[iP][1])); tB=unit((B[0]-pts[iN][0],B[1]-pts[iN][1]))
    cur=min(A[0],B[0]); need=cur-tx
    LA=need/max(1e-6,-tA[0]); LB=need/max(1e-6,-tB[0])
    A2=(A[0]+tA[0]*LA,A[1]+tA[1]*LA); B2=(B[0]+tB[0]*LB,B[1]+tB[1]*LB)
    # rebuild point list with A, A2, B2, B inserted
    newpts=[];newfl=[];newends=[]; s=0
    for cj,e in enumerate(ends):
        for q in range(s,e+1):
            newpts.append(pts[q]); newfl.append(fl[q])
            if cj==ci and q==iA: newpts+= [A2,B2]; newfl+=[1,1]
        newends.append(len(newpts)-1); s=e+1
    g=G[n]
    g.coordinates=GlyphCoordinates([(round(x),round(y)) for x,y in newpts]); g.flags=bytearray(newfl)
    g.endPtsOfContours=newends; g.numberOfContours=len(newends); g.program=a.program if hasattr(a,'program') else None
    g.recalcBounds(G)
    adv=f['hmtx'][n][0]; f['hmtx'][n]=(adv,g.xMin)
    print(n,'cap',(round(A[0]),round(A[1])),(round(B[0]),round(B[1])),'-> xMin',g.xMin,'contours',g.numberOfContours, 'yMin/yMax',g.yMin,g.yMax)
f.save('v1008c.ttf')
