from pathlib import Path
import zipfile, copy, re, xml.etree.ElementTree as ET
from PIL import ImageFont

ROOT=Path(__file__).resolve().parents[2]
TARGET=ROOT/'Figures/visio/KAMT-Trans-framwork.vsdx'
BACKUP=TARGET.with_name('KAMT-Trans-framwork.before-energy-20261017.vsdx')
if not BACKUP.exists(): BACKUP.write_bytes(TARGET.read_bytes())
PNG=ROOT/'Figures/KAMT-Trans框架图.png'
PNGBACK=ROOT/'Figures/visio/KAMT-Trans-framework.before-energy-20261017.png'
if not PNGBACK.exists(): PNGBACK.write_bytes(PNG.read_bytes())
NS='http://schemas.microsoft.com/office/visio/2012/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
ET.register_namespace('',NS); ET.register_namespace('r',REL)
def tag(x): return '{'+NS+'}'+x
def el(t,**a): return ET.Element(tag(t),{k:str(v) for k,v in a.items()})
def cell(p,n,v,f=None):
    c=p.find(tag('Cell')+'[@N="'+n+'"]')
    if c is None: c=ET.SubElement(p,tag('Cell'),N=n)
    c.set('V',str(v)); c.attrib.pop('F',None)
    if f is not None: c.set('F',f)
    return c
with zipfile.ZipFile(BACKUP) as z: parts={n:z.read(n) for n in z.namelist()}
old=ET.fromstring(parts['visio/pages/page1.xml'])
source={s.get('ID'):s for s in old.find(tag('Shapes'))}
page=el('PageContents');page.set('{http://www.w3.org/XML/1998/namespace}space','preserve'); shapes=ET.SubElement(page,tag('Shapes'))
W,H=16.5,8.85
serial=3000
INK='#233248'; PUR='#715497'; LIGHT='#F0EBF6'; BLUE='#4B709D'; GREEN='#61834C'; ORANGE='#B77B42'
def new(name):
    global serial
    serial+=1
    s=ET.SubElement(shapes,tag('Shape'),ID=str(serial),NameU=name,Type='Shape',LineStyle='0',FillStyle='0',TextStyle='0')
    return s
def rect(x,y,w,h,text='',fill='#FFFFFF',stroke=INK,size=15,bold=False,name='Block',align=1):
    s=new(name)
    for n,v in {'PinX':x+w/2,'PinY':H-y-h/2,'Width':w,'Height':h,'LocPinX':w/2,'LocPinY':h/2,
        'Angle':0,'LineWeight':0.012,'LineColor':stroke or INK,'LinePattern':1 if stroke else 0,
        'FillForegnd':fill or '#FFFFFF','FillPattern':1 if fill else 0,'FillGradientEnabled':0,'ShdwPattern':0,'Rounding':0.025,
        'VerticalAlign':1,'LeftMargin':0.06,'RightMargin':0.06,'TopMargin':0.025,'BottomMargin':0.025,
        'TxtPinX':w/2,'TxtPinY':h/2,'TxtWidth':w,'TxtHeight':h,'TxtLocPinX':w/2,'TxtLocPinY':h/2}.items(): cell(s,n,v)
    g=ET.SubElement(s,tag('Section'),N='Geometry',IX='0')
    for i,(a,b) in enumerate([(0,0),(w,0),(w,h),(0,h),(0,0)]):
        r=ET.SubElement(g,tag('Row'),T='MoveTo' if i==0 else 'LineTo',IX=str(i+1));cell(r,'X',a);cell(r,'Y',b)
    if text:
        sec=ET.SubElement(s,tag('Section'),N='Character');r=ET.SubElement(sec,tag('Row'),IX='0')
        for n,v in {'Font':'Times New Roman','AsianFont':'Times New Roman','ComplexScriptFont':'Times New Roman','Size':size/72,'Color':INK,'Style':1 if bold else 0,'Case':0,'Pos':0,'FontScale':1,'Letterspace':0,'LangID':'en-US','ComplexScriptSize':-1}.items():cell(r,n,v)
        r.find(tag('Cell')+'[@N="Size"]').set('U','PT')
        sec=ET.SubElement(s,tag('Section'),N='Paragraph');r=ET.SubElement(sec,tag('Row'),IX='0');cell(r,'HorzAlign',align);cell(r,'SpLine',-1.05)
        text=text.replace('_{KG}^{(i)}','ᴷᴳᵢ').replace('_{KL}','ᴷᴸ').replace('_{α∈Δ(Jᵢ)}',' [α ∈ Δ(Jᵢ)]')
        t=ET.SubElement(s,tag('Text'));t.text=text+'\n'
    return s
