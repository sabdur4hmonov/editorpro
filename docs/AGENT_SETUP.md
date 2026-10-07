# Claude va Codex: bitta loyiha, bitta tajriba

Claude `CLAUDE.md` orqali, Codex bevosita `AGENTS.md` ni o'qiydi. Ikki turli videoda parallel
ishlash va foydalanuvchi yuboradigan promptlar: [PARALLEL.md](PARALLEL.md). CPU ishlari FIFO navbatda.

## Sessiya boshi

```powershell
.venv\Scripts\python.exe scripts\handoff.py show
.venv\Scripts\python.exe scripts\sync_skills.py --check
```

AGENT_MEMORY.md ni o'qi, faqat o'z videongni davom ettir/egala. Skill tekshiruvi 1-kod bersa
va boshqa agentning unfinished videosi bo'lmasa:

```powershell
.venv\Scripts\python.exe scripts\sync_skills.py --apply
```

Manba faqat docs/claude_skills/. Nusxalar .claude/skills/ va .agents/skills/.
Yangilash yangi paket o'rnatmaydi va boshqa fayllarni o'chirmaydi. Manba/nusxa o'zgarishini commit qil.
Claude: `/namuna input\video.mp4 NOM`. Codex: `$namuna input\video.mp4 NOM`.
Brendsiz bo'lsa NOM yozilmaydi. To'rtta skill ikkala agentga ham bir xil jarayonni beradi.

## Har montajdan keyin

Namuna taqqoslash, draft, avtomatik preflight, urg'u, yangi grafikalar, muqova va
matn navbati uchun [STUDIO.md](STUDIO.md) ni o'qing. Vositalar ikkala agent uchun bir xil CLI.

EDIT_QUALITY.md bo'yicha o'z review.md faylingni yoz. Parallel montajda tajribani faqat
o'z deferred_learning.md faylingga yoz. Ikkala video tugab, boshqa agent idle bo'lgach bitta agent
AGENT_MEMORY.md ga natija va keyingi tavsiyani qo'shadi.
Feedback/glossary ham shu yakuniy idle bosqichda yangilanadi va commit qilinadi.
Joriy video, foydalanuvchi javobi va keyingi buyruqni handoff.py set --video VIDEO --agent NOM
bilan temp/<video>/HOLAT.md ga yoz. Loyiha HOLAT.md faqat umumiy state uchun.

## Mahalliy MCP — montaj-project

`scripts/project_mcp.py` Python standart kutubxonasi bilan ishlaydi: internet, API kaliti,
yangi paket yoki pullik xizmat talab qilmaydi. Protokol: MCP stdio, 2025-11-25 va oldingi
2024-11-05 / 2025-03-26 / 2025-06-18 versiyalari; boshqa versiya kelganda 2025-11-25 taklif qilinadi.
Bu maxsus kichik adapter, to'liq MCP SDK emas.

Uchta tool:

- project_state — handoff.py show bilan bir xil holat.
- read_guide — rules, playbook, sample_style, quality, memory yoki setup hujjatini o'qish.
- skills_status — ikkala agent nusxalarining manba bilan mosligini tekshirish.

Render va fayl yozish mavjud CLI orqali bajariladi. MCP ixtiyoriy fayl yo'li yoki shell
buyrug'i qabul qilmaydi. HOLAT.md va jurnalga sir kiritilmaydi.

Claude loyiha sozlamasi `.mcp.json`, Codexniki `.codex/config.toml`. Ushbu kompyuterning
mutlaq yo'llari yozilgan; loyiha ko'chsa ikkalasida ham command/args/cwd yo'llarini yangila.
Keyingi sessiyada loyihani qayta och. Claude loyiha MCPsi uchun o'z ishonch tasdig'ini so'raydi;
MCP menyusida montaj-project ni tasdiqla. Codexda loyiha ishonchli bo'lishi kerak.
Ulanishning amaldagi holatini client MCP menyusi orqali tekshir; konfiguratsiya borligi
joriy ochiq sessiyada server allaqachon ishlayapti degani emas.

```powershell
codex mcp get montaj-project
claude mcp get montaj-project
.venv\Scripts\python.exe scripts\test_agent_setup.py
```

Rasmiy manbalar (2026-10-07 tekshirilgan):

- [Codex MCP konfiguratsiyasi](https://developers.openai.com/codex/mcp)
- [Claude loyiha MCP sozlamasi va tasdiq](https://code.claude.com/docs/en/mcp)
- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP versiya kelishuvi](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)

## Qo'shimcha montaj xizmatlari

Descript/Runway/Adobe kabi connectorlar hisob, ulanish, ba'zida kredit talab qiladi.
Ular bu lokal montaj dvigatelining zarur qismi emas. Hozir o'rnatilmagan; aniq ijodiy ehtiyoj,
narx va foydalanuvchi roziligi bo'lganda qo'shiladi. Remotion/HyperFrames uchun mavjud
docs/SKILLS_AUDIT.md va docs/REMOTION_PROMPT.md dan boshlang. CPU cheklovini hisobga oling.
