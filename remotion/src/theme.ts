// Shared look for every overlay scene. Values come from props (brand / per-video style), never hard-coded per scene.
import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export type Theme = {
  accent: string;
  text: string;
  paper: string;
  ink: string;
  font: string;      // body / sub words
  display: string;   // condensed hero words
};

export const DEFAULT_THEME: Theme = {
  accent: '#F4BE4F',
  text: '#FFFFFF',
  paper: '#F4EEDF',
  ink: '#172126',
  font: 'Onest',
  display: 'Oswald',
};

// Local fonts (OFL): style/fonts copied by render.mjs + extra display fonts in public/fonts (temp/fonts_extra/selected,
// licences OFL_*.txt). No network fonts. Coverage measured with Pillow (U+02BB okina / Uzbek+Russian Cyrillic):
//   full: Oswald, Cormorant (+Italic), Lora Italic | Russian ok, no okina: Alumni Sans, Roboto Condensed
//   Latin only: Anton (+okina), Space Grotesk (+okina), Instrument Serif (no okina -> use ASCII apostrophe)
const FILES: Record<string, Array<[string, 'normal' | 'italic']>> = {
  Onest: [['Onest.ttf', 'normal']], Oswald: [['Oswald.ttf', 'normal']],
  Inter: [['Inter.ttf', 'normal'], ['Inter-Italic.ttf', 'italic']], Montserrat: [['Montserrat.ttf', 'normal'], ['Montserrat-Italic.ttf', 'italic']],
  Unbounded: [['Unbounded.ttf', 'normal']], Caveat: [['Caveat.ttf', 'normal']], 'Playfair Display': [['PlayfairDisplay-Italic.ttf', 'italic']],
  Anton: [['Anton.ttf', 'normal']], 'Alumni Sans': [['AlumniSans.ttf', 'normal'], ['AlumniSans-Italic.ttf', 'italic']],
  Cormorant: [['Cormorant.ttf', 'normal'], ['Cormorant-Italic.ttf', 'italic']], Lora: [['Lora-Italic.ttf', 'italic']],
  'Instrument Serif': [['InstrumentSerif-Regular.ttf', 'normal'], ['InstrumentSerif-Italic.ttf', 'italic']],
  'Roboto Condensed': [['RobotoCondensed.ttf', 'normal']], 'Space Grotesk': [['SpaceGrotesk.ttf', 'normal']],
};
const loaded = new Set<string>();
export const ensureFont = (family: string) => {
  if (loaded.has(family) || !FILES[family]) return;
  loaded.add(family);
  for (const [file, style] of FILES[family]) {
    loadFont({family, url: staticFile(`fonts/${file}`), weight: '100 900', style});
  }
};

// Motion grammar (frames at 30 fps), measured on the samples (docs/STYLE_STUDY):
// s42 poster entrance 7 f, s35 ticket unfold ~16 f, s33 prop 9 f@25 = ~11 f, s26 pill 6-8 f@25.
export const SPRING = {damping: 14, mass: 0.7, stiffness: 140};
export const SPRING_SOFT = {damping: 20, mass: 0.9, stiffness: 90};
