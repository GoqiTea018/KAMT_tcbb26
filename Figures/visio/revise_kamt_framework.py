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
W,H=17,9.8
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

panel(.15,.15,4.05,9.5,'a','Knowledge and modality inputs')
panel(4.55,.15,7.95,9.5,'b','Knowledge weighting and injection')
panel(12.85,.15,4.0,9.5,'c','Multimodal fusion')

# Knowledge is the shared semantic source. Its construction is shown elsewhere.
rect(.38,.88,3.6,4.35,fill='#F6F2FA',stroke=None)
label(.48,1.0,3.42,.4,'DemRKG knowledge embeddings',16,True,PUR)
graphnodes=[(.72,2.04),(.98,1.7),(1.45,1.68),(1.78,1.98),(1.48,2.4),(.96,2.36),(1.28,2.04)]
for aa,bb in [(0,1),(0,5),(0,6),(1,2),(1,6),(2,3),(2,6),(3,4),(3,6),(4,5),(4,6),(5,6),(1,5)]:
    line([graphnodes[aa],graphnodes[bb]],PUR,False,False,.011)
for nn,(xx,yy) in enumerate(graphnodes):
    ss=rect(xx-.085,yy-.085,.17,.17,fill=['#8E77AB','#C1B2D3','#B0C7DF','#DED4E8','#7C9E7A','#D8C2A2','#A08DBA'][nn],stroke=PUR)
    gg=ss.find(tag('Section')+'[@N="Geometry"]');ss.remove(gg)
    gg=ET.SubElement(ss,tag('Section'),N='Geometry',IX='0');rr=ET.SubElement(gg,tag('Row'),T='Ellipse',IX='1')
    for key,val in {'X':.085,'Y':.085,'A':.17,'B':.085,'C':.085,'D':.17}.items():cell(rr,key,val)

line([(1.86,2.03),(2.25,2.03)],PUR)
for rr in range(3):tensor(2.3,1.68+rr*.22,['#80689C','#9B87B3','#B7A7CA','#D3C8DF','#E6DFEF'],1.25,.22)
label(2.13,2.42,1.62,.55,'Relation-trained\nentity matrix E',14)
rect(.65,3.13,2.95,.7,'Clinical observations\nActivation + entity mapping',LIGHT,PUR,15)
line([(2.12,3.83),(2.12,4.15)],PUR)
label(.65,4.1,2.95,.32,'Patient-specific embedding lookup',14,True,PUR)
line([(3.55,2.01),(3.8,2.01),(3.8,4.54),(3.42,4.54)],PUR)
tensor(.85,4.52,['#80689C','#9B87B3','#B7A7CA','#D3C8DF','#E6DFEF'],2.5,.24)
eq(.65,4.83,2.95,'X_{KG}^{(i)}     J_{i}, M_{i}',16,PUR)
line([(3.98,4.54),(5.02,4.54)],PUR)

label(.55,5.54,3.2,.35,'Modality-specific encoding',17,True)
for n,(yy,ic,enc,clr,pal,title) in enumerate([
    (6.1,167,168,BLUE,['#4B709D','#7294B9','#9CB5CF','#C3D2E2','#E7EDF4'],'EHR'),
    (7.18,170,169,GREEN,['#557C2F','#7DA15E','#A5C58C','#C8DCB8','#E8F0E0'],'BM'),
    (8.26,171,1407,ORANGE,['#C98D48','#D9A468','#E4BC91','#EED3B8','#F5E5D6'],'MRI')]):
    rect(.4,yy-.02,3.55,.91,fill=['#EEF3F8','#F1F5EC','#F8F2EB'][n],stroke=None)
    reuse(ic,.52,yy+.09,.74)
    label(.5,yy+.53,.83,.26,title,14,True)
    line([(1.35,yy+.34),(1.64,yy+.34)],clr)
    reuse(enc,1.71,yy+.08,.70)
    label(1.45,yy+.53,.92,.26,'MLP' if n<2 else '3D-CNN',13)
    line([(2.25,yy+.34),(2.55,yy+.34)],clr)
    tensor(2.62,yy+.23,pal,1.05,.22)
    eq(2.45,yy+.5,1.4,'h_{i,'+title+'}',14,clr)
    line([(3.68,yy+.34),(4.36,yy+.34)],clr,False)
