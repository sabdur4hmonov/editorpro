"""Capability detection only; no install and no GPU smoke job. Runtime CPU fallback."""
from __future__ import annotations
import argparse, json
from functools import lru_cache
import common as C
@lru_cache(maxsize=1)
def cuda_count():
    try:
        import ctranslate2
        return int(ctranslate2.get_cuda_device_count())
    except (ImportError,RuntimeError,OSError): return 0
def encoder(style,requested=None):
    mode=style.get('hardware',{}).get('encode',style['video'].get('use_nvenc',False))
    if requested is not None: mode=requested
    if mode not in (True,False,'auto','cpu','nvenc'): raise C.MontajError('hardware.encode: auto | cpu | nvenc')
    if mode in (False,'cpu'): return False
    return cuda_count()>0 and C.has_encoder('h264_nvenc')
def whisper_device(wcfg):
    device=str(wcfg.get('device','auto')).lower()
    if device not in ('cpu','cuda','auto'): raise C.MontajError('whisper.device: auto | cpu | cuda')
    if device=='auto': device='cuda' if cuda_count()>0 else 'cpu'
    compute=str(wcfg.get('compute_type','auto'))
    if compute=='auto': compute='float16' if device=='cuda' else 'int8'
    return device,compute
def onnx_providers(mode='auto'):
    if mode not in ('auto','cpu','cuda'): raise C.MontajError('hardware.onnx: auto | cpu | cuda')
    if mode=='cpu' or cuda_count()==0: return ['CPUExecutionProvider']
    try:
        import onnxruntime as ort
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            if hasattr(ort,'preload_dlls'):
                try: ort.preload_dlls()
                except (RuntimeError,OSError) as error: C.warn(f'CUDA DLL preload failed; session will try CPU fallback: {error}')
            return ['CUDAExecutionProvider','CPUExecutionProvider']
    except ImportError: pass
    return ['CPUExecutionProvider']
def opencv_backend(cv2,mode='auto'):
    if mode not in ('auto','cpu','cuda'): raise C.MontajError('hardware.onnx: auto | cpu | cuda')
    if mode!='cpu' and cuda_count()>0:
        try:
            if cv2.dnn.DNN_TARGET_CUDA in cv2.dnn.getAvailableTargets(cv2.dnn.DNN_BACKEND_CUDA):
                return cv2.dnn.DNN_BACKEND_CUDA,cv2.dnn.DNN_TARGET_CUDA
        except (AttributeError,cv2.error): pass
    return cv2.dnn.DNN_BACKEND_OPENCV,cv2.dnn.DNN_TARGET_CPU
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--style'); a=ap.parse_args()
    style=C.load_style(a.style); device,compute=whisper_device(style['whisper'])
    C.info(json.dumps({'cuda_devices':cuda_count(),'nvenc_selected':encoder(style),'whisper_device':device,
                       'whisper_compute':compute,'onnx_providers':onnx_providers(style.get('hardware',{}).get('onnx','auto')),
                       'gpu_tested':False},indent=2))
if __name__=='__main__': C.run_main(main)
