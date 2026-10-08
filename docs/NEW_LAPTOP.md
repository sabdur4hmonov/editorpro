# Yangi Windows laptopga ko'chirish

2026-10-08: hozirgi kompyuterda NVIDIA yo'q. Python 3.11.9, CPU/int8/CPUExecutionProvider
tekshirildi. GPU ishga tushirish, tezlik va drayver/DLL mosligi **SINOVDAN O'TMAGAN**.
Bu yo'riqnoma hozir hech narsa o'rnatmaydi; har o'rnatish/yuklash/o'chirishni foydalanuvchi
alohida tasdiqlaydi. Agent .env'ni ochmaydi.

## 1. Nimalar ko'chadi

Ikkala agent/watcher idle bo'lsin. `handoff.py show`, git branch/logni tekshir; faqat `montaj-v3`.
Loyiha papkasini `.git` bilan Explorer orqali nusxala. `.venv` boshqa yo'l/kompyuterga portable emas,
yangi muhit alohida yaratiladi; eski kompyuterdagi muhit o'chirilmaydi.

| Narsa | Ko'chirish |
|---|---|
| scripts, docs, style/fonts, brands, .agents/skills, .claude/skills | Loyiha bilan birga |
| assets | Hammasi: sfx + litsenziya, models + credit/hash, icons, emoji zip, HTML |
| input, samples, output | Gitda yo'q; foydalanuvchi Explorer orqali nusxalaydi, original o'zgarmaydi |
| temp/<video> | Davom etadigan joblar: cut, words, SRT, elements, style, HOLAT va barcha assetlar |
| temp/.motion_history, temp/sprint1 | Uslub tarixi va A/B dalili, gitda yo'q |
| HOLAT.md | Project state/tasdiqlar gitda yo'q; qo'lda loyiha ildiziga |
| .env | **Faqat foydalanuvchi qo'lda**, agent ochmaydi/chiqarmaydi/gitga kiritmaydi |
| HF cache | Butun hub: models--*/snapshots + blobs + refs, faqat snapshot emas |
| rembg cache | .rembg va mavjud .u2net; modellarning o'zini, `.venv` emas |

