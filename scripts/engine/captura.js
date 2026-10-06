// Ponte de captura do render.mjs (injetada depois do V4.init; não altera o desenho, que continua puro em t).
// 1) Pré-carregamento determinístico dos quadros da câmera: o render.mjs calcula as chaves do quadro atual (need)
//    e dos 12 seguintes (ahead); as do quadro atual são esperadas (img.decode) antes de desenhar, as outras ficam pedidas.
//    Se a previsão errar, o desenho duplo antigo continua de rede de segurança (e é contado).
// 2) Caminho WebCodecs: o canvas vira VideoFrame e vai para o VideoEncoder H.264 por hardware; só o vídeo comprimido
//    (Annex B) sai do navegador, em lotes de cerca de 4 MB, por POST para o servidor local do render.mjs.
(function (V) {
  'use strict';
  const main = document.getElementById('c');
  const inflight = new Map();
  function want(key) {
    let p = inflight.get(key);
    if (!p) { p = V.loadFrames([key]).finally(() => inflight.delete(key)); inflight.set(key, p); }
    return p;
  }
  async function draw(t, audit, nudge, need, ahead) {
    const now = need.map(want);
    for (const k of ahead) want(k);
    if (now.length) await Promise.all(now);
    let miss = V.renderFrame(t, { audit, nudge }), dbl = 0;
    if (miss.length) { dbl = 1; await V.loadFrames(miss); miss = V.renderFrame(t, { audit, nudge }); }
    return dbl;
  }
  // caminho de reserva (o de antes): JPEG/PNG em base64 pelo protocolo do Playwright
  V.__img = async function (t, fmt, q, audit, nudge, need, ahead) {
    const dbl = await draw(t, audit, nudge, need, ahead);
    return { url: main.toDataURL(fmt === 'png' ? 'image/png' : 'image/jpeg', q), dbl };
  };

  // ---------- WebCodecs ----------
  const WC = { enc: null, chunks: [], keys: [], bytes: 0, fi: 0, seq: 0, sess: 0, port: 0, err: null, fp: false };
  // Impressão digital assíncrona de cada quadro: cópia reduzida (1/8) feita na GPU e lida sem travar o desenho
  // (createImageBitmap e VideoFrame.copyTo são assíncronos). Serve só para apontar candidatos a quadro repetido; a confirmação é exata, depois do render.
  const FP = { list: [], pend: [] };
  function fnv(u8) { const d = new Uint32Array(u8.buffer, 0, u8.byteLength >> 2); let h = 2166136261; for (let i = 0; i < d.length; i++) h = Math.imul(h ^ d[i], 16777619) >>> 0; return h; }
  function fingerprint(fi, src) {
    // redução 1/8 feita pelo createImageBitmap a partir de um clone do VideoFrame do encoder (sem desenhar de novo no canvas)
    const w = Math.max(2, Math.round(main.width / 8)), h = Math.max(2, Math.round(main.height / 8));
    FP.pend.push(createImageBitmap(src, { resizeWidth: w, resizeHeight: h, resizeQuality: 'low' }).then(bm => {
      const vf = new VideoFrame(bm, { timestamp: fi }), buf = new Uint8Array(vf.allocationSize());
      return vf.copyTo(buf).then(() => { FP.list[fi] = fnv(buf); }).finally(() => { vf.close(); bm.close(); });
    }).catch(() => { FP.list[fi] = -1 - fi; }).finally(() => src.close()));
  }
  V.__wcProbe = async function (cfg) {
    if (typeof VideoEncoder === 'undefined' || typeof VideoFrame === 'undefined') return { ok: false, why: 'navegador sem VideoEncoder' };
    try { const r = await VideoEncoder.isConfigSupported(cfg); return { ok: !!r.supported, why: r.supported ? '' : 'VideoEncoder.isConfigSupported recusou a configuração' }; }
    catch (e) { return { ok: false, why: String(e && e.message || e) }; }
  };
  V.__wcStart = function (cfg, port, sess, fp) {
    Object.assign(WC, { chunks: [], keys: [], bytes: 0, fi: 0, seq: 0, sess, port, err: null, fp: !!fp });
    FP.list = []; FP.pend = [];
    WC.enc = new VideoEncoder({
      output: ch => {
        const u = new Uint8Array(ch.byteLength); ch.copyTo(u);
        if (ch.type === 'key') WC.keys.push(Math.round(ch.timestamp * 30 / 1e6) + ':' + WC.bytes);
        WC.chunks.push(u); WC.bytes += u.byteLength;
      },
      error: e => { WC.err = String(e && e.message || e); }
    });
    WC.enc.configure(cfg);
  };
  async function post(final) {
    if (final) await WC.enc.flush();
    if (!WC.bytes) return;
    const body = new Blob(WC.chunks), k = WC.keys.join(',');
    WC.chunks = []; WC.keys = []; WC.bytes = 0;
    const r = await fetch(`http://127.0.0.1:${WC.port}/?s=${WC.sess}&n=${WC.seq++}&k=${k}`, { method: 'POST', body });
    if (!r.ok) throw new Error('servidor local recusou o lote: ' + r.status);
  }
  V.__wcFrame = async function (t, audit, nudge, need, ahead) {
    if (WC.err) throw new Error('VideoEncoder: ' + WC.err);
    const dbl = await draw(t, audit, nudge, need, ahead);
    const vf = new VideoFrame(main, { timestamp: Math.round(WC.fi * 1e6 / 30), duration: Math.round(1e6 / 30) });
    const src = WC.fp ? vf.clone() : null;
    WC.enc.encode(vf, { keyFrame: WC.fi % 60 === 0 }); vf.close();
    if (WC.fp) { fingerprint(WC.fi, src); if (FP.pend.length > 6) await FP.pend.shift(); }
    WC.fi++;
    while (WC.enc.encodeQueueSize > 3 && !WC.err) await new Promise(r => { WC.enc.addEventListener('dequeue', r, { once: true }); setTimeout(r, 50); });
    if (WC.bytes > 4e6) await post(false);
    return dbl;
  };
  V.__wcEnd = async function () {
    await post(true);
    await Promise.all(FP.pend); FP.pend = [];
    WC.enc.close(); WC.enc = null;
    if (WC.err) throw new Error('VideoEncoder: ' + WC.err);
    return { frames: WC.fi, batches: WC.seq, fp: WC.fp ? Array.from({ length: WC.fi }, (_, i) => FP.list[i] ?? null) : null };
  };
  // Confirmação exata (depois do render, só para candidatos): desenha t e compara o quadro inteiro, como o JPEG de antes.
  let full = null;
  V.__exact = async function (t, nudge, need) {
    await draw(t, false, nudge, need, []);
    if (!full) { full = document.createElement('canvas'); full.width = main.width; full.height = main.height; full.x = full.getContext('2d', { willReadFrequently: true }); }
    full.x.clearRect(0, 0, full.width, full.height); full.x.drawImage(main, 0, 0);
    return fnv(new Uint8Array(full.x.getImageData(0, 0, full.width, full.height).data.buffer));
  };
})(window.V4);
