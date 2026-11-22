#!/usr/bin/env python3
"""
bibliotecury: importa livros a partir de arquivos EPUB e PDF.

Para cada arquivo encontrado, cria livros/<nome-do-livro>.js com título, autor,
ano, gênero, páginas, capa e resumo (quando o arquivo traz essas informações),
deixa nota, lido e "O que eu achei" para você preencher, e coloca o livro
no fim da lista em livros.js.

Uso:
    python3 importar.py                  # lê a pasta leituras/
    python3 importar.py ~/Downloads      # lê outra pasta (ou um arquivo)
    python3 importar.py --vigiar         # fica de olho em leituras/ e importa o que chegar

Livros que já têm arquivo em livros/ são pulados, então pode rodar quantas vezes quiser.
"""
import hashlib
import html
import io
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import zipfile
import posixpath
from pathlib import Path
from xml.etree import ElementTree as ET

RAIZ = Path(__file__).resolve().parent
LIVROS = RAIZ / 'livros'
CAPAS = RAIZ / 'capas'
LISTA = RAIZ / 'livros.js'
PADRAO = RAIZ / 'leituras'

PALETA = ['#1F3FB0', '#D9472B', '#141414', '#2F6B4F', '#C98A1B', '#7A2E3A',
          '#3D6FB6', '#0B0964', '#300202', '#23BDA8', '#5B3A7A', '#8A5A2E']


# ---------- gêneros ----------
# O gênero que vem no arquivo (em qualquer língua) é trocado por um dos nomes de GENEROS em livros.js.
# A primeira regra que casar vence; por isso ficção científica vem antes de literatura.
REGRAS_GENERO = [
    ('Ficção científica', r'science.?fiction|sci.?fi|^sf$|ficção científica|ficcao cientifica|ciencia.?ficci|fantas'),
    ('Biografia', r'biogra|memoir|memória|autobiog'),
    ('Viagem', r'travel|viage|viaje|viagg'),
    ('História', r'histor'),
    ('Economia e negócios', r'econom|business|negócio|negocio|financ|management|investi'),
    ('Acadêmico', r'textbook|engineering|acadêm|academ|telecom'),
    ('Literatura', r'fiction|ficção|ficcion|romance|novel|literat|littérat|classic|clássic|fábula|fable|poe'),
]


def genero_canonico(bruto):
    t = (bruto or '').strip().lower()
    if not t:
        return ''
    for nome, regra in REGRAS_GENERO:
        if re.search(regra, t):
            return nome
    return ''


# ---------- utilidades ----------

def slug(texto):
    t = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    t = re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-').lower()
    return t[:60].strip('-') or 'livro'


def limpo(texto):
    """Texto de uma linha, sem HTML e sem crase invertida (que quebraria o .js)."""
    if not texto:
        return ''
    t = html.unescape(re.sub(r'<[^>]+>', ' ', str(texto)))
    return re.sub(r'\s+', ' ', t).replace('`', "'").strip()


def resumo_limpo(texto):
    """Descrição do livro em parágrafos, sem HTML."""
    if not texto:
        return ''
    t = re.sub(r'(?i)<\s*(br|/p|/div)\s*/?>', '\n\n', str(texto))
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t)).replace('`', "'")
    pars = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', t)]
    return '\n\n'.join(p for p in pars if p)


def nome_autor(texto):
    """'Kafka, Franz' ou 'Bradbury,Ray' vira 'Franz Kafka' / 'Ray Bradbury'."""
    t = limpo(texto)
    partes = [p.strip() for p in t.split(',')]
    if len(partes) == 2 and ' ' not in partes[0] and partes[1]:
        return f'{partes[1]} {partes[0]}'
    return t