Hugging Face standart Windows manzili `%USERPROFILE%\.cache\huggingface\hub`.
HF_HOME/HF_HUB_CACHE mavjud bo'lsa haqiqiy manzil boshqacha:
`.venv\Scripts\python.exe -c "from huggingface_hub import constants; print(constants.HF_HUB_CACHE)"`.
Bu kalitlarni chiqarish emas, cache yo'lini ko'rsatish. [HF rasmiy cache qo'llanmasi](https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache).

Hozirgi rembg 2.0.85: `%USERPROFILE%\.rembg\models\<model>\`; eski `%USERPROFILE%\.u2net\`
ham qidiriladi. REMBG_HOME/U2NET_HOME o'rnatilgan bo'lsa mos papkani ko'chir.
Aniq algoritm `.venv/Lib/site-packages/rembg/sessions/base.py`da tekshirildi;
[rembg rasmiy loyiha](https://github.com/danielgatis/rembg). Yangi laptopdagi versiyani qayta tekshir.
Yangi model avtomatik yuklashga ruxsat bermang: avval cache to'liq ko'chganini tekshir.

## 2. Avval CPU muhitini qaytarish

Foydalanuvchi ruxsatidan keyin Python 3.11, Git, FFmpeg va Windows VC++ runtime o'rnatiladi.
Python 3.11.9 joriy loyihada tekshirilgan; yangi Python minor versiyasini taxminan almashtirmang.
Git/FFmpeg paket manager IDlarini bu yerda taxmin qilmaymiz: rasmiy download sahifalaridan
foydalanuvchi o'rnatadi: [Python Windows](https://www.python.org/downloads/windows/),
[Git Windows](https://git-scm.com/install/windows), [FFmpeg](https://ffmpeg.org/download.html),
[Microsoft VC++ runtime](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
FFmpeg/ffprobe PATHda bo'lsin. GPU uchun NVIDIA rasmiy drayver kerak.

Yangi loyiha ildizida, ruxsatdan keyin:

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\handoff.py show
.venv\Scripts\python.exe scripts\sync_skills.py --apply
.venv\Scripts\python.exe scripts\sync_skills.py --check
.venv\Scripts\python.exe scripts\hardware.py
.venv\Scripts\python.exe scripts\person_mask.py
.venv\Scripts\python.exe scripts\transcribe.py --model-info yuldashev222/whisper-small-uz-v1-ct2
.venv\Scripts\python.exe scripts\test_motion.py
.venv\Scripts\python.exe scripts\test_takes.py
.venv\Scripts\python.exe scripts\test_studio.py
.venv\Scripts\python.exe scripts\test_agent_setup.py
.venv\Scripts\python.exe scripts\selftest.py --no-whisper
```

Venv buyruqlari [Python rasmiy venv](https://docs.python.org/3/library/venv.html)dan;
pip `-r` va `check` [pip rasmiy hujjati](https://pip.pypa.io/en/stable/user_guide/) va
[pip check](https://pip.pypa.io/en/stable/cli/pip_check/)dan. Skript flaglari kod/--helpda tekshirildi.
O'rnatish yangi laptopda hali bajarilmagan. requirements.lock.txt tarixiy to'liq muhit dalili;
rembg asosiy requirements.txtda bor, lockda bo'lmasligi mumkin. Lockni yagona install ro'yxati demang.
CPU selftestdan keyin Whisper jonli tekshiruv: `selftest.py` (--no-whispersiz), cache mavjud bo'lsa;
model yuklash talabi chiqsa avval foydalanuvchidan so'ra.

## 3. NVIDIA — keyingi bosqich, bu kompyuterda bajarilmagan

Kod `hardware.encode: auto`, `hardware.onnx: auto`, whisper `device: auto`, `compute_type: auto`.
GPU mavjudligi va runtime mos bo'lsa NVENC, CUDA/float16, ONNX CUDA tanlanadi; init/inference/kodlash
xatosida ogohlantirib CPU qaytadi. Bu Python/Pillow grafik chizishni GPUga o'tkazmaydi.
Oddiy opencv-python wheel'da YuNet CPU qoladi; GPU OpenCV alohida CUDA build talab qiladi,
bu loyiha uni avtomatik o'rnatmaydi. [OpenCV DNN](https://docs.opencv.org/4.x/d6/d0f/group__dnn.html).

faster-whisper/CTranslate2 uchun CUDA 12 cuBLAS va cuDNN 9 kerak; Windowsda mos NVIDIA
runtime DLL papkalari PATHda bo'lsin. [faster-whisper rasmiy talablar](https://github.com/SYSTRAN/faster-whisper).
CUDA va cuDNNni NVIDIA rasmiy Windows installeridan o'rnatish: [CUDA](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/),
[cuDNN](https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html).
Aniq installer/driver versiyasi yangi GPU modeli aniqlanganda tekshiriladi — hozir **TASDIQLANMAGAN**.

ONNX Runtime 1.30 GPU default CUDA 13ga o'tgan; shu loyihaning CT2 CUDA12 talabi bilan ko'r-ko'rona
latest o'rnatmang. Rasmiy jadvaldagi CUDA12/cuDNN9 liniyasini tanlash uchun quyidagi versiya
oralig'i qo'llanadi (jadvaldan chiqarilgan loyiha tanlovi, yangi laptopda **SINOVDAN O'TMAGAN**):

```powershell
# Faqat foydalanuvchi ruxsatidan keyin; CPU/GPU ORTni bir muhitga aralashtirmang.
.venv\Scripts\python.exe -m pip uninstall onnxruntime
.venv\Scripts\python.exe -m pip install "onnxruntime-gpu[cuda,cudnn]>=1.21,<1.27"
.venv\Scripts\python.exe -c "import onnxruntime as ort; ort.preload_dlls(); print(ort.get_available_providers())"
.venv\Scripts\python.exe scripts\hardware.py
ffmpeg -hide_banner -h encoder=h264_nvenc
```

Extras/preload va CUDA versiya jadvali [ONNX CUDA rasmiy hujjati](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html),
uninstall sintaksisi [pip](https://pip.pypa.io/en/stable/cli/pip_uninstall/). ORT CUDA12 liniyasi 12.8+
talab qiladi; CTranslate2 va ORTni bir xil major DLLlar bilan tekshiring. Extras Whisperning barcha
cuBLAS DLLlarini albatta ta'minlaydi deb hisoblamang; Whisper talabi alohida.
CPU rembg metadata'si onnxruntime talab qilgani sabab GPUga almashtirgach pip check shu talabni
missing deb ko'rsatishi mumkin: paket mosligini alohida ko'ring, CPU ORTni qayta o'rnatib GPU
fayllarini ustidan bosmang. Bu migratsiya hal etilgunga qadar ONNX CPUda qolishi mumkin.

`hardware.py` capability xolos, GPU ishlaganining isboti emas. Yangi laptopda selftest,
cached-model transcribe va real compose renderni alohida bajaring, logda fallback bo'lmaganini
tekshiring. NVENC flaglari [NVIDIA FFmpeg qo'llanmasi](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/ffmpeg-with-nvidia-gpu/index.html)da.
GPU tekshiruvi tugamaguncha "GPU tayyor" deb belgilamang. Muammo bo'lsa per-video sozlamada
`hardware.encode: cpu`, `hardware.onnx: cpu`, whisper `device: cpu`, `compute_type: int8`.

## 4. Ko'chirgandan keyingi tekshiruv

Per-video elements/style ichida eski absolute disk yo'llari bo'lsa faqat o'z job nusxasida tuzating;
input/samples fayllarini tahrir qilmang. `.env` ishlashini foydalanuvchi xizmat orqali tekshiradi,
agent kalitni chiqarmaydi. Watcher ishlayotgan bo'lsa direct agent boshlashdan oldin yopiladi.
Ikkala agent source skillni o'qisin; nusxalar sync --checkda teng, FIFO heavy lock ishlasin.
Muvaffaqiyatli test natijasi, versiyalar va qilinmagan GPU sinovlarini HOLAT/AGENT_MEMORYga yozing.
