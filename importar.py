#!/usr/bin/env python3
"""
bibliotecury: importa livros a partir de arquivos EPUB, PDF e do Kindle (KFX, AZW, AZW3, MOBI).
Os do Kindle precisam do Calibre instalado (calibre-ebook.com).

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
REGISTRO = PADRAO / '.importados'  # arquivos já importados (um nome por linha); não vão para o GitHub

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
    t = limpo(re.sub(r'\([^)]*\)', '', texto or ''))          # tira "(research Fellow)" e afins
    t = re.sub(r'\s+(and|e|&|y|et)\s+', ', ', t)                # "A and B" vira "A, B"
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


# ---------- Kindle (KFX, AZW, AZW3, MOBI) via Calibre ----------
# Formatos da Amazon são fechados; quem lê os dados deles é o "ebook-meta", que vem com o Calibre.
# Só lemos título, autor, data, gênero, sinopse e capa: nada de mexer em DRM.

KINDLE = ('.kfx', '.azw', '.azw3', '.azw8', '.mobi', '.prc')


def ebook_meta():
    for cmd in ('ebook-meta', '/opt/calibre/ebook-meta', '/usr/bin/ebook-meta'):
        if shutil.which(cmd):
            return [shutil.which(cmd)]
    if shutil.which('flatpak') and subprocess.run(['flatpak', 'info', 'com.calibre_ebook.calibre'],
                                                  capture_output=True).returncode == 0:
        return ['flatpak', 'run', '--command=ebook-meta', '--filesystem=host', 'com.calibre_ebook.calibre']
    return None


def titulo_do_arquivo(caminho):
    """"Can't Hurt Me_ Master Your Mind_B07H453KGH.kfx" -> "Can't Hurt Me: Master Your Mind"."""
    t = re.sub(r'[_ ]+B0[0-9A-Z]{8}$', '', caminho.stem)      # tira o código da Amazon (ASIN)
    t = re.sub(r'_\s', ': ', t, count=1).replace('_', ' ')
    return limpo(t)


def calibre_meta(cmd, caminho):
    """Lê os dados com o ebook-meta. Devolve {} se o arquivo não tiver nada legível (ex.: DRM)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        capa = Path(tmp) / 'capa.jpg'
        r = subprocess.run(cmd + [str(caminho), f'--get-cover={capa}'], capture_output=True, text=True, timeout=180)
        # saída no formato "Title               : Nome", com "Comments" podendo ocupar várias linhas
        campos, chave = {}, None
        for linha in r.stdout.splitlines():
            m = re.match(r'^([A-Za-z() ]+?)\s*:\s(.*)$', linha)
            if m:
                chave = m.group(1).strip(); campos[chave] = m.group(2).strip()
            elif chave == 'Comments':
                campos[chave] += '\n' + linha
        autores = [nome_autor(re.sub(r'\[.*?\]', '', a)) for a in campos.get('Author(s)', '').split('&') if a.strip()]
        if not autores or autores == ['Unknown']:
            return {}  # o Calibre só repetiu o nome do arquivo: não leu nada de verdade
        info = {
            'titulo': limpo(campos.get('Title', '')),
            'autor': ', '.join(autores),
            'genero': limpo(campos.get('Tags', '').split(',')[0]),
            'resumo': resumo_limpo(campos.get('Comments', '')),
        }
        m = re.search(r'\d{4}', campos.get('Published', ''))
        info['ano'] = m.group(0) if m and not m.group(0).startswith('01') else ''
        if capa.exists() and capa.stat().st_size:
            info['capa_dados'] = capa.read_bytes()
        return info