def cor_letra(fundo):
    r, g, b = (int(fundo[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return '#141414' if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.6 else '#F1E9D6'


def salvar_capa(dados, nome):
    """Grava a capa em capas/<nome>.jpg (reduzida, se der). Devolve o caminho relativo."""
    if not dados:
        return ''
    CAPAS.mkdir(exist_ok=True)
    destino = CAPAS / f'{nome}.jpg'
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(dados)).convert('RGB')
        im.thumbnail((800, 1200))
        im.save(destino, 'JPEG', quality=85, optimize=True)
    except Exception:
        destino.write_bytes(dados)
    return f'capas/{destino.name}'


# ---------- EPUB ----------

def ler_epub(caminho):
    info = {}
    with zipfile.ZipFile(caminho) as z:
        cont = ET.fromstring(z.read('META-INF/container.xml'))
        opf_path = next(e.get('full-path') for e in cont.iter() if e.tag.endswith('rootfile'))
        opf = ET.fromstring(z.read(opf_path))
        base = posixpath.dirname(opf_path)

        def dc(nome):
            return [e.text.strip() for e in opf.iter() if e.tag.endswith('}' + nome) and e.text and e.text.strip()]

        info['titulo'] = limpo((dc('title') or [''])[0])
        info['autor'] = ', '.join(nome_autor(a) for a in dc('creator'))
        datas = dc('date')
        anos = [m.group(0) for d in datas for m in [re.search(r'\d{4}', d)] if m]
        info['ano'] = min(anos) if anos else ''
        info['genero'] = limpo((dc('subject') or [''])[0])
        info['resumo'] = resumo_limpo((dc('description') or [''])[0])

        manifest = {}
        for e in opf.iter():
            if e.tag.endswith('}item'):
                manifest[e.get('id')] = e
        # capa: <meta name="cover">, properties="cover-image" ou um item com "cover" no nome
        capa = None
        for e in opf.iter():
            if e.tag.endswith('}meta') and e.get('name') == 'cover' and e.get('content') in manifest:
                capa = manifest[e.get('content')]
        if capa is None:
            capa = next((e for e in manifest.values() if 'cover-image' in (e.get('properties') or '')), None)
        if capa is None:
            capa = next((e for e in manifest.values()
                         if (e.get('media-type') or '').startswith('image/')
                         and 'cover' in ((e.get('id') or '') + (e.get('href') or '')).lower()), None)
        if capa is not None:
            try:
                info['capa_dados'] = z.read(posixpath.normpath(posixpath.join(base, capa.get('href'))))
            except KeyError:
                pass

        # páginas: estimadas pelo número de palavras (~275 por página), se o texto não tiver DRM
        if 'META-INF/encryption.xml' not in z.namelist():
            palavras = 0
            for e in manifest.values():
                if 'html' in (e.get('media-type') or ''):
                    try:
                        txt = z.read(posixpath.normpath(posixpath.join(base, e.get('href')))).decode('utf-8', 'ignore')
                    except KeyError:
                        continue
                    palavras += len(re.sub(r'<[^>]+>', ' ', txt).split())
            if palavras > 2000:
                info['paginas'] = str(round(palavras / 275))
    return info


# ---------- PDF ----------

def ler_pdf(caminho):
    info = {}
    if shutil.which('pdfinfo'):
        saida = subprocess.run(['pdfinfo', str(caminho)], capture_output=True, text=True).stdout
        campos = dict(re.findall(r'^([^:\n]+):\s*(.*)$', saida, re.M))
        info['titulo'] = limpo(campos.get('Title', ''))
        info['autor'] = nome_autor(campos.get('Author', ''))
        info['paginas'] = campos.get('Pages', '').strip()
        info['ano'] = ''  # a data do PDF é a do arquivo, não a do livro
        info['genero'] = limpo(campos.get('Subject', ''))
    else:
        dados = Path(caminho).read_bytes()
        info['paginas'] = str(len(re.findall(rb'/Type\s*/Page[^s]', dados)) or '')
    if shutil.which('pdftoppm'):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['pdftoppm', '-jpeg', '-f', '1', '-l', '1', '-scale-to', '1000', '-singlefile',
                            str(caminho), str(Path(tmp) / 'capa')], capture_output=True)
            img = Path(tmp) / 'capa.jpg'
            if img.exists():
                info['capa_dados'] = img.read_bytes()
    return info


# ---------- gravação ----------

def nomes_na_lista():
    return re.findall(r'"([^"]+)"', LISTA.read_text(encoding='utf-8').split('LIVROS', 1)[1])


def adicionar_na_lista(nome):
    texto = LISTA.read_text(encoding='utf-8')
    fim = texto.rindex(']')
    antes = texto[:fim].rstrip()
    if not antes.endswith(('[', ',')):
        antes += ','
    LISTA.write_text(f'{antes}\n  "{nome}",\n{texto[fim:]}', encoding='utf-8')


def importar(caminho):
    ext = caminho.suffix.lower()
    try:
        info = ler_epub(caminho) if ext == '.epub' else ler_pdf(caminho)
    except Exception as e:
        print(f'  ✗ {caminho.name}: não consegui ler ({e})')
        return None  # tenta de novo na próxima volta (pode estar sendo copiado)

    if not info.get('titulo'):
        info['titulo'] = limpo(re.sub(r'[_]+', ' ', caminho.stem))
    nome = slug(info['titulo'])
    if (LIVROS / f'{nome}.js').exists() or nome in nomes_na_lista():
        print(f'  · {caminho.name}: já existe (livros/{nome}.js), pulei')
        return False

    bruto = info.get('genero', '')
    info['genero'] = genero_canonico(bruto)
    if bruto and not info['genero']:
        print(f'    gênero "{bruto}" não se encaixou em nenhum; preencha à mão')

    cor = PALETA[int(hashlib.md5(nome.encode()).hexdigest(), 16) % len(PALETA)]
    capa = salvar_capa(info.get('capa_dados'), nome)
    resumo = info.get('resumo') or 'Escreva aqui um resumo do livro.'

    js = f"""livro(`
titulo: {info['titulo']}
autor: {info.get('autor', '')}
ano: {info.get('ano', '')}
genero: {info.get('genero', '')}
paginas: {info.get('paginas', '')}
nota:
lido:
cor: {cor}
letra: {cor_letra(cor)}
capa: {capa}

## Resumo

{resumo}

## O que eu achei

Escreva aqui o que você achou deste livro.
`);
"""
    (LIVROS / f'{nome}.js').write_text(js, encoding='utf-8')
    adicionar_na_lista(nome)
    print(f'  ✓ {caminho.name} → livros/{nome}.js' + ('' if capa else ' (sem capa)'))
    return True


def arquivos(alvos):
    for alvo in alvos:
        alvo = Path(alvo).expanduser()
        if alvo.is_file():
            yield alvo
        elif alvo.is_dir():
            yield from sorted(p for p in alvo.rglob('*') if p.suffix.lower() in ('.epub', '.pdf'))
        else:
            print(f'Não encontrei: {alvo}')


def main():
    args = [a for a in sys.argv[1:] if a != '--vigiar']
    vigiar = '--vigiar' in sys.argv
    alvos = args or [PADRAO]
    PADRAO.mkdir(exist_ok=True)

    vistos = set()
    while True:
        novos = 0
        for arq in arquivos(alvos):
            if arq in vistos:
                continue
            ok = importar(arq)
            if ok is not None or not vigiar:
                vistos.add(arq)
            novos += bool(ok)
        if not vigiar:
            print(f'{novos} livro(s) importado(s).')
            return
        time.sleep(3)


if __name__ == '__main__':
    if '--vigiar' in sys.argv:
        print('De olho na pasta. Solte um EPUB ou PDF nela; Ctrl+C para parar.')
    try:
        main()
    except KeyboardInterrupt:
        pass