def label(x,y,w,h,text,size=15,bold=False,color=None):
    s=rect(x,y,w,h,text,None,None,size,bold,'Label')
    if color:
        for r in s.find(tag('Section')+'[@N="Character"]'):cell(r,'Color',color)
    return s
def line(points,color=INK,arrow=True,dashed=False,width=.015):
    s=new('Knowledge-flow' if color==PUR else 'Data-flow')
    xs=[p[0] for p in points];ys=[H-p[1] for p in points];x=min(xs);y=min(ys);w=max(xs)-x;h=max(ys)-y
    for n,v in {'PinX':x,'PinY':y,'Width':max(w,.001),'Height':max(h,.001),'LocPinX':0,'LocPinY':0,'LineColor':color,'LineWeight':width,'LinePattern':2 if dashed else 1,'FillPattern':0,'EndArrow':4 if arrow else 0,'EndArrowSize':1,'BeginArrow':0,'Rounding':0}.items():cell(s,n,v)
    g=ET.SubElement(s,tag('Section'),N='Geometry',IX='0');cell(g,'NoFill',1)
    for i,(px,py) in enumerate(points):
        r=ET.SubElement(g,tag('Row'),T='MoveTo' if i==0 else 'LineTo',IX=str(i+1));cell(r,'X',px-x);cell(r,'Y',H-py-y)
    return s
def reuse(id,x,y,scale=1):
    s=copy.deepcopy(source[str(id)])
    c={a.get('N'):a for a in s.findall(tag('Cell'))};ow=float(c['Width'].get('V'));oh=float(c['Height'].get('V'))
    # Scale local numeric coordinates and remove cached inherited formulas only where necessary.
    if scale!=1:
        for e in s.iter(tag('Cell')):
            if e.get('N') in {'PinX','PinY','Width','Height','LocPinX','LocPinY','X','Y','A','ImgOffsetX','ImgOffsetY','ImgWidth','ImgHeight','TxtPinX','TxtPinY','TxtWidth','TxtHeight','TxtLocPinX','TxtLocPinY'}:
                try:e.set('V',str(float(e.get('V'))*scale))
                except (ValueError,TypeError):pass
    cell(s,'PinX',x+ow*scale/2);cell(s,'PinY',H-y-oh*scale/2)
    shapes.append(s)
def tensor(x,y,colors,w=1.0,h=.23):
    for i,c in enumerate(colors):rect(x+i*w/len(colors),y,w/len(colors),h,fill=c,stroke=INK)
def panel(x,y,w,h,key,title):
    rect(x,y,w,h,fill=None,stroke='#A4AFBE',name='Panel')
    label(x+.12,y+.08,.3,.35,key,21,True)
    label(x+.5,y+.08,w-.65,.4,title,17 if w<5 else 20,True)

# Equation runs are separate native text shapes, avoiding font fallback.
def eq(x,y,w,text,size=16,color=INK,bold=False):
    text=text.replace('J_i','Jᵢ')
    runs=[]
    for part in re.split(r'([_^]\{[^}]*\})',text):
        if not part:continue
        if part.startswith('_{'):runs.append((part[2:-1],-.12,.72))
        elif part.startswith('^{'):runs.append((part[2:-1],.12,.72))
        else:runs.append((part,0,1))
    font='C:/Windows/Fonts/timesbd.ttf' if bold else 'C:/Windows/Fonts/times.ttf'
    widths=[ImageFont.truetype(font,round(size*8*scale)).getlength(txt)/8/72 for txt,shift,scale in runs]
    factor=min(1,(w-.08)/sum(widths));xx=x+(w-sum(widths)*factor)/2
    for (txt,shift,scale),ww in zip(runs,widths):
        t=label(xx,y-shift*factor,ww*factor+.015,.35,txt,size*scale*factor,bold,color)
        for n in ['LeftMargin','RightMargin','TopMargin','BottomMargin']:cell(t,n,0)
        xx+=ww*factor