# Shared modality input bus; the gap marks a crossing with the KG path.
line([(4.36,8.6),(4.36,4.65)],INK,False)
line([(4.36,4.42),(4.36,1.72),(5.02,1.72)],INK)

# Q, K and V are explicit and keep their different scientific roles.
label(4.95,.87,7.15,.32,'Applied independently to EHR, BM and MRI, for each attention head',15)
rect(5.02,1.38,1.4,.8,fill='#EDF2F7',stroke=BLUE)
label(5.05,1.42,1.34,.3,'Modality',14)
eq(5.02,1.76,1.4,'h_{im}',16,BLUE)
line([(6.42,1.72),(6.72,1.72)],BLUE)
rect(6.72,1.38,1.22,.8,fill='#EDF2F7',stroke=BLUE)
label(6.75,1.42,1.16,.3,'Query',14)
eq(6.72,1.76,1.22,'W_{m}^{Q}, b_{m}^{Q}',13,BLUE)
line([(7.94,1.72),(8.3,1.72)],BLUE)
eq(7.84,2.12,.48,'q_{im}',15,BLUE)
rect(8.3,1.35,3.77,.94,fill=LIGHT,stroke=PUR)
label(8.4,1.39,3.57,.32,'Compatibility energy',16,True,PUR)
eq(8.4,1.81,3.57,'ε_{imj} = − q_{im}^{T} k_{imj} / √d_{k}',17,PUR)

rect(5.02,4.15,1.4,.8,fill=LIGHT,stroke=PUR)
label(5.05,4.2,1.34,.3,'Adapter',15)
eq(5.02,4.59,1.4,'A_{m}',17,PUR)
line([(6.42,4.54),(6.7,4.54)],PUR)
rect(6.7,4.2,1.22,.8,fill=LIGHT,stroke=PUR)
label(6.73,4.24,1.16,.3,'Key',14)
eq(6.7,4.6,1.22,'W_{m}^{K}, b_{m}^{K}',13,PUR)
line([(7.92,4.54),(8.08,4.54),(8.08,2.12),(8.3,2.12)],PUR)
eq(7.51,3.12,.55,'k_{imj}',15,PUR)
line([(6.56,4.54),(6.56,6.14),(6.7,6.14)],PUR)
rect(6.7,5.8,1.22,.8,fill=LIGHT,stroke=PUR)
label(6.73,5.84,1.16,.3,'Value',14)
eq(6.7,6.2,1.22,'W_{m}^{V}, b_{m}^{V}',13,PUR)
line([(7.92,6.14),(8.48,6.14),(8.48,7.04),(8.78,7.04)],PUR)
eq(7.95,6.23,.65,'v_{imj}',16,PUR)
label(5.0,5.14,1.43,.53,'Relation-trained\nKeys and Values',13,color=PUR)

# The free-energy card defines the weights; the closed form is the computation.
line([(10.18,2.29),(10.18,2.68)],PUR)
rect(8.78,2.68,3.29,3.58,fill='#FFF8E8',stroke='#C49A42')
label(8.88,2.79,3.09,.32,'Conditional free energy',17,True)
eq(8.9,3.25,3.05,'F_{im}(α) = Σ_{j∈J_i} α_{j} ε_{imj}',17)
eq(8.9,3.66,3.05,'+ D_{KL}(α ∥ u_{i})',17)
eq(8.9,4.08,3.05,'α_{im}^{*} = arg min [α ∈ Δ(Jᵢ)] F_{im}(α)',15)
label(8.9,4.56,3.05,.32,'Closed form: masked softmax',16,True)
eq(8.88,5.16,1.0,'α_{imj}^{*} =',17)
eq(9.9,4.96,2.05,'exp(−ε_{imj})',17)
line([(9.96,5.35),(11.92,5.35)],INK,False,False,.009)
eq(9.9,5.38,2.05,'Σ_{ℓ∈J_i} exp(−ε_{imℓ})',17)
eq(8.9,5.75,3.05,'α_{imj}^{*} = 0,  j ∉ J_{i}',14)
line([(3.98,4.95),(4.67,4.95),(4.67,6.8),(8.58,6.8),(8.58,5.47),(8.78,5.47)],PUR,True,True,.012)
label(5.0,6.93,2.9,.4,'Support mask from patient activation',13,color=PUR)

