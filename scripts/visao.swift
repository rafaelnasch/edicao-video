// Helper Vision da skill (macOS): caixas de rosto ou de saliência por atenção, normalizadas com origem
// no canto superior esquerdo. Compilado sob demanda por proporcoes.py em ~/.cache/edicao-video/visao.
// Uso: visao rosto|saliencia img1.png [img2.png ...]  ->  JSON [{arquivo, w, h, caixas:[{x,y,w,h,c}]}]
import Vision
import AppKit

let args = Array(CommandLine.arguments.dropFirst())
let modo = args.first ?? "rosto"
var out: [[String: Any]] = []
for p in args.dropFirst() {
  guard let img = NSImage(contentsOfFile: p), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    out.append(["arquivo": p, "erro": "leitura"]); continue
  }
  let handler = VNImageRequestHandler(cgImage: cg, options: [:])
  var caixas: [[String: Double]] = []
  let conv: (CGRect, Double) -> [String: Double] = { b, c in ["x": Double(b.origin.x), "y": Double(1 - b.origin.y - b.height), "w": Double(b.width), "h": Double(b.height), "c": c] }
  if modo == "saliencia" {
    let req = VNGenerateAttentionBasedSaliencyImageRequest()
    try? handler.perform([req])
    for o in (req.results?.first?.salientObjects ?? []) { caixas.append(conv(o.boundingBox, Double(o.confidence))) }
  } else {
    let req = VNDetectFaceRectanglesRequest()
    try? handler.perform([req])
    for f in (req.results ?? []) { caixas.append(conv(f.boundingBox, Double(f.confidence))) }
  }
  out.append(["arquivo": p, "w": cg.width, "h": cg.height, "caixas": caixas])
}
print(String(data: try! JSONSerialization.data(withJSONObject: out, options: []), encoding: .utf8)!)
