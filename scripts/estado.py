#!/usr/bin/env python3
"""Estado da edição e pontos de aprovação (P0.1). Um arquivo por run: <run>/estado.json.

Formato:
  {"esquema":1, "empresa":"<slug>", "video":"<AAAA-MM-DD-slug>", "fase":"briefing|cortes|amostra|completo|entregue",
   "modo_acesso":"sincronizada|espelho-rclone|espelho-composio|misto|somente-direcao", "versao":"v01",
   "aprovacoes":[{"fase","em","por","nome","arquivo","sha256","sem_gate"}], "entregas":[{"versao","arquivo","sha256","em"}],
   "jev_chamadas":0, "criado":"…", "atualizado":"…"}
Caminhos dentro do estado são sempre relativos ao run, porque ele sobe para 3-projeto/ e é lido em outra máquina.

Uso (o run vem de --run, da variável EDICAO_VIDEO_RUN ou da pasta atual):
  estado.py --run RUN --criar --empresa SLUG --video ID [--modo sincronizada] [--versao v01]
  estado.py --run RUN --mostrar
  estado.py --run RUN --fase cortes
  estado.py --run RUN --aprovar amostra --por cliente|dono [--nome "Quem aprovou"] [--arquivo amostra/amostra.mp4]
  estado.py --run RUN --aprovar completo --por cliente|dono [--nome "Quem"] [--arquivo final.mp4] [--pasta-empresa PASTA]
  estado.py --run RUN --aprovar amostra --por dono --sem-gate      (pula a conferência; só o dono; fica registrado)
  estado.py --run RUN --checar amostra                              (código 0 se aprovada, 1 com o comando que falta)

Sem --arquivo, a aprovação da amostra usa amostra/amostra.mp4 do run (saída do amostra.py) e a do completo, final.mp4.
A aprovação guarda o SHA-256 do arquivo: se ele mudar depois, a aprovação deixa de valer e a conferência avisa.
Na pasta da empresa (receita RUN/edicao.json do amostra.py, ou --pasta-empresa), a aprovação também vai para o registro: a linha
da versão entregue com esse arquivo no versoes.md ganha "Quem viu" e o veredito "aprovada"; o MAPA do vídeo ganha o
próximo passo; no completo, versao_aprovada, aprovado_por e status aprovado, e a linha do 05-videos/MAPA.md vai para
"Publicados" como "aprovado vNN em AAAA-MM-DD". Sem a pasta, só o estado.json do run muda (e o comando avisa).

Para outros scripts (import protegido: se este arquivo não existir, só avise):
  from estado import checar, exigir_aprovacao, contar_jev
  ok, motivo = checar(run, 'amostra')
  exigir_aprovacao(run, 'amostra', 'gerar_imagens.py')   # sai com código 1 e cita o comando, se faltar
"""
import argparse, datetime, hashlib, json, os, sys
from pathlib import Path

FASES = ['briefing', 'cortes', 'amostra', 'completo', 'entregue']
FASES_APROVACAO = ['amostra', 'completo']
MODOS = ['sincronizada', 'espelho-rclone', 'espelho-composio', 'misto', 'somente-direcao']
POR = ['cliente', 'dono']
ARQUIVO_PADRAO = {'amostra': 'amostra/amostra.mp4', 'completo': 'final.mp4'}
NOME = 'estado.json'


def agora():
    return os.environ.get('EDICAO_VIDEO_AGORA') or datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def sha256(caminho, bloco=1 << 20):
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for parte in iter(lambda: f.read(bloco), b''):
            h.update(parte)
    return h.hexdigest()


def caminho_estado(run):
    return Path(run) / NOME


def carregar(run):
    p = caminho_estado(run)
    if not p.exists():
        raise FileNotFoundError(f'sem {NOME} em {run}: rode "projeto.py trazer" ou "estado.py --criar"')
    return json.loads(p.read_text(encoding='utf-8'))