# Visual redesign: compact scientific objects, two equations and sequential panels.
def circle(cx,cy,r,txt='',fill='#FFFFFF',stroke=INK,size=18):
    ss=rect(cx-r,cy-r,2*r,2*r,txt,fill,stroke,size)
    gg=ss.find(tag('Section')+'[@N="Geometry"]');ss.remove(gg)
    gg=ET.SubElement(ss,tag('Section'),N='Geometry',IX='0');rr=ET.SubElement(gg,tag('Row'),T='Ellipse',IX='1')
    for key,val in {'X':r,'Y':r,'A':2*r,'B':r,'C':r,'D':2*r}.items():cell(rr,key,val)
    return ss

def backdrop(x,w,letter,title,fill,title_size=19):
    ss=rect(x,.15,w,8.52,fill=fill,stroke='#BDC5CD',name='Panel')
    cell(ss,'LinePattern',2)
    label(x+.12,.27,.3,.4,letter,22,True)
    label(x+.47,.22,w-.58,.66,title,title_size,True)

backdrop(.15,3.1,'a','Knowledge embedding','#F6F3FA',18)
backdrop(3.5,6.7,'b','Energy-based knowledge weighting','#FFFBF1',20)
backdrop(10.45,5.9,'c','Knowledge-augmented\nmultimodal fusion','#F1F7F5',18)
PURPAL=['#705391','#9176AD','#AE98C4','#CBBBDC','#E4DAED']
BLUEPAL=['#3D6798','#698DB7','#96AFCD','#BED0E3','#E0E9F3']
GREENPAL=['#527D35','#7FA55D','#AAC88D','#CBDDBA','#E5EFDC']
ORANGEPAL=['#BE7C35','#D29B5A','#E2BB8D','#EFD3B2','#F5E8D9']

# a: embeddings are received from the preceding figure, then activated by patient.
label(.38,1.0,2.62,.35,'DemRKG embeddings',17,True,PUR)
for ii in range(3):
    tensor(.58+ii*.1,1.64-ii*.1,PURPAL,1.12,.2)
eq(.42,1.98,.45,'E',19,PUR)
reuse(2415,2.1,1.52,1.15)
label(1.75,2.03,1.18,.34,'Activation',15)
line([(1.14,1.92),(1.14,2.64)],PUR)
line([(2.34,2.34),(2.34,2.64)],PUR)
rect(.58,2.64,2.2,.57,'Patient lookup',LIGHT,PUR,17)
line([(1.68,3.21),(1.68,3.59)],PUR)
tensor(.57,3.61,PURPAL[:3]+['#E4E4E4']+[PURPAL[4]],2.22,.28)
eq(.52,3.99,2.3,'X_{KG}^{(i)}',18,PUR)
label(.38,4.43,2.62,.31,'Support Jᵢ / mask Mᵢ',14,color=PUR)

label(.36,4.98,2.68,.32,'Clinical feature embeddings',16,True)
for yy,ic,enc,title,clr,pal in [
    (5.54,167,168,'EHR',BLUE,BLUEPAL),
    (6.59,170,169,'BM',GREEN,GREENPAL),
    (7.64,171,1407,'MRI',ORANGE,ORANGEPAL)]:
    reuse(ic,.42,yy+.03,.58)
    label(.37,yy+.4,.75,.28,title,14,True)
    line([(1.1,yy+.22),(1.32,yy+.22)],clr)
    reuse(enc,1.4,yy,.55)
    label(1.12,yy+.4,.85,.28,'MLP' if title!='MRI' else '3D-CNN',12)
    line([(1.84,yy+.22),(2.0,yy+.22)],clr)
    tensor(2.03,yy+.1,pal,.75,.22)
    line([(2.78,yy+.22),(3.35,yy+.22)],clr,False)