line([(10.42,6.26),(10.42,6.65)],PUR)
rect(8.78,6.65,3.29,.9,fill=LIGHT,stroke=PUR)
label(8.9,6.68,3.05,.3,'Weighted knowledge readout',16,True,PUR)
eq(8.9,7.09,3.05,'Σ_{j∈J_i} DropAttn(α^{*})_{j} v_{imj}',16,PUR)
line([(10.42,7.55),(10.42,7.89)],PUR)
rect(8.78,7.89,3.29,.51,'Concat heads + output projection',LIGHT,PUR,15)
line([(10.42,8.4),(10.42,8.7)],PUR)
rect(8.78,8.7,3.29,.66,fill='#EDF2F7',stroke=BLUE)
eq(8.88,8.86,3.09,'h_{im}^{Aug} = LayerNorm(h_{im} + z_{im}^{kg})',16,BLUE)
eq(6.8,8.78,1.4,'Residual h_{im}',14,BLUE)
line([(8.22,9.03),(8.78,9.03)],BLUE)
label(5.0,7.5,3.1,1.0,'Keys shape compatibility energy.\nValues provide knowledge content.\nThe mask selects valid entities.\nuᵢ is uniform over Jᵢ.',14,color=PUR)

# The fused branches use the same augmented features produced in panel b.
label(13.05,.92,3.6,.35,'Knowledge-augmented features',16,True)
rect(13.22,1.53,1.3,.63,'BM','#E8F0E0',GREEN,16,True)
rect(15.12,1.53,1.3,.63,'EHR','#E7EDF4',BLUE,16,True)
line([(14.52,1.79),(15.12,1.79)])
line([(15.12,1.9),(14.52,1.9)])
line([(13.87,2.16),(13.87,2.37),(14.82,2.37),(14.82,2.6)])
line([(15.77,2.16),(15.77,2.37),(14.82,2.37)],INK,False)
rect(13.37,2.6,2.9,.85,'Bidirectional cross-attention\nResidual + LayerNorm','#EFEAF5',PUR,15)
line([(14.82,3.45),(14.82,3.77)])
rect(13.37,3.77,2.9,.64,'Concat + clinical projection','#EFEAF5',PUR,15)
eq(13.37,4.38,2.9,'H_{ab}',18,BLUE,True)
line([(14.82,4.41),(14.82,5.05)],PUR)
label(14.85,4.68,1.2,.25,'Key / Value',13,color=PUR)
rect(13.37,5.05,2.9,.77,'MRI cross-attention\nResidual + LayerNorm','#EFEAF5',PUR,15)
rect(13.02,6.16,1.6,.62,'Augmented MRI','#F5E5D6',ORANGE,14)
line([(13.82,6.16),(13.82,5.82)],ORANGE)
label(13.0,5.84,.85,.25,'Query',13,color=ORANGE)
line([(15.47,5.82),(15.47,6.97)])
eq(15.35,6.1,1.05,'Z_{mri}',16)
line([(13.37,4.55),(12.98,4.55),(12.98,7.3),(13.37,7.3)],BLUE)
rect(13.37,6.97,2.9,.66,fill='#EDF2F7',stroke=BLUE)
eq(13.5,7.12,2.64,'F_{final} = [H_{ab} ∥ Z_{mri}]',16,BLUE)
line([(14.82,7.63),(14.82,7.94)])
rect(13.37,7.94,2.9,.56,'MLP + Softmax','#E1EEF0','#548991',16)
line([(14.82,8.5),(14.82,8.82)])
rect(13.37,8.82,2.9,.59,'ADRD prediction','#FFFFFF',INK,18,True)

line([(12.07,9.03),(12.66,9.03),(12.66,1.31),(15.77,1.31)],PUR,False,False,.012)
line([(13.87,1.31),(13.87,1.53)],GREEN)
line([(15.77,1.31),(15.77,1.53)],BLUE)
line([(12.66,6.47),(13.02,6.47)],ORANGE)

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
