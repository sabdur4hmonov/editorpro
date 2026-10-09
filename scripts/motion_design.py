"""Opt-in source-driven motion; seconds, frame-fraction offsets, clockwise rotation.

Tracks use seconds relative to an element, offsets in frame fractions, clockwise degrees.
Imported lazily by elements.build_elements; legacy behavior remains the default.
"""
from __future__ import annotations
from collections import OrderedDict
import math
import cv2
import numpy as np
import common as C
import elements as E
import motion as M
import motion_language as ML
from PIL import Image, ImageDraw

LIMITS = {'dx': (-1, 1), 'dy': (-1, 1), 'scale': (.05, 3),
          'rotate': (-180, 180), 'opacity': (0, 1)}
IDENTITY = dict(dx=0., dy=0., scale=1., rotate=0., opacity=1.)
EASINGS = ('linear', 'soft', 'snappy', 'spring', 'overshoot')


class Track:
    def __init__(self, frames, duration, cfg):
        self.cfg = cfg
        if not isinstance(frames, list) or len(frames) < 2:
            raise C.MontajError('trajectory: kamida ikki keyframe kerak.')
        previous, state, self.frames = -1., dict(IDENTITY), []
        for row in frames:
            if not isinstance(row, dict) or set(row) - (set(LIMITS) | {'at', 'ease'}):
                raise C.MontajError('trajectory: noma’lum keyframe maydoni.')
            at = float(row.get('at', -1))
            if not math.isfinite(at) or at <= previous or not -1e-9 <= at <= duration+1e-9:
                raise C.MontajError('trajectory.at: takrorlanmas, o‘suvchi va element ichida bo‘lsin.')
            at=min(duration,max(0.,at))
            if not self.frames and at != 0:
                raise C.MontajError('trajectory: birinchi keyframe at=0 bo‘lsin.')
            ease = row.get('ease', 'soft')
            if ease not in EASINGS:
                raise C.MontajError('trajectory.ease: linear/soft/snappy/spring/overshoot kerak.')
            for key, bounds in LIMITS.items():
                value = float(row.get(key, state[key]))
                if not math.isfinite(value) or not bounds[0] <= value <= bounds[1]:
                    raise C.MontajError('trajectory.' + key + ': chekli son va belgilangan oraliq kerak.')
                state[key] = value
            self.frames.append((at, dict(state), ease))
            previous = at

    def at(self, seconds):
        if seconds <= self.frames[0][0]:
            return dict(self.frames[0][1])
        for (a, av, _), (b, bv, ease) in zip(self.frames, self.frames[1:]):
            if seconds < b:
                p = (seconds-a)/(b-a)
                cfg = C.deep_merge(self.cfg, {'easing': {'enter': ease}})
                u = p if ease == 'linear' else ML.curve(p, cfg)
                # Spring/overshoot remains expressive, but alpha/scale cannot become invalid.
                return {key: min(LIMITS[key][1], max(LIMITS[key][0], av[key]+(bv[key]-av[key])*u))
                        for key in IDENTITY}
        return dict(self.frames[-1][1])


def transition_progress(t, start, end, seconds):
    d = min(seconds, (end-start)*.45)
    if d <= 0:
        return 1.
    return M.ease_in_out(min(1., max(0., min((t-start)/d, (end-t)/d))))


def split_geometry(width, height, anchor, progress):
    """A single source crop, never a crossfade between two copies of a face."""
    p = min(1., max(0., progress))
    half = height//2
    ch = float(half)
    target_y = min(max(0., anchor[1]*height-ch*.42), height-ch)
    return (0, int(round(target_y*p)), width,
            int(round(height+(ch-height)*p)), int(round(height+(half-height)*p)))