# h is shared with the query and the residual inputs identified in panel c.
line([(3.35,7.86),(3.35,3.91)],INK,False)
line([(3.35,3.62),(3.35,1.78),(4.4,1.78)],INK)
eq(3.69,1.23,.55,'h_{m}',17,BLUE)

# b: a single branch illustrates Q/K/V for every modality.
label(3.83,1.0,5.97,.28,'For each modality m ∈ {EHR, BM, MRI}',15)
rect(4.4,1.43,1.0,.7,'Q','#E4EDF7',BLUE,22,True)
line([(5.4,1.78),(6.6,1.78),(6.6,2.16)],BLUE)
line([(2.79,3.75),(4.0,3.75)],PUR)
rect(4.0,3.4,1.1,.7,'Adapter',LIGHT,PUR,16)
line([(5.1,3.75),(5.45,3.75)],PUR)
rect(5.45,3.4,.65,.7,'K',LIGHT,PUR,22,True)
line([(6.1,3.75),(6.6,3.75),(6.6,2.56)],PUR)
line([(5.25,3.75),(5.25,5.6),(5.45,5.6)],PUR)
rect(5.45,5.25,.65,.7,'V',LIGHT,PUR,22,True)
circle(6.6,2.36,.2,'×','#FFFFFF',INK,21)
line([(6.8,2.36),(7.15,2.36)],INK)
label(5.67,2.65,.8,.5,'Scale &\nnegate',12)
label(7.12,1.63,2.28,.35,'Energy ε',18,True)
energycols=['#D0B7D9','#A276B6','#E3E3E3','#C29ACF','#E8DCEC']
tensor(7.15,2.2,energycols,2.15,.33)
line([(8.22,2.53),(8.22,3.42)],INK)
rect(7.15,3.42,2.15,.6,'Masked softmax','#FFF0CA','#C99D3D',17)
# The dashed path carries the patient support, separately from embedding content.
line([(3.0,4.55),(3.42,4.55),(3.42,4.7),(6.8,4.7),(6.8,3.72),(7.15,3.72)],PUR,True,True,.012)
eq(5.33,4.77,1.25,'M_{i}',16,PUR)
line([(8.22,4.02),(8.22,4.37)],INK)
heights=[.23,.61,0,.39,.13]
for ii,hh in enumerate(heights):
    xx=7.23+ii*.42
    if hh:rect(xx,5.12-hh,.29,hh,fill=['#C7B5D6','#705391','#E3E3E3','#9C7CB8','#DDCFE8'][ii],stroke=PUR)
    else:label(xx-.02,5.03,.33,.2,'0',11,color='#929292')
line([(7.12,5.12),(9.35,5.12)],INK,False,False,.008)
label(7.08,5.29,2.35,.32,'Optimal weights α*',17,True)
line([(8.22,5.65),(8.22,6.12)],PUR)
line([(6.1,5.6),(6.45,5.6),(6.45,6.44),(7.15,6.44)],PUR)
rect(7.15,6.12,2.25,.65,'Value readout',LIGHT,PUR,18)
# Two compact governing expressions replace the equation-heavy callout.
label(3.9,7.17,5.85,.32,'Conditional free-energy minimum',16,True)
eq(3.88,7.56,5.94,'F(α) = Σ_{j∈J_i} α_{j} ε_{j} + D_{KL}(α ∥ u_{i})',18)
eq(3.88,8.06,5.94,'α^{*} = softmax(−ε + M_{i})',18)
# The modality-specific response goes to the residual injection for each branch.
line([(9.4,6.44),(10.28,6.44),(10.28,1.23),(15.98,1.23)],PUR,False,False,.014)
eq(9.45,5.78,.72,'z_{m}^{kg}',16,PUR)

