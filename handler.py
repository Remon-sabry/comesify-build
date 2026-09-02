import os, json, tempfile, subprocess, requests, html
import runpod

def ass_time(x):
    x=max(0,float(x)); h=int(x//3600); m=int((x%3600)//60); s=int(x%60); cs=int((x-int(x))*100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def hex_ass(h, alpha='00'):
    h=str(h or '#FFFFFF').replace('#','')
    if len(h)==3: h=''.join(c*2 for c in h)
    if len(h)!=6: h='FFFFFF'
    return '&H'+alpha+h[4:6]+h[2:4]+h[0:2]

def esc(s): return str(s or '').replace('{','').replace('}','').replace('\\','').replace('\n','\\N').replace('\r','')

def style_cfg(k,color):
    primary=hex_ass(color or '#FFFFFF')
    return {
      'viral':(74,'&H00101018','&H90000000',3,6,0,1,hex_ass('#FFE600'),6,True,True,360,False),
      'karaoke':(72,'&H00000000','&H85000000',3,5,1,1,primary,6,True,True,360,False),
      'neon':(70,hex_ass('#111111'),'&H99000000',1,5,2,1,primary,6,True,True,350,False),
      'clean':(56,'&H00101010','&H00000000',1,3,1,0,primary,8,False,False,320,False),
      'box':(60,'&H00151515','&HAA151515',3,3,0,1,primary,6,True,True,330,False),
      'podcast':(48,'&HA0000000','&H00000000',3,2,0,0,primary,8,False,False,300,False),
      'bold':(80,'&H00000000','&H00000000',1,9,0,1,hex_ass('#FFE600'),6,True,True,360,True)
    }.get(k,(74,'&H00101018','&H90000000',3,6,0,1,hex_ass('#FFE600'),6,True,True,360,False))

def font_for(lang):
    c=str(lang or 'en').lower().split('-')[0]
    return {'ar':'Noto Sans Arabic','hi':'Noto Sans Devanagari'}.get(c,'Roboto')

def make_ass(clip,style,edit,words,lang):
    color=(edit or {}).get('captionColor','#FFFFFF'); fs,outline,back,bstyle,bord,shadow,bold,emph,cadence,emoji,pop,marginv,upper=style_cfg(style,color)
    # ASS PlayRes remains 1080x1920 exactly like the browser renderer.
    events=[]; cstart=float(clip.get('start',0)); cend=float(clip.get('end',0)); dur=max(.01,cend-cstart)
    emphset={str(x).lower() for x in clip.get('emphasis_words',[]) if x}
    emojis=[str(x) for x in clip.get('emojis',[]) if x][:3] or ['🔥','✨','💯']
    for idx,w in enumerate(words):
        ws=float(w.get('start',0)); we=float(w.get('end',0));
        if we<=cstart or ws>=cend: continue
        wst=max(0,ws-cstart); wen=min(dur,we-cstart)
        if wen<=wst: wen=wst+.16
        wen=min(dur,wen+.04); raw=str(w.get('word','')); pure=esc(raw)
        if upper: pure=pure.upper()
        is_emph=raw.lower() in emphset; col=emph if is_emph else hex_ass(color); scale=126 if is_emph else 106
        size_tag=(f'\\fscx72\\fscy72\\t(0,110,\\fscx{scale}\\fscy{scale})' if pop else f'\\fscx{scale}\\fscy{scale}')
        base_y=1920-marginv; enter=f'\\move(540,{base_y+24},540,{base_y},0,140)'
        text='{'+enter+size_tag+'\\c'+col+'\\b'+('1' if is_emph or bold else '0')+'}'+pure
        if emoji and emojis and (idx+1)%cadence==0: text+=' {\\fnNoto Emoji}'+emojis[(idx//cadence)%len(emojis)]+'{\\fn'+font_for(lang)+'}'
        events.append(f'Dialogue: 0,{ass_time(wst)},{ass_time(wen)},Default,,0,0,0,,{{\\an2}}{text}')
    if not events:
        fallback=esc(clip.get('hook') or clip.get('title') or '')
        if fallback: events.append(f'Dialogue: 0,0:00:00.00,{ass_time(dur)},Default,,0,0,0,,{{\\an2}}'+fallback+'\\N')
    ov=(edit or {}).get('overlay') or {}
    if ov.get('text'):
        ox=max(40,min(1040,round(float(ov.get('x',540) or 540)))); oy=max(40,min(1880,round(float(ov.get('y',260) or 260)))); oc=hex_ass(ov.get('color','#FFFFFF')); ofs=max(28,min(140,round(float(ov.get('size',64) or 64)))); border=hex_ass(ov.get('outline','#000000'))
        tag=f'{{\\an5\\pos({ox},{oy})\\fs{ofs}\\c{oc}\\bord'+('4' if ov.get('outline') else '0')+f'\\3c{border}\\b1\\q2}}'
        events.append(f'Dialogue: 10,0:00:00.00,{ass_time(dur)},Default,,0,0,0,,{tag}{esc(ov.get("text"))}')
    return '[Script Info]\nScriptType: v4.00+\nPlayResX:1080\nPlayResY:1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n'+f'Style: Default,{font_for(lang)},{fs},{hex_ass(color)},&H000000FF,{outline},{back},{bold},0,0,0,100,100,0,0,{bstyle},{bord},{shadow},2,60,60,{marginv},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'+'\n'.join(events)+'\n'

def clamp(x,a,b): return max(a,min(b,float(x)))
def keyframe_expr(points,dur):
    raw=points if isinstance(points,list) and points else [{'t':0,'x':0},{'t':1,'x':0}]
    p=sorted([{'t':clamp(q.get('t',0),0,dur),'x':clamp(q.get('x',0),-1,1)} for q in raw], key=lambda z:z['t'])
    if len(p)==1: p.append({'t':dur,'x':p[0]['x']})
    expr=str(p[-1]['x'])
    for k in range(len(p)-2,-1,-1):
        a,b=p[k],p[k+1]; span=max(.001,b['t']-a['t']); seg=f"({a['x']}+({b['x']-a['x']:.6f})*(t-{a['t']:.4f})/{span:.4f})"; expr=f"if(lt(t,{b['t']:.4f}),{seg},{expr})"
    return expr

def normal_crop(expr,W=1080,H=1920):
    cropx=f"(iw-min(iw,ih*9/16))/2*(1+({expr}))"
    return f"crop='min(iw,ih*9/16)':'min(ih,iw*16/9)':'{cropx}':'(ih-min(ih,iw*16/9))/2',scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"

def static_half(side,W=1080,H=1920):
    half=(H-24)//2; x='0' if side=='left' else 'iw/2'; return half,f"crop=iw/2:ih:{x}:0,scale={W}:{half}:force_original_aspect_ratio=decrease,pad={W}:{half}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"

def render(inp,src,out,ass):
    clip=inp['clip']; edit=inp.get('edit') or {}; layout=edit.get('layout','manual'); dur=max(.01,float(clip['end'])-float(clip['start'])); pts=edit.get('keyframes') or []
    face=edit.get('faceLayout'); hybrid=layout=='auto' and isinstance(face,dict) and isinstance(face.get('splitSegments'),list) and face.get('splitSegments') and face.get('top') and face.get('bottom')
    fullsplit=bool(edit.get('splitScreen')) and layout=='split' and not hybrid
    enc=['-c:v','h264_nvenc','-preset','p4','-cq','24','-c:a','aac','-b:a','128k','-movflags','+faststart','-y',out]
    # fallback to software x264 if NVENC is unavailable on the selected GPU image.
    if hybrid or fullsplit:
        if fullsplit:
            half,lc=static_half('left'); _,rc=static_half('right'); off=half+24
            graph=f"[0:v]split=2[sp1][sp2];[sp1]{lc}[topv];[sp2]{rc}[botv];color=c=black:s=1080x1920:r=30:d={dur:.3f}[bg];[bg][topv]overlay=0:0[one];[one][botv]overlay=0:{off}[stack];[stack]settb=AVTB,fps=30,setsar=1,format=yuv420p,ass={ass}:fontsdir=/opt/ias-fonts[vout]"
            args=['-ss',str(clip['start']),'-i',src,'-t',str(dur),'-filter_complex',graph,'-map','[vout]','-map','0:a:0?']+enc
        else:
            segs=[{'start':max(0,float(x.get('start',0))),'end':min(dur,float(x.get('end',0)))} for x in face['splitSegments'] if float(x.get('end',0))-float(x.get('start',0))>.08]
            cuts=sorted(set([0,dur]+[v for x in segs for v in (x['start'],x['end'])])); parts=[]
            for a,b in zip(cuts,cuts[1:]):
                if b-a<.05: continue
                mid=(a+b)/2; issp=any(mid>=x['start']-.001 and mid<=x['end']+.001 for x in segs); parts.append((a,b,issp))
            labels=[]; srcs='[0:v]split='+str(len(parts))+''.join(f'[src{k}]' for k in range(len(parts)))+';'
            graph=srcs
            for k,(a,b,issp) in enumerate(parts):
                source=f'[src{k}]'; lab=f'p{k}'
                if not issp:
                    graph+=f'{source}trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS,{normal_crop(keyframe_expr(pts,b-a))}[{lab}];'
                else:
                    A,B,T,U=f'a{k}',f'b{k}',f't{k}',f'u{k}'; half,lc=static_half('left'); _,rc=static_half('right'); off=half+24
                    graph+=f'{source}trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS,split=2[{A}][{B}];[{A}]{lc}[{T}];[{B}]{rc}[{U}];color=c=black:s=1080x1920:r=30:d={b-a:.4f}[bg{k}];[bg{k}][{T}]overlay=0:0[o{k}];[o{k}][{U}]overlay=0:{off}[{lab}];'
                labels.append(f'[{lab}]')
            graph+=''.join(labels)+f'concat=n={len(labels)}:v=1:a=0,settb=AVTB,fps=30,setsar=1,format=yuv420p,ass={ass}:fontsdir=/opt/ias-fonts[vout]'
            args=['-ss',str(clip['start']),'-i',src,'-t',str(dur),'-filter_complex',graph,'-map','[vout]','-map','0:a:0?']+enc
    else:
        vf=normal_crop(keyframe_expr(pts,dur) if pts else '0')+f",ass={ass}:fontsdir=/opt/ias-fonts"; args=['-ss',str(clip['start']),'-i',src,'-t',str(dur),'-vf',vf,'-map','0:v:0','-map','0:a:0?']+enc
    r=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error']+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if r.returncode!=0:
        enc2=['-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-b:a','128k','-movflags','+faststart','-y',out]
        args2=args[:-len(enc)]+enc2
        r=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error']+args2,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if r.returncode!=0: raise RuntimeError(r.stderr.decode(errors='ignore')[-3000:])

def handler(job):
    inp=job['input']; tmp=tempfile.mkdtemp(prefix='ias-rp-'); src=os.path.join(tmp,'source.mp4'); out=os.path.join(tmp,'result.mp4'); ass=os.path.join(tmp,'caps.ass')
    try:
        with requests.get(inp['source_url'],stream=True,timeout=120) as rr:
            rr.raise_for_status();
            with open(src,'wb') as f:
                for chunk in rr.iter_content(1024*1024):
                    if chunk:f.write(chunk)
        with open(ass,'w',encoding='utf-8') as f:f.write(make_ass(inp['clip'],inp.get('caption_style','viral'),inp.get('edit') or {},inp.get('words') or [],inp.get('language','en')))
        render(inp,src,out,ass)
        with open(out,'rb') as f:
            rr=requests.post(inp['callback_url'],files={'file':('render.mp4',f,'video/mp4')},data={'status':'COMPLETED'},timeout=180)
            rr.raise_for_status()
        return {'status':'COMPLETED'}
    except Exception as e:
        try: requests.post(inp['callback_url'],json={'status':'FAILED','error':str(e)[:1200]},timeout=20)
        except Exception: pass
        raise
    finally:
        import shutil; shutil.rmtree(tmp,ignore_errors=True)

runpod.serverless.start({'handler':handler})