def salvar(run, est):
    est['atualizado'] = agora()
    p = caminho_estado(run)
    tmp = p.with_name('.' + p.name + '.parcial')
    tmp.write_text(json.dumps(est, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, p)
    return est


def criar(run, empresa, video, modo='sincronizada', versao='v01', fase='briefing'):
    if modo not in MODOS:
        raise ValueError(f'modo de acesso inválido: {modo} (use {", ".join(MODOS)})')
    if fase not in FASES:
        raise ValueError(f'fase inválida: {fase}')
    Path(run).mkdir(parents=True, exist_ok=True)
    if caminho_estado(run).exists():
        est = carregar(run)
        est.update({'empresa': empresa, 'video': video, 'modo_acesso': modo})
        return salvar(run, est)
    t = agora()
    return salvar(run, {'esquema': 1, 'empresa': empresa, 'video': video, 'fase': fase, 'modo_acesso': modo,
                        'versao': versao, 'aprovacoes': [], 'entregas': [], 'jev_chamadas': 0, 'criado': t})


def mudar_fase(run, fase):
    if fase not in FASES:
        raise ValueError(f'fase inválida: {fase} (use {", ".join(FASES)})')
    est = carregar(run)
    est['fase'] = fase
    return salvar(run, est)


def _relativo(run, arquivo):
    a = Path(arquivo)
    if not a.is_absolute():
        a = Path(run) / a
    try:
        return a.resolve().relative_to(Path(run).resolve()).as_posix(), a
    except ValueError:
        return a.name, a      # fora do run: guarda só o nome (o estado vai para a pasta do cliente)


def _dentro_do_run(run, caminho):
    try:
        Path(caminho).resolve().relative_to(Path(run).resolve())
        return True
    except ValueError:
        return False


def aprovar(run, fase, por, nome='', arquivo=None, sem_gate=False):
    if fase not in FASES_APROVACAO:
        raise ValueError(f'só se aprova {", ".join(FASES_APROVACAO)}; recebido: {fase}')
    if por not in POR:
        raise ValueError(f'--por deve ser {" ou ".join(POR)}')
    if sem_gate and por != 'dono':
        raise ValueError('--sem-gate só vale com --por dono')
    est = carregar(run)
    reg = {'fase': fase, 'em': agora(), 'por': por, 'nome': nome, 'arquivo': None, 'sha256': None, 'sem_gate': sem_gate}
    if not sem_gate:
        arquivo = arquivo or ARQUIVO_PADRAO.get(fase)
        if not arquivo:
            raise ValueError(f'diga qual arquivo foi aprovado: --arquivo (fase {fase})')
        rel, abs_ = _relativo(run, arquivo)
        if not abs_.is_file():
            raise ValueError(f'arquivo aprovado não existe: {arquivo}')
        reg['arquivo'], reg['sha256'] = rel, sha256(abs_)
        if not _dentro_do_run(run, abs_):
            reg['caminho_local'] = str(abs_.resolve())    # fora do run: para conferir depois (sobe como @FORA@)
    est['aprovacoes'].append(reg)
    if FASES.index(est['fase']) < FASES.index(fase):
        est['fase'] = fase
    return salvar(run, est)


def aprovacao(run, fase):
    """A última aprovação registrada da fase, ou None."""
    try:
        est = carregar(run)
    except FileNotFoundError:
        return None
    regs = [a for a in est.get('aprovacoes', []) if a.get('fase') == fase]
    return regs[-1] if regs else None


def checar(run, fase='amostra'):
    """(ok, motivo). Confere também se o arquivo aprovado não mudou depois da aprovação."""
    if not caminho_estado(run).exists():
        return False, f'sem {NOME} no run {run}'
    a = aprovacao(run, fase)
    comando = f'python3 scripts/estado.py --run "{run}" --aprovar {fase} --por cliente|dono'
    if not a:
        return False, f'a {fase} ainda não foi aprovada. Mostre a {fase} e registre: {comando}'
    if a.get('sem_gate'):
        return True, f'{fase} liberada sem conferência pelo dono em {a["em"]}'
    alvo = Path(a['caminho_local']) if a.get('caminho_local') else Path(run) / (a.get('arquivo') or '')
    if not a.get('arquivo') or not alvo.is_file():
        return False, f'o arquivo aprovado sumiu ({a["arquivo"]}). Refaça a {fase}, mostre e registre: {comando}'
    if sha256(alvo) != a['sha256']:
        return False, f'a {fase} mudou depois da aprovação ({a["arquivo"]}). Mostre de novo e registre: {comando}'
    return True, f'{fase} aprovada por {a["por"]}{(" (" + a["nome"] + ")") if a.get("nome") else ""} em {a["em"]}'


def exigir_aprovacao(run, fase='amostra', quem=''):
    ok, motivo = checar(run, fase)
    if not ok:
        print(f'{quem + ": " if quem else ""}recusado: {motivo}', file=sys.stderr)
        sys.exit(1)
    return motivo


def contar_jev(run, n=1):
    est = carregar(run)
    est['jev_chamadas'] = int(est.get('jev_chamadas', 0)) + n
    return salvar(run, est)


def registrar_entrega(run, versao, arquivo, sha, fase=None):
    est = carregar(run)
    est.setdefault('entregas', []).append({'versao': versao, 'arquivo': arquivo, 'sha256': sha, 'em': agora()})
    est['versao'] = versao
    if fase == 'completo':
        est['fase'] = 'entregue'
    elif fase and FASES.index(est['fase']) < FASES.index(fase):
        est['fase'] = fase
    return salvar(run, est)


def _pasta_do_video(run, empresa=None):
    """(empresa, pasta do vídeo) pela receita do run (edicao.json) ou por --empresa com o vídeo do estado.json."""
    import projeto as PJ
    est = carregar(run)
    emp = None
    rec = Path(run) / 'edicao.json'
    if not empresa and rec.is_file():
        try:
            r = json.loads(rec.read_text(encoding='utf-8'))
            e = r.get('empresa')
            if e:
                emp = Path(e) if Path(e).is_absolute() else Path(run) / e
                video = r.get('video') or est.get('video')
        except ValueError:
            emp = None
    if empresa:
        emp, video = Path(empresa).expanduser(), est.get('video')
    if not emp or not (emp / 'empresa.json').is_file() or not video:
        return None, None
    try:
        return emp, PJ.localizar_video(emp, video)
    except PJ.Erro:
        return None, None


def registrar_na_pasta(run, fase, por, nome='', empresa=None):
    """Leva a aprovação ao versoes.md e aos MAPAs (veja o cabeçalho). Devolve a frase do que mudou."""
    import projeto as PJ, frontmatter as fm
    emp, vdir = _pasta_do_video(run, empresa)
    if not vdir:
        return ('aprovação registrada só no run: não achei a pasta do vídeo (rode o amostra.py com --empresa e --video, ou '
                'passe --pasta-empresa); atualize o versoes.md à mão')
    est, ap = carregar(run), aprovacao(run, fase)
    ents = [e for e in est.get('entregas') or [] if e.get('sha256') == (ap or {}).get('sha256')] if ap else []
    if not ents:
        return (f'aprovação registrada no run, mas este arquivo não foi entregue em 4-entregas/ (nenhuma entrega com o mesmo '
                f'SHA-256): entregue antes ou marque o versoes.md à mão')
    ent = ents[-1]
    versao, quem = ent['versao'], nome or por
    vm = vdir / 'versoes.md'
    if vm.is_file(): PJ.marcar_versao(vm, versao, quem=quem, veredito='aprovada')
    entregue_como = 'completo' if '-completo-' in str(ent.get('arquivo') or '') else 'amostra'
    if entregue_como == 'completo':
        fm.atualizar_arquivo(vdir / 'MAPA.md', status='aprovado', versao_aprovada=versao, aprovado_por=quem, atualizado=PJ.hoje())
        PJ.proximo_passo(vdir, f'publicar a {versao} (aprovada por {quem} em {PJ.hoje()}).')
        PJ.secao_mapa_videos(emp, vdir, 'Publicados', f'aprovado {versao} em {PJ.hoje()}')
    else:
        fm.atualizar_arquivo(vdir / 'MAPA.md', atualizado=PJ.hoje())
        PJ.proximo_passo(vdir, f'render completo (passo 7); a amostra {versao} foi aprovada por {quem} em {PJ.hoje()}.')
        PJ.secao_mapa_videos(emp, vdir, 'Em andamento', f'amostra {versao} aprovada · render completo')
    # o 3-projeto/ da pasta leva o estado.json com a aprovação (a prova do chat novo lê a pasta, não o cache)
    PJ.subir_leves(run, vdir / '3-projeto', empresa=emp, video=vdir)
    frase = f'versoes.md: {versao} aprovada por {quem}; MAPA do vídeo, 05-videos/MAPA.md e 3-projeto/estado.json atualizados'
    if PJ.indice(emp):   # espelho do Composio: a aprovação vai ao Drive agora
        try:
            enviados, avisos = PJ.enviar_composio(emp)
            frase += f'; enviado ao Drive: {len(enviados)} arquivos, conferidos' + ''.join(f'\nAVISO: {x}' for x in avisos)
        except PJ.Erro as e:
            frase += f'\nAVISO: a aprovação ficou só no espelho ({e}); rode projeto.py enviar --empresa "{emp}"'
    return frase


def main(argv=None):
    ap = argparse.ArgumentParser(description='Estado da edição e pontos de aprovação (estado.json do run).')
    ap.add_argument('--run', default=os.environ.get('EDICAO_VIDEO_RUN') or '.')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--criar', action='store_true')
    g.add_argument('--mostrar', action='store_true')
    g.add_argument('--fase', choices=FASES)
    g.add_argument('--aprovar', choices=FASES_APROVACAO, metavar='FASE')
    g.add_argument('--checar', choices=FASES_APROVACAO, metavar='FASE')
    ap.add_argument('--empresa')
    ap.add_argument('--video')
    ap.add_argument('--modo', choices=MODOS, default='sincronizada')
    ap.add_argument('--versao', default='v01')
    ap.add_argument('--por', choices=POR)
    ap.add_argument('--nome', default='')
    ap.add_argument('--arquivo')
    ap.add_argument('--sem-gate', action='store_true')
    ap.add_argument('--pasta-empresa', dest='empresa_pasta', help='pasta da empresa (quando o run não tem edicao.json): leva a aprovação ao versoes.md')
    a = ap.parse_args(argv)
    try:
        if a.criar:
            if not (a.empresa and a.video):
                ap.error('--criar precisa de --empresa e --video')
            est = criar(a.run, a.empresa, a.video, a.modo, a.versao)
        elif a.fase:
            est = mudar_fase(a.run, a.fase)
        elif a.aprovar:
            if not a.por:
                ap.error('--aprovar precisa de --por cliente|dono')
            est = aprovar(a.run, a.aprovar, a.por, a.nome, a.arquivo, a.sem_gate)
            print(f'aprovado: {a.aprovar} por {a.por}{" (sem conferência, registrado)" if a.sem_gate else ""}')
            if not a.sem_gate:
                try:
                    print(registrar_na_pasta(a.run, a.aprovar, a.por, a.nome, a.empresa_pasta))
                except Exception as e:   # o registro na pasta nunca desfaz a aprovação do run
                    print(f'aviso: aprovação registrada no run, mas o versoes.md não foi atualizado ({e})', file=sys.stderr)
        elif a.checar:
            ok, motivo = checar(a.run, a.checar)
            print(('OK: ' if ok else 'FALTA: ') + motivo)
            return 0 if ok else 1
        else:
            est = carregar(a.run)
        print(json.dumps(est, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError) as e:
        print(f'erro: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