# c: the same residual knowledge update is applied to all three encoded modalities.
for xx,title,clr,pal in [(10.84,'EHR',BLUE,BLUEPAL),(12.73,'BM',GREEN,GREENPAL),(14.62,'MRI',ORANGE,ORANGEPAL)]:
    label(xx,1.52,1.12,.3,title,17,True,clr)
    tensor(xx,1.98,pal,1.12,.23)
    line([(xx+.56,2.21),(xx+.56,2.76)],clr)
    rect(xx,2.76,1.12,.66,'Add &\nNorm', '#FFFFFF',clr,15)
    line([(xx+1.3,1.23),(xx+1.3,3.09),(xx+1.12,3.09)],PUR)
    line([(xx+.56,3.42),(xx+.56,3.75)],clr)
    tensor(xx,3.75,pal,1.12,.23)

# EHR-BM interaction yields the joint clinical state.
line([(11.4,3.98),(11.4,4.61)],BLUE)
line([(13.29,3.98),(13.29,4.61)],GREEN)
rect(10.94,4.61,3.58,.65,'EHR ↔ BM attention','#E5EDF0','#5E8590',18)
line([(12.73,5.26),(12.73,5.6)],BLUE)
tensor(12.19,5.6,['#4B709D','#7B9DB7','#8BAE8A','#B3CCA5'],1.05,.23)
eq(10.98,5.52,1.1,'H_{ab}',18,BLUE)
# MRI supplies Q; H_ab supplies K and V, and also bypasses alignment to final fusion.
line([(15.18,3.98),(15.18,6.12)],ORANGE)
label(15.38,5.36,.55,.3,'Q',16,color=ORANGE)
line([(12.73,5.83),(12.73,6.46),(13.23,6.46)],BLUE)
label(12.29,5.97,.82,.3,'K, V',15,color=BLUE)
rect(13.23,6.12,2.5,.68,'MRI alignment','#E5EDF0','#5E8590',18)
line([(14.48,6.8),(14.48,7.28)],INK)
eq(14.74,6.88,1.0,'Z_{mri}',16)
line([(12.19,5.72),(11.75,5.72),(11.75,7.53),(12.3,7.53)],BLUE)
rect(12.3,7.28,2.43,.5,'Concat','#FFFFFF',INK,17)
line([(13.51,7.78),(13.51,7.98)],INK)
rect(12.98,7.98,1.06,.52,'MLP','#DEECEE','#548991',17)
line([(14.04,8.24),(14.43,8.24)],INK)
rect(14.43,7.98,1.59,.52,'Prediction','#FFFFFF',INK,16,True)

# Native text and styles consistently use Times New Roman.
for s in page.iter(tag('Shape')):
    for c in s.iter(tag('Cell')):
        if c.get('N') in {'Font','AsianFont','ComplexScriptFont'}:c.set('V','Times New Roman');c.attrib.pop('F',None)
parts['visio/pages/page1.xml']=ET.tostring(page,encoding='utf-8',xml_declaration=True)
pages=ET.fromstring(parts['visio/pages/pages.xml']);p=pages.find(tag('Page'));ps=p.find(tag('PageSheet'))
cell(ps,'PageWidth',W);cell(ps,'PageHeight',H);p.set('ViewScale','0.6');p.set('ViewCenterX',str(W/2));p.set('ViewCenterY',str(H/2))
parts['visio/pages/pages.xml']=ET.tostring(pages,encoding='utf-8',xml_declaration=True)
doc=ET.fromstring(parts['visio/document.xml'])
for c in doc.iter(tag('Cell')):
    if c.get('N') in {'Font','AsianFont','ComplexScriptFont'}:c.set('V','Times New Roman');c.attrib.pop('F',None)
parts['visio/document.xml']=ET.tostring(doc,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in parts.items():z.writestr(name,data)
ids=[s.get('ID') for s in page.iter(tag('Shape'))]
assert len(ids)==len(set(ids))
print(f'Updated {TARGET}; {len(ids)} editable shapes; backup {BACKUP}')