class MotionBroll(E.BrollLayer):
    def __init__(self, ctx, el):
        super().__init__(ctx, el)
        self.morph = el.get('transition') == 'layout_morph' and self.mode == 'split'
        if el.get('transition') not in (None, 'layout_morph'):
            raise C.MontajError('broll.transition: faqat layout_morph mavjud.')
        self.morph_seconds = float(el.get('transition_seconds', ML.duration(ML.config(ctx.style), 'transition')))
        self.seam_color = M.rgb(ctx.style.get('motion_design', {}).get('seam_color', '#EBEBEB'))
        if not math.isfinite(self.morph_seconds) or self.morph_seconds < 0:
            raise C.MontajError('broll.transition_seconds: manfiy bo‘lmagan chekli son kerak.')

    def draw(self, frame, t):
        if not self.morph:
            return super().draw(frame, t)
        p = transition_progress(t, self.start, self.end, self.morph_seconds)
        if p <= 0:
            return
        content = self._content(t)
        if content is None:
            return
        content = content[..., :3]
        if self.bw:
            content = cv2.cvtColor(cv2.cvtColor(content, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
        if self.dim:
            content = cv2.convertScaleAbs(content, alpha=1-self.dim)
        if self.lower_gradient:
            top = M.clamp01(float(self.lower_gradient.get('from', .52)))
            amount = M.clamp01(float(self.lower_gradient.get('amount', .5)))
            ramp = np.clip((np.linspace(0, 1, content.shape[0])-top)/max(.001, 1-top), 0, 1)
            content = (content.astype(np.float32)*(1-ramp[:, None, None]*amount)).astype(np.uint8)
        W, H = self.ctx.W, self.ctx.H
        x, y, cw, ch, out_h = split_geometry(W, H, self.ctx.anchor, p)
        # Resize the original ONCE into a moving viewport; there is only one doctor.
        doctor = cv2.resize(frame[y:y+ch, x:x+cw], (W, out_h), interpolation=cv2.INTER_LINEAR)
        bh = H-out_h
        frame[:out_h] = doctor
        if bh:
            frame[out_h:] = content[-bh:]
            seam = max(1, round(2*self.ctx.k*p))
            frame[max(0, out_h-seam):out_h] = self.seam_color


class MotionImage(E.ImageLayer):
    def __init__(self, ctx, el):
        super().__init__(ctx, el)
        self.track = Track(el['trajectory'], self.end-self.start, ML.config(ctx.style)) if 'trajectory' in el else None
        self.transform_cache = OrderedDict()
        self.cache_limit = 24*1024*1024
        self.blur_max = float(ctx.style.get('motion_design', {}).get('fast_blur_px', 0))
        if not math.isfinite(self.blur_max) or not 0 <= self.blur_max <= 8:
            raise C.MontajError('motion_design.fast_blur_px: 0..8 kerak.')
        self.blur_max *= ctx.k

    def transformed(self, sprite, angle, blur):
        # Static sprites only: video frames must never reuse another frame's pixels.
        key = (id(sprite), round(angle*2)/2, int(round(blur)))
        if self.reader is None and key in self.transform_cache:
            self.transform_cache.move_to_end(key)
            return self.transform_cache[key]
        rot = key[1]
        result = sprite
        if abs(rot) > .01:
            matrix = cv2.getRotationMatrix2D((sprite.w/2, sprite.h/2), -rot, 1)
            cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
            nw, nh = math.ceil(sprite.w*cos+sprite.h*sin), math.ceil(sprite.h*cos+sprite.w*sin)
            matrix[0, 2] += (nw-sprite.w)/2
            matrix[1, 2] += (nh-sprite.h)/2
            pix = cv2.warpAffine(sprite.pix, matrix, (nw, nh), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            result = M.Sprite(pix, -nw/2, -nh/2)
        if blur >= .5:
            result = result.blurred(blur)
        if self.reader is None and result.pix.nbytes <= self.cache_limit:
            self.transform_cache[key] = result
            while len(self.transform_cache) > 16 or sum(s.pix.nbytes for s in self.transform_cache.values()) > self.cache_limit:
                self.transform_cache.popitem(last=False)
        return result

    def draw(self, frame, t):
        if self.track is None:
            return super().draw(frame, t)
        state = self.track.at(t-self.start)
        previous = self.track.at(max(0., t-self.start-1/self.ctx.fps))
        speed = math.hypot((state['dx']-previous['dx'])*self.ctx.W,
                           (state['dy']-previous['dy'])*self.ctx.H)*self.ctx.fps
        blur = self.blur_max*min(1., speed/max(1., self.ctx.H*1.2))
        sprite = self.reader.sprite_at(t-self.start) if self.reader is not None else self.spr
        if sprite is None:
            return
        sprite = self.transformed(sprite, state['rotate'], blur)
        M.blit(frame, sprite, self.cx+state['dx']*self.ctx.W, self.cy+state['dy']*self.ctx.H,
               opacity=state['opacity']*self.opacity, scale=state['scale'], anchor=(0, 0))


class MotionStage(E.StageLayer):
    def __init__(self, ctx, el):
        super().__init__(ctx, el)
        self.morph = el.get('transition') == 'layout_morph'
        if el.get('transition') not in (None, 'layout_morph'):
            raise C.MontajError('stage.transition: faqat layout_morph mavjud.')
        self.morph_seconds = float(el.get('transition_seconds', ML.duration(ML.config(ctx.style), 'follow')))
        if not math.isfinite(self.morph_seconds) or self.morph_seconds < 0:
            raise C.MontajError('stage.transition_seconds: manfiy bo‘lmagan chekli son kerak.')
        # Existing complex events remain available through the legacy renderer. Avoid silently
        # losing progress/footer/punch/flash while opting into this prototype's simpler morph.
        if self.morph and any(el.get(key) for key in ('footer', 'progress', 'punch', 'shake', 'flash')):
            raise C.MontajError('stage layout_morph: footer/progress/punch/shake/flash hozir qo‘llanmaydi.')

    def draw(self, frame, t):
        if not self.morph:
            return super().draw(frame, t)
        p = transition_progress(t, self.start, self.end, self.morph_seconds)
        if p <= 0:
            return
        W, H = self.ctx.W, self.ctx.H
        sx0, sy0 = round(self.sx0*p), round(self.sy0*p)
        sx1, sy1 = round(W+(self.sx1-W)*p), round(H+(self.sy1-H)*p)
        width, height = max(2, round(W+(self.cw-W)*p)), max(2, round(H+(self.ch-H)*p))
        ox = min(max(0, round((self.cx-self.cw/2)*p)), W-width)
        oy = min(max(0, round((self.cy-self.ch/2)*p)), H-height)
        card = cv2.resize(frame[sy0:sy1, sx0:sx1], (width, height), interpolation=cv2.INTER_LINEAR)
        self.backdrop.draw(frame, t, 0)
        radius = min(round(self.radius*p), width//2, height//2)
        if radius:
            # Small antialiased masks, bounded by actual card size. One source view only.
            mask = np.full((height, width), 255, np.uint8)
            corner = np.zeros((radius*2, radius*2), np.uint8)
            cv2.circle(corner, (radius, radius), radius, 255, -1, cv2.LINE_AA)
            mask[:radius, :radius] = corner[:radius, :radius]
            mask[:radius, -radius:] = corner[:radius, radius:]
            mask[-radius:, :radius] = corner[radius:, :radius]
            mask[-radius:, -radius:] = corner[radius:, radius:]
            alpha = mask.astype(np.float32)[..., None]/255
            region = frame[oy:oy+height, ox:ox+width]
            region[:] = (card*alpha+region*(1-alpha)).astype(np.uint8)
        else:
            frame[oy:oy+height, ox:ox+width] = card


def number(value, name, low, high):
    value=float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise C.MontajError(f'{name}: {low}..{high} chekli son kerak.')
    return value


def warp(sprite, state, pivot=(0.,0.)):
    """Premultiplied affine sprite about a chosen local pivot; transparent borders."""
    angle,scale=state['rotate'],state['scale']
    if abs(angle)<.001 and abs(scale-1)<.001:
        return sprite
    px,py=pivot[0]-sprite.ox,pivot[1]-sprite.oy
    matrix=cv2.getRotationMatrix2D((px,py),-angle,scale)
    corners=np.array([[0,0],[sprite.w,0],[0,sprite.h],[sprite.w,sprite.h]],np.float64)
    coords=corners@matrix[:,:2].T+matrix[:,2]
    x0,y0=np.floor(coords.min(axis=0));x1,y1=np.ceil(coords.max(axis=0))
    matrix[:,2]-=[x0,y0]
    nw,nh=max(1,int(x1-x0)),max(1,int(y1-y0))
    if nw*nh>24_000_000:
        raise C.MontajError('trajectory transform juda katta: scale yoki card/canvas o‘lchamini kamaytiring.')
    pixels=cv2.warpAffine(sprite.pix,matrix,(nw,nh),flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    return M.Sprite(pixels,x0+sprite.ox,y0+sprite.oy)


class TrackedText(E.Layer):
    """Reuse RichBlock including per-word motion, then animate the whole block about pivot."""
    def __init__(self,ctx,el):
        super().__init__(el['start'],el['end']);self.ctx=ctx
        plain=dict(el);plain.pop('trajectory',None)
        self.child=E.TextLayer(ctx,plain);self.z=self.child.z
        self.behind_person=self.child.behind_person
        self.track=Track(el['trajectory'],self.end-self.start,ML.config(ctx.style))
        p=el.get('pivot',[el.get('x',.5),el.get('y',.3)])
        if not isinstance(p,list) or len(p)!=2:raise C.MontajError('pivot: [x,y] kerak.')
        self.pivot=tuple(number(v,'pivot',0,1)*d for v,d in zip(p,(ctx.W,ctx.H)))

    def draw(self,frame,t):
        canvas=np.zeros((self.ctx.H,self.ctx.W,4),np.uint8)
        self.child.draw(canvas,t)
        yy,xx=np.nonzero(canvas[...,3])
        if not len(xx):return
        x0,x1,y0,y1=xx.min(),xx.max()+1,yy.min(),yy.max()+1
        spr=M.Sprite(canvas[y0:y1,x0:x1],x0-self.pivot[0],y0-self.pivot[1])
        st=self.track.at(t-self.start);spr=warp(spr,st)
        M.blit(frame,spr,self.pivot[0]+st['dx']*self.ctx.W,self.pivot[1]+st['dy']*self.ctx.H,st['opacity'])


MATERIALS=('paper','grid','ticket','polaroid','film','pill')


class CardLayer(E.Layer):
    """Original procedural material cards; uses only project/user assets and installed fonts."""
    z=35
    def __init__(self,ctx,el):
        super().__init__(el['start'],el['end']);self.ctx=ctx
        material=el.get('material','paper')
        if material not in MATERIALS:raise C.MontajError('card.material: '+', '.join(MATERIALS))
        self.cx=number(el.get('x',.5),'card.x',0,1)*ctx.W
        self.cy=number(el.get('y',.42),'card.y',0,1)*ctx.H
        w=max(8,round(number(el.get('width',.76),'card.width',.03,1.5)*ctx.W))
        h=max(8,round(number(el.get('height',.18),'card.height',.02,1.5)*ctx.H))
        radius=round(min(w,h)*number(el.get('radius',.05),'card.radius',0,.5))
        self.track=Track(el['trajectory'],self.end-self.start,ML.config(ctx.style)) if 'trajectory' in el else None
        p=el.get('pivot',[.5,.5])
        if not isinstance(p,list) or len(p)!=2:raise C.MontajError('card.pivot: [x,y] kerak.')
        self.pivot=((number(p[0],'card.pivot',0,1)-.5)*w,(number(p[1],'card.pivot',0,1)-.5)*h)
        cfg=ctx.style.get('motion_design',{})
        color=el.get('color',cfg.get('paper_color','#F4EEDF'))
        text_color=el.get('text_color','#172126')
        self.active_at=None
        if 'active_at' in el:self.active_at=number(el['active_at'],'card.active_at',self.start,self.end)
        accent=el.get('active_color',ctx.style.get('captions',{}).get('accent','#F4BE4F'))
        self.sprites=[self.make(ctx,el,material,w,h,radius,color,text_color)]
        if self.active_at is not None:self.sprites.append(self.make(ctx,el,material,w,h,radius,accent,text_color))
        self.anim=el.get('anim','pop')
        if self.anim not in ('none','pop','fade'):raise C.MontajError('card.anim: none/pop/fade kerak.')
        ctx.check_safe('Kartochka',self.cx-w/2,self.cy-h/2,self.cx+w/2,self.cy+h/2)

    @staticmethod
    def make(ctx,el,material,w,h,radius,color,text_color):
        rng=np.random.default_rng(int(ctx.style.get('motion_design',{}).get('material_seed',41)))
        base=np.empty((h,w,4),np.uint8);base[:]=M.rgb(color)+(255,)
        if material in ('paper','grid','ticket'):
            noise=rng.integers(-3,4,(h,w,1),dtype=np.int16)
            base[...,:3]=np.clip(base[...,:3].astype(np.int16)+noise,0,255).astype(np.uint8)
        img=Image.fromarray(base);draw=ImageDraw.Draw(img)
        pad=max(4,round(w*.055))
        if material=='grid':
            step=max(8,round(w*.065));line=M.rgb(el.get('grid_color','#C9C6B9'))+(180,)
            for x in range(0,w,step):draw.line((x,0,x,h),fill=line,width=1)
            for y in range(0,h,step):draw.line((0,y,w,y),fill=line,width=1)
        if material=='ticket':
            mid=round(w*.76);dash=max(3,round(h*.035))
            for y in range(pad,h-pad,dash*3):draw.line((mid,y,mid,y+dash),fill=(100,110,107,180),width=1)
            rr=max(2,round(h*.05))
            draw.ellipse((mid-rr,-rr,mid+rr,rr),fill=(0,0,0,0));draw.ellipse((mid-rr,h-rr,mid+rr,h+rr),fill=(0,0,0,0))
        if material=='film':
            for x in range(pad,w-pad,max(8,round(w*.07))):
                for y in (2,h-pad):draw.rounded_rectangle((x,y,x+max(3,pad//2),y+pad//2),2,fill=(0,0,0,0))
        photo_bottom=pad
        if el.get('file'):
            src=Image.open(ctx.asset(el['file'],'card.file')).convert('RGB')
            fraction=number(el.get('photo_fraction',.66),'card.photo_fraction',.1,.9)
            ph=max(1,round(h*fraction)-pad);pw=w-2*pad
            scale=max(pw/src.width,ph/src.height);src=src.resize((max(pw,round(src.width*scale)),max(ph,round(src.height*scale))),Image.Resampling.LANCZOS)
            left=(src.width-pw)//2;top=(src.height-ph)//2
            img.paste(src.crop((left,top,left+pw,top+ph)),(pad,pad));photo_bottom=pad+ph+pad//2
        text=C.strip_markup(str(el.get('text','')))
        if text:
            size=max(6,round(number(el.get('font_size',70),'card.font_size',8,300)*ctx.k))
            font=ctx.fonts.get(el.get('font','Inter'),size,int(el.get('weight',700)))
            # Fit actual text; never truncate an Uzbek grapheme or invent a shortened claim.
            lines=[]
            for line in text.splitlines():
                current=''
                for word in line.split():
                    candidate=(current+' '+word).strip()
                    if current and font.getlength(candidate)>w-2*pad:lines.append(current);current=word
                    else:current=candidate
                lines.append(current)
            available=h-photo_bottom-pad
            for _ in range(12):
                if len(lines)*size*1.17<=available and max((font.getlength(x) for x in lines),default=0)<=w-2*pad:break
                size=max(6,round(size*.87));font=ctx.fonts.get(el.get('font','Inter'),size,int(el.get('weight',700)))
            if len(lines)*size*1.17>available or max((font.getlength(x) for x in lines),default=0)>w-2*pad:
                raise C.MontajError('card.text sig‘madi; card.height/width ni oshiring.')
            draw=ImageDraw.Draw(img);y=photo_bottom+max(0,(available-len(lines)*size*1.17)/2)+size*.85
            for line in lines:
                x=(w-font.getlength(line))/2
                M.draw_text(draw,(x,y),line,font,M.rgb(text_color)+(255,),anchor='ls');y+=size*1.17
        shape=el.get('shape','rounded')
        if shape not in ('rounded','diagonal','arch'):raise C.MontajError('card.shape: rounded/diagonal/arch kerak.')
        mask=Image.new('L',(w,h),0);md=ImageDraw.Draw(mask)
        if shape=='diagonal':md.polygon([(round(w*.15),0),(w,0),(round(w*.85),h),(0,h)],fill=255)
        elif shape=='arch':md.rounded_rectangle((0,0,w-1,h-1),radius=min(w,h)//2,fill=255)
        else:md.rounded_rectangle((0,0,w-1,h-1),radius=radius if material!='pill' else min(w,h)//2,fill=255)
        alpha=np.minimum(np.asarray(img)[...,3],np.asarray(mask));img.putalpha(Image.fromarray(alpha))
        return M.pil_sprite(img,shadow={'blur':8*ctx.k,'dy':5*ctx.k,'opacity':.25})

    def draw(self,frame,t):
        spr=self.sprites[int(self.active_at is not None and t>=self.active_at)]
        if self.track:
            state=self.track.at(t-self.start);spr=warp(spr,state,self.pivot)
            M.blit(frame,spr,self.cx+state['dx']*self.ctx.W,self.cy+state['dy']*self.ctx.H,state['opacity'])
        else:
            op,scale=(1.,1.) if self.anim=='none' else self.appear(t,self.start,self.end)
            if self.anim=='fade':scale=1.
            M.blit(frame,spr,self.cx,self.cy,op,scale)


class CanvasLayer(E.Layer):
    """One composition camera for timed text/cards/images; nested canvases are rejected."""
    z=20
    def __init__(self,ctx,el):
        super().__init__(el['start'],el['end']);self.ctx=ctx
        self.track=Track(el['trajectory'],self.end-self.start,ML.config(ctx.style)) if 'trajectory' in el else None
        self.background=el.get('background')
        if self.background is not None:M.rgb(self.background)
        children=[]
        for item in el.get('items',[]):
            if item.get('behind_person'):
                raise C.MontajError('canvas.items behind_person qo‘llanmaydi; uni alohida top-level element qiling.')
            if item.get('type') not in ('text','title','image','card'):
                raise C.MontajError('canvas.items: faqat text/title/image/card kerak.')
            child=dict(item,start=item.get('at',self.start),end=item.get('end',self.end));child.pop('at',None)
            if not self.start<=float(child['start'])<float(child['end'])<=self.end:
                raise C.MontajError('canvas.items vaqtlar canvas ichida bo‘lsin (absolute seconds).')
            children.append(child)
        if not children:raise C.MontajError('canvas.items bo‘sh.')
        self.children=E.build_elements(ctx,children,self.end)

    def draw(self,frame,t):
        canvas=np.zeros((self.ctx.H,self.ctx.W,4),np.uint8)
        if self.background is not None:canvas[:]=M.rgb(self.background)+(255,)
        for child in sorted(self.children,key=lambda c:c.z):
            if child.active(t):child.draw(canvas,t)
        if self.track:
            spr=M.Sprite(canvas,-self.ctx.W/2,-self.ctx.H/2)
            st=self.track.at(t-self.start);spr=warp(spr,st)
            M.blit(frame,spr,self.ctx.W/2+st['dx']*self.ctx.W,self.ctx.H/2+st['dy']*self.ctx.H,st['opacity'])
        else:M.blit(frame,M.Sprite(canvas),0,0)

    def close(self):
        for child in self.children:child.close()


def build(ctx,el,total):
    kind=el['type']
    if kind=='card':return CardLayer(ctx,el)
    if kind=='canvas':return CanvasLayer(ctx,el)
    if el.get('transition')=='layout_morph':
        if kind=='broll':return MotionBroll(ctx,el)
        if kind=='stage':return MotionStage(ctx,el)
        raise C.MontajError('layout_morph faqat broll/stage uchun.')
    if 'trajectory' in el:
        if kind=='image':return MotionImage(ctx,el)
        if kind in ('text','title'):return TrackedText(ctx,el)
        raise C.MontajError('trajectory faqat image/text/title/card/canvas uchun.')
    return E.ELEMENT_TYPES[kind](ctx,el)


def caption_recipe(style,cfg,cue,opts):
    """Structure-specific choices reuse existing entrances; explicit cue animation wins."""
    if not cfg.get('_motion') or any(k in opts for k in ('anim','anim_main','anim_sub','exit','emphasis')):
        return cfg
    seconds=style.get('_energy',{}).get('seconds',[])
    role=seconds[min(len(seconds)-1,max(0,int(cue['start'])))]['structure'] if seconds else 'key_point'
    recipe=style.get('motion_design',{}).get('caption_recipes',{}).get(role)
    if not recipe:return cfg
    if recipe.get('enter') not in ML.ENTRANCES or recipe.get('sub') not in ML.ENTRANCES or recipe.get('emphasis') not in ML.EMPHASIS:
        raise C.MontajError('motion_design.caption_recipes: mavjud enter/sub/emphasis kerak.')
    mc=C.deep_merge(cfg['_motion'],{'choice':recipe})
    return dict(cfg,animation=recipe['enter'],anim_main=recipe['enter'],anim_sub=recipe['sub'],
                emphasis=recipe['emphasis'],exit=mc['pairs'][recipe['enter']],_motion=mc)
