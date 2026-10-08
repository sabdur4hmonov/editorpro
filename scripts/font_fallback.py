"""Per-character fallback with baseline-aligned spans; no font downloads."""
from functools import lru_cache
from PIL import ImageFont
import common as C
import glyph_audit as G

@lru_cache(maxsize=8192)
def covers(path, ch):
    try:
        return not G.missing(path, ch)
    except (OSError, ValueError, IndexError, G.struct.error):
        return False

class Font:
    def __init__(self, primary, owner, weight, italic):
        self.primary = primary
        self.owner = owner
        self.size = primary.size
        self.weight, self.italic = weight, italic
        self.chars = {}

    def character_font(self, ch):
        if ch in self.chars:
            return self.chars[ch]
        font = self.primary
        if not covers(str(font.path), ch):
            entries = sorted(self.owner.entries, key=lambda e: (
                e['family'] != 'inter', e['italic'] != self.italic, abs(e['weight']-self.weight)))
            entry = next((e for e in entries if covers(e['path'], ch)), None)
            if entry is None and not self.owner.system_scanned:
                self.owner._scan_system()
                return self.character_font(ch)
            if entry:
                font = self.owner.get(entry['family'], self.size, self.weight, self.italic).primary
                # A family can have several files; ensure the selected file has this glyph.
                if not covers(str(font.path), ch):
                    font = ImageFont.truetype(entry['path'], self.size)
            key = ('fallback', str(self.primary.path), ch)
            if key not in self.owner.warned:
                self.owner.warned.add(key)
                C.warn(f'Glyph fallback U+{ord(ch):04X}: {self.primary.getname()[0]} -> '
                       f'{font.getname()[0] if entry else "MISSING in all installed fonts"}')
        self.chars[ch] = font
        return font

    def runs(self, text):
        runs = []
        for ch in text:
            font = self.character_font(ch)
            if runs and runs[-1][1] is font:
                runs[-1] = (runs[-1][0]+ch, font)
            else:
                runs.append((ch, font))
        return runs

    def getlength(self, text):
        return sum(font.getlength(run) for run, font in self.runs(text))

    def getmetrics(self):
        fonts = [self.primary] + list(self.chars.values())
        return tuple(max(f.getmetrics()[i] for f in fonts) for i in (0, 1))

    def draw(self, draw, xy, text, fill, anchor='ls', stroke_width=0, stroke_fill=None):
        runs = self.runs(text)
        x, y = xy
        if anchor == 'la':
            y += self.primary.getmetrics()[0]
        elif anchor != 'ls':
            raise C.MontajError(f'Fallback text anchor not supported: {anchor}')
        for run, font in runs:
            draw.text((x, y), run, font=font, fill=fill, anchor='ls',
                      stroke_width=stroke_width, stroke_fill=stroke_fill)
            x += font.getlength(run)