def baixar(url):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'bibliotecury-importar/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def open_library(titulo):
    """Procura o livro pelo título no catálogo público da Open Library."""
    import json
    import urllib.parse
    campos = 'title,author_name,first_publish_year,subject,cover_i,number_of_pages_median'
    doc = None
    # tenta o título inteiro e, se não achar, só a parte antes do subtítulo ("Can't Hurt Me: Master..." -> "Can't Hurt Me")
    for t in dict.fromkeys([titulo, titulo.split(':')[0].strip()]):
        url = 'https://openlibrary.org/search.json?' + urllib.parse.urlencode({'title': t, 'limit': 5, 'fields': campos})
        docs = json.loads(baixar(url)).get('docs', [])
        # pula "resumos" e similares que aparecem junto com o livro de verdade
        doc = next((d for d in docs if d.get('author_name')
                    and not re.search(r'summary|resumo|workbook|study guide', ' '.join(d['author_name']) + ' ' + d.get('title', ''), re.I)), None)
        if doc:
            break
    if not doc:
        return {}
    info = {
        'autor': ', '.join(nome_autor(a) for a in doc['author_name'][:2]),
        'ano': str(doc.get('first_publish_year') or ''),
        'paginas': str(doc.get('number_of_pages_median') or ''),
        'genero': next((g for g in map(genero_canonico, doc.get('subject', [])) if g), ''),
    }
    if doc.get('cover_i'):
        try:
            info['capa_dados'] = baixar(f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg")
        except Exception:
            pass
    return info


def ler_kindle(caminho):
    info = {}
    cmd = ebook_meta()
    if cmd:
        try:
            info = calibre_meta(cmd, caminho)
        except Exception:
            info = {}
    if not info:
        # arquivo com DRM (ou sem Calibre): usa o título do nome do arquivo e completa pela Open Library
        info = {'titulo': titulo_do_arquivo(caminho)}
        try:
            achado = open_library(info['titulo'])
        except Exception as e:
            achado = {}
            print(f'    não consegui consultar a Open Library ({e})')
        if achado:
            print('    arquivo com DRM: dados completados pela Open Library, confira')
        else:
            print('    arquivo com DRM e livro não achado na Open Library: só o título foi preenchido')
        info.update(achado)
    return info


# ---------- gravação ----------

def _lista_livros(texto):
    """Posição (início, fim) do conteúdo entre os colchetes de LIVROS = [ ... ] em livros.js."""
    ini = texto.index('[', texto.index('LIVROS'))
    return ini + 1, texto.index(']', ini)


def nomes_na_lista():
    texto = LISTA.read_text(encoding='utf-8')
    ini, fim = _lista_livros(texto)
    return re.findall(r'"([^"]+)"', texto[ini:fim])


def adicionar_na_lista(nome):
    texto = LISTA.read_text(encoding='utf-8')
    ini, fim = _lista_livros(texto)
    antes = texto[:fim].rstrip()
    if not antes.endswith(('[', ',')):
        antes += ','
    LISTA.write_text(f'{antes}\n  "{nome}",\n{texto[fim:]}', encoding='utf-8')


def parecido_com_existente(nome):
    """Acha um livro já cadastrado com o mesmo título, ex.: "1954-ray-bradbury-fahrenheit-451" ~ "fahrenheit-451"."""
    for f in LIVROS.glob('*.js'):
        if f.stem.startswith('_'):
            continue
        m = re.search(r'^titulo:\s*(.+)$', f.read_text(encoding='utf-8'), re.M)
        existente = slug(m.group(1)) if m else f.stem
        for e in {existente, f.stem}:
            if len(e) >= 6 and (f'-{e}-' in f'-{nome}-' or f'-{nome}-' in f'-{e}-'):
                return f.name
    return None


def registrados():
    try:
        return set(REGISTRO.read_text(encoding='utf-8').splitlines())
    except FileNotFoundError:
        return set()


def registrar(caminho):
    with REGISTRO.open('a', encoding='utf-8') as f:
        f.write(caminho.name + '\n')


def importar(caminho):
    if caminho.name in registrados():
        return False  # já importado antes (mesmo que você tenha renomeado ou apagado o .js)
    ext = caminho.suffix.lower()
    try:
        info = ler_epub(caminho) if ext == '.epub' else ler_kindle(caminho) if ext in KINDLE else ler_pdf(caminho)
    except RuntimeError as e:  # erro definitivo (ex.: falta o Calibre): não adianta tentar de novo
        print(f'  ✗ {caminho.name}: {e}')
        return False
    except Exception as e:
        print(f'  ✗ {caminho.name}: não consegui ler ({e})')
        return None  # tenta de novo na próxima volta (pode estar sendo copiado)

    if not info.get('titulo'):
        info['titulo'] = limpo(re.sub(r'[_]+', ' ', caminho.stem))
    nome = slug(info['titulo'])
    if (LIVROS / f'{nome}.js').exists() or nome in nomes_na_lista():
        print(f'  · {caminho.name}: já existe (livros/{nome}.js), pulei')
        registrar(caminho)
        return False
    igual = parecido_com_existente(nome)
    if igual:
        print(f'  · {caminho.name}: parece ser o mesmo livro de livros/{igual}, pulei')
        registrar(caminho)
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
    registrar(caminho)
    print(f'  ✓ {caminho.name} → livros/{nome}.js' + ('' if capa else ' (sem capa)'))
    return True


def arquivos(alvos):
    for alvo in alvos:
        alvo = Path(alvo).expanduser()
        if alvo.is_file():
            yield alvo
        elif alvo.is_dir():
            yield from sorted(p for p in alvo.rglob('*') if p.suffix.lower() in ('.epub', '.pdf') + KINDLE)
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
        print('De olho na pasta. Solte um EPUB, PDF ou arquivo do Kindle nela; Ctrl+C para parar.')
    try:
        main()
    except KeyboardInterrupt:
        pass
