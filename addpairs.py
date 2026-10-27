"""Add one GPOS pair lookup (dist feature) that nudges an ottu right where a
letter's descending tail would otherwise touch it. Marks other than ottus are
skipped (mark filtering set), so it also works with a vowel sign in between."""
import sys, pickle
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
f=TTFont(sys.argv[1]); fix=pickle.load(open('pairfix.pkl','rb'))
order=set(f.getGlyphOrder())
fam={'uni0C9B':'ch','uni0CA2':'ddh','uni0CAB':'ph','uni0CAD':'bh'}
pairs={}
for (g1,g2),dx in fix.items():
    if dx is None or g1=='givowelknda': continue
    if g1 in fam:
        p=fam[g1]
        firsts=[g1]+[n for n in (p+'anocrestknda',p+'ivowelknda',p+'evowelknda') if n in order]
        seconds=[g2]+[n for n in (g2.replace('subscriptknda','subscriptrightknda'),) if n in order and n!=g2]
        for a in firsts:
            for b in seconds: pairs[(a,b)]=('place',dx)
    elif g1.endswith('_only'):
        pairs[(g1[:-5],g2)]=('place',dx)
    elif 'subscript' in g1:
        pairs[(g1,g2)]=('adv',dx)
    else:
        pairs[(g1,g2)]=('place',dx)
gdef=f['GDEF'].table
subs=sorted([n for n in f.getGlyphOrder() if 'subscript' in n], key=f.getGlyphID)
cov=ot.Coverage(); cov.glyphs=subs
gdef.MarkGlyphSetsDef.Coverage.append(cov); gdef.MarkGlyphSetsDef.MarkSetCount=len(gdef.MarkGlyphSetsDef.Coverage)
setidx=len(gdef.MarkGlyphSetsDef.Coverage)-1
from collections import defaultdict
by1=defaultdict(list)
for (a,b),v in pairs.items(): by1[a].append((b,v))
st=ot.PairPos(); st.Format=1
firsts=sorted(by1,key=f.getGlyphID)
st.Coverage=ot.Coverage(); st.Coverage.glyphs=firsts
st.ValueFormat1=0x0004  # XAdvance
st.ValueFormat2=0x0001  # XPlacement
st.PairSet=[]
for a in firsts:
    ps=ot.PairSet(); ps.PairValueRecord=[]
    for b,(kind,dx) in sorted(by1[a],key=lambda t:f.getGlyphID(t[0])):
        r=ot.PairValueRecord(); r.SecondGlyph=b
        v1=ot.ValueRecord(); v1.XAdvance=dx if kind=='adv' else 0
        v2=ot.ValueRecord(); v2.XPlacement=dx if kind=='place' else 0
        r.Value1=v1; r.Value2=v2; ps.PairValueRecord.append(r)
    ps.PairValueCount=len(ps.PairValueRecord); st.PairSet.append(ps)
st.PairSetCount=len(st.PairSet)
lk=ot.Lookup(); lk.LookupType=2; lk.LookupFlag=0x10; lk.MarkFilteringSet=setidx
lk.SubTable=[st]; lk.SubTableCount=1
gpos=f['GPOS'].table; gpos.LookupList.Lookup.append(lk); gpos.LookupList.LookupCount=len(gpos.LookupList.Lookup)
li=len(gpos.LookupList.Lookup)-1
for i,fr in enumerate(gpos.FeatureList.FeatureRecord):
    if fr.FeatureTag=='dist' and i in (4,5,6):
        fr.Feature.LookupListIndex.append(li); fr.Feature.LookupCount=len(fr.Feature.LookupListIndex)
f.save(sys.argv[2]); print(len(pairs),'pairs; lookup',li)
