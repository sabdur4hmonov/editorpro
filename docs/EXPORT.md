# Resolve va Premiere uchun montaj eksporti

Paket: `timeline.xml` (FCP 7 xmeml v5), `source_cuts.xml`, `manifest.json`,
`captions.srt`, `graphics/*.mov` (ProRes 4444, straight alpha), `speech.wav`,
`sfx.wav`, `music.wav`, `base.mp4`, `audio_cues.md/json` va `validation.json`.
Musiqa berilmagan bo'lsa music stem jim; yangi musiqa o'ylab topilmaydi.

## Nimalar tekshirildi

- [Apple legacy XML Elements Catalog](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/FinalCutPro_XML/Elements/Elements.html):
  xmeml, sequence/rate, track/clipitem, in/out/start/end, file/pathurl,
  timecode/frame/displayformat, sourcetrack, samplecharacteristics va straight alpha maydonlari.
- [Adobe rasmiy qo'llanmasi](https://helpx.adobe.com/archive/en/premiere-pro/cc/2015/premiere_pro_reference.pdf):
  Premiere FCP 7 va undan oldingi XML loyihalarini import qiladi. Bu import manbasi eski;
  o'rnatilgan hozirgi Premiere'da GUI sinovi qilinmadi.
- [Adobe hozirgi XML hujjati](https://helpx.adobe.com/premiere/desktop/organize-media/import-files/migrate-from-final-cut-pro-x.html):
  yangi `.fcpxml` bevosita import qilinmaydi. Shu sabab bu eksport FCP 7 `.xml` ishlatadi,
  Xto7 kabi pullik konvertor talab qilmaydi.
- [Adobe SRT formatlari](https://helpx.adobe.com/premiere/desktop/add-text-images/insert-captions/supported-file-formats-for-captions.html):
  SRT import formati. [ProRes ko'magi](https://helpx.adobe.com/uk/premiere/desktop/render-and-export/render-sequences-for-playback/smart-rendering-supported-formats.html)
  QuickTime ProRes 4444 ni sanaydi; alpha ko'rinishi GUI'da hali tekshirilmagan.
- [Resolve 20 Colorist Guide](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Colorist-Guide.pdf):
  XML timeline importi va manba kliplarni avtomatik olish tasvirlangan. Katta PDF to'liq
  ochilmadi; rasmiy qidiruvdagi tegishli bo'lak tekshirildi.
- [Resolve 20 Windows kodeklar jadvali, 7-bet](https://documents.blackmagicdesign.com/SupportNotes/DaVinci_Resolve_20_Supported_Codec_List.pdf):
  ProRes MOV decode va WAV PCM mavjud. Encode/Studio cheklovini import imkoniyati bilan aralashtirma.
  Resolve SRT importining hozirgi aniq menyusi ushbu sessiyada rasmiy hujjatdan tasdiqlanmadi.

FCPXML/OTIO/AAF/EDL uchun moslik taxmin qilinmaydi va bu sprintda eksport qilinmaydi.
Native XML, SRT, MOV va WAV yo'li uchun tashqi pullik plagin qo'shilmadi.
**GUI import UNVERIFIED**: XML'ni parse qilish editorni ochib import qilish o'rnini bosmaydi.

## Paket yaratish (matn tasdig'i HOLAT.md da bo'lishi shart)

```powershell
.venv\Scripts\python.exe scripts\editor_export.py export temp\video\cut.mp4 --source input\video.mp4 --cuts temp\video\cuts.json --subs temp\video\subs.srt --words temp\video\cut.words.json --elements temp\video\elements.json --style temp\video\style.json --out-dir temp\video\editor --approved
.venv\Scripts\python.exe scripts\editor_export.py validate temp\video\editor
```

Bu buyruqlar skriptning haqiqiy argparse/kodidan tekshirildi. Eksport og'ir ishlar navbatini oladi.
Sequence **butun fps**, non-drop timecode, speed=1. Source average FPS farq qilsa
`source_conformed.mp4` ishchi nusxa yaratiladi: [FFmpeg fps](https://ffmpeg.org/ffmpeg-filters.html#fps)
`round=near` bilan duplicate/drop qilib CFR beradi; source seconds saqlanadi, vaqt frame gridga
yaxlitlanadi (bir framegacha). Originalga tegilmaydi. Sintetik 24->30 va real doktor_1 bilan tekshiriladi;
manifest original FPS/path, working path va conform usulini yozadi. Source timeline shu nusxaga qaraydi.
29.97 sequence/drop-frame/tezlashtirish moslashtirgichi tekshirilmagan; aniq xato beradi.
Embedded source timecode bo'lmasa manifest `file-relative 00:00:00:00` deb yozadi.
source_out va record_out oxirgi kadrdan keyingi chegara, inclusive emas.

## Premiere'da

1. `File > Import` orqali `timeline.xml` ni tanlang (rasmiy XML workflow; sizdagi versiya GUI'si tekshirilmagan).
2. Media offline bo'lsa paket papkasi va original `input` manbasiga relink qiling.
3. `captions.srt` ni import qilib caption trackga qo'ying. Matn tahrirlanadi;
   word animation SRT formatida saqlanmaydi.
4. V1 base, yuqori video tracklar alpha grafika; audio tracklar speech/sfx/music.
   Base ichidagi original ovozni qayta yoqmang: speech stem alohida bor.
   Uch stereo stem XMLda oltita kanal tracki bo'lib keladi; L/Rni birga boshqaring.
5. Alpha noto'g'ri ko'rinsa `Interpret Footage` orqali straight alpha ni tekshiring
   (bu aniq GUI sozlamasi hozirgi versiyada UNVERIFIED).
6. Kesishlarni o'zgartirmoqchi bo'lsangiz `source_cuts.xml` ni alohida sequence sifatida import qiling.

## Resolve'da

1. Yangi loyiha; `File > Import > Timeline` orqali `timeline.xml` (menyu yo'li versiyangizda UNVERIFIED).
2. Import bilan media olishni yoqing; zarur bo'lsa paket va original inputga relink qiling.
3. `captions.srt` ni Media Poolga import, keyin subtitle trackga joylang
   (hozirgi GUI va SRT menyusi UNVERIFIED, sizda tekshirish kerak).
4. Grafika clip alpha'si straight, audio speech/sfx/music alohida ekanini tekshiring.
5. Original kesishlar uchun ikkinchi `source_cuts.xml` timeline ishlatiladi.

## Amaliy chegaralar

- Asosiy timeline base'da zoom, rang, stage/split b-roll va fon effektlari rasterlangan.
  Original-source timeline ularni qayta yaratmaydi; framingni qo'lda moslash kerak.
- Har bir mustaqil grafika o'z MOV'i va timeline in/out bilan keladi.
  Odam orqasidagi grafika mustaqil alpha sifatida chiqarilmaydi: eksport aniq to'xtaydi.
- Captionlar SRT; mavjud word motion editorning caption tizimiga tarjima qilinmaydi.
- Source-CFR nusxa eksport uchun qayta kodlanadi (CRF16); original master saqlanadi.
  VFR frame'larini asl indeks bo'yicha ko'rsatish o'rniga source seconds va CFR grid ishlatiladi.
- Stemlar nutq me'yori, haqiqiy sidechain va umumiy pasaytirishdan keyin, final limiterdan oldin.
  Ularni qo'shish delivery AAC bilan bitma-bit teng emas; limiter/encode farqi bor.
- Paketning XML, SRT, MOV kodeki/alpha/duration va uch stem duration'i qayta parse qilinadi.
  Testda haqiqiy MOV RGBA qilib dekodlanib, ochiq/yopiq alpha ham tekshiriladi.
- Media ko'chirilsa file URL'lar eskiradi: relink zarur. FPS mos bo'lsa original paketga nusxalanmaydi;
  mos bo'lmasa vaqtni saqlovchi CFR working copy paket ichida yaratiladi.
