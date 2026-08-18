import os
import urllib.parse
import re
import time
import base64
import random
import feedparser
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_GAMES")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID_GAMES", BLOGGER_ID),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variavel/segredo: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "openai/gpt-oss-120b"

# --- GERACAO DE IMAGENS COM IA (Pollinations.ai) ---
# Opcional: se nao configurado, ou se qualquer etapa falhar, o script cai
# automaticamente no metodo antigo (busca de imagem no Openverse).
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # opcional: remove marca dagua e aumenta limite
# Sem token: 1 requisicao a cada 15s. Com token gratuito (auth.pollinations.ai): a cada 5s.
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
QTD_MIN_IMAGENS = 3
QTD_MAX_IMAGENS = 5

# --- FONTES: games no mundo todo (PC, console, mobile, tabuleiro, RPG, cards) ---
FONTES = {
    # Nacionais
    "IGN Brasil": "https://br.ign.com/feed/",
    "TecMundo Games": "https://www.tecmundo.com.br/feed/games",
    "Adrenaline (Games)": "https://www.adrenaline.com.br/feed/",
    "Critical Hits": "https://criticalhits.com.br/feed/",
    "Voxel": "https://www.tecmundo.com.br/feed/voxel",

    # Internacionais - generalistas de games
    "IGN Global": "https://www.ign.com/feed",
    "Kotaku": "https://kotaku.com/rss",
    "GameSpot": "https://www.gamespot.com/feeds/mashup/",
    "PC Gamer": "https://www.pcgamer.com/rss/",
    "Eurogamer": "https://www.eurogamer.net/feed",
    "Polygon": "https://www.polygon.com/rss/index.xml",
    "Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed",
    "VG247": "https://www.vg247.com/feed",
    "GamesRadar": "https://www.gamesradar.com/rss/",
    "Game Rant": "https://gamerant.com/feed/",
    "Dot Esports": "https://dotesports.com/feed",

    # Consoles/plataformas especificas
    "Nintendo Life": "https://www.nintendolife.com/feeds/latest",
    "Push Square (PlayStation)": "https://www.pushsquare.com/feeds/latest",
    "Pure Xbox": "https://www.purexbox.com/feeds/latest",

    # Mobile
    "TouchArcade": "https://toucharcade.com/feed/",
    "Pocket Gamer": "https://www.pocketgamer.com/rss/",

    # Tabuleiro / RPG de mesa / cards
    "Tabletop Gaming News": "https://tabletopgamingnews.com/feed/",
}

# --- Tags/labels do Blogger por categoria (a IA escolhe a categoria certa) ---
CATEGORIAS_TAGS = {
    "pc": ["pc gamer", "games", "steam"],
    "console": ["console", "games", "playstation", "xbox", "nintendo"],
    "mobile": ["jogos mobile", "celular", "games"],
    "retro": ["retro games", "nostalgia", "games classicos"],
    "arcade": ["arcade", "fliperama", "games"],
    "tabuleiro": ["jogo de tabuleiro", "board game", "games"],
    "card": ["card game", "tcg", "games"],
    "rpg": ["rpg de mesa", "rpg", "games"],
    "esports": ["esports", "competitivo", "games"],
    "indie": ["jogo indie", "indie games", "games"],
}

ARQUIVO_HISTORICO = "historico_jogos_novidades.txt"
ARQUIVO_HISTORICO_RETRO = "historico_jogos_retro.txt"

# --- LINHA DO TEMPO DOS GAMES (fatos reais e bem documentados) ---
# Usada como fallback "hoje na historia dos games" quando nao ha noticia fresca nas fontes.
# Fornecer o fato pronto para a IA evita que ela invente datas/numeros incorretos.
GAMES_HISTORICOS = [
    {"ano": 1958, "evento": "o fisico William Higinbotham cria o 'Tennis for Two', um dos primeiros jogos eletronicos da historia, rodando em um osciloscopio"},
    {"ano": 1972, "evento": "a Atari lanca 'Pong' nos fliperamas, popularizando os video games"},
    {"ano": 1972, "evento": "a Magnavox lanca o Odyssey, o primeiro console domestico de video game"},
    {"ano": 1975, "evento": "a Atari lanca a versao domestica de 'Pong' para tocar na TV de casa"},
    {"ano": 1977, "evento": "a Atari lanca o console Atari 2600 (VCS), que populariza os cartuchos intercambiaveis"},
    {"ano": 1978, "evento": "'Space Invaders' e lancado nos fliperamas japoneses e se torna febre mundial"},
    {"ano": 1980, "evento": "'Pac-Man' e lancado pela Namco e se torna um icone cultural"},
    {"ano": 1981, "evento": "'Donkey Kong' e lancado nos arcades, marcando a estreia do personagem que viraria Mario"},
    {"ano": 1983, "evento": "a industria de video games norte-americana sofre o famoso 'crash de 1983', quase acabando com o mercado"},
    {"ano": 1983, "evento": "a Nintendo lanca o Famicom no Japao, base do que se tornaria o NES"},
    {"ano": 1985, "evento": "o NES (Nintendo Entertainment System) chega aos Estados Unidos, revivendo a industria pos-crash, junto com 'Super Mario Bros.'"},
    {"ano": 1986, "evento": "'The Legend of Zelda' e lancado no Japao para o Famicom Disk System"},
    {"ano": 1987, "evento": "o Master System da Sega, distribuido pela Tectoy, comeca sua trajetoria de sucesso no Brasil"},
    {"ano": 1988, "evento": "a Sega lanca o Mega Drive no Japao"},
    {"ano": 1989, "evento": "a Nintendo lanca o Game Boy, revolucionando os jogos portateis"},
    {"ano": 1989, "evento": "'Prince of Persia' e lancado, com sua animacao fluida revolucionaria para a epoca"},
    {"ano": 1990, "evento": "a Nintendo lanca o Super Famicom no Japao, que chegaria ao ocidente como Super Nintendo (SNES)"},
    {"ano": 1991, "evento": "'Sonic the Hedgehog' estreia no Mega Drive como resposta da Sega ao Mario"},
    {"ano": 1992, "evento": "'Mortal Kombat' e lancado nos arcades, iniciando polemicas por sua violencia grafica"},
    {"ano": 1993, "evento": "a id Software lanca 'Doom', um marco fundador dos jogos de tiro em primeira pessoa"},
    {"ano": 1993, "evento": "Richard Garfield cria 'Magic: The Gathering', o primeiro grande jogo de cartas colecionaveis (TCG) do mundo"},
    {"ano": 1994, "evento": "a Sony lanca o PlayStation no Japao, entrando de vez na guerra dos consoles"},
    {"ano": 1994, "evento": "a Sega lanca o Sega Saturn no Japao"},
    {"ano": 1995, "evento": "'Chrono Trigger' e lancado para o Super Famicom no Japao, tornando-se um classico cult dos RPGs"},
    {"ano": 1996, "evento": "a Nintendo lanca o Nintendo 64 no Japao"},
    {"ano": 1996, "evento": "'Pokemon Red e Green' sao lancados no Japao para o Game Boy, dando inicio ao fenomeno Pokemon"},
    {"ano": 1996, "evento": "o Pokemon Trading Card Game e lancado no Japao"},
    {"ano": 1996, "evento": "'Resident Evil' e lancado, popularizando o genero survival horror"},
    {"ano": 1997, "evento": "'Final Fantasy VII' e lancado para o PlayStation, se tornando um marco dos RPGs em 3D"},
    {"ano": 1997, "evento": "'GoldenEye 007' e lancado para o Nintendo 64, referencia em jogos de tiro em console"},
    {"ano": 1998, "evento": "'The Legend of Zelda: Ocarina of Time' e lancado para o Nintendo 64"},
    {"ano": 1998, "evento": "a Valve lanca 'Half-Life', elevando a narrativa dos jogos de tiro em primeira pessoa"},
    {"ano": 1999, "evento": "a Sega lanca o Dreamcast nos Estados Unidos"},
    {"ano": 2000, "evento": "a Sony lanca o PlayStation 2 no Japao, que se tornaria o console mais vendido da historia"},
    {"ano": 2001, "evento": "a Microsoft lanca o Xbox, entrando pela primeira vez na guerra dos consoles"},
    {"ano": 2001, "evento": "a Nintendo lanca o GameCube"},
    {"ano": 2001, "evento": "'Grand Theft Auto III' e lancado, revolucionando os jogos de mundo aberto"},
    {"ano": 2001, "evento": "'Halo: Combat Evolved' e lancado como jogo de lancamento do Xbox"},
    {"ano": 2003, "evento": "a Nokia lanca o N-Gage, um celular hibrido com console portatil"},
    {"ano": 2004, "evento": "a Blizzard lanca 'World of Warcraft', que se tornaria o MMORPG mais popular do mundo"},
    {"ano": 2004, "evento": "a Nintendo lanca o Nintendo DS, com sua tela dupla inovadora"},
    {"ano": 2004, "evento": "a Valve lanca 'Half-Life 2'"},
    {"ano": 2004, "evento": "a Sony lanca o PSP (PlayStation Portable) no Japao"},
    {"ano": 2005, "evento": "a Microsoft lanca o Xbox 360"},
    {"ano": 2006, "evento": "a Sony lanca o PlayStation 3"},
    {"ano": 2006, "evento": "a Nintendo lanca o Wii, popularizando os controles por movimento"},
    {"ano": 2007, "evento": "a Irrational Games lanca 'BioShock'"},
    {"ano": 2007, "evento": "'Call of Duty 4: Modern Warfare' e lancado, redefinindo os jogos de tiro militares"},
    {"ano": 2008, "evento": "a Nintendo lanca o Nintendo DSi no Japao"},
    {"ano": 2009, "evento": "Markus 'Notch' Persson lanca a primeira versao alpha publica de 'Minecraft'"},
    {"ano": 2011, "evento": "'Minecraft' e oficialmente lancado apos dois anos em desenvolvimento aberto"},
    {"ano": 2011, "evento": "a Nintendo lanca o Nintendo 3DS"},
    {"ano": 2011, "evento": "a Sony lanca o PlayStation Vita no Japao"},
    {"ano": 2011, "evento": "'Dark Souls' e lancado, dando origem ao genero que ficaria conhecido como Soulslike"},
    {"ano": 2011, "evento": "'The Elder Scrolls V: Skyrim' e lancado"},
    {"ano": 2013, "evento": "a Sony e a Microsoft lancam PlayStation 4 e Xbox One quase simultaneamente"},
    {"ano": 2013, "evento": "'Grand Theft Auto V' e lancado, se tornando um dos produtos de entretenimento mais lucrativos da historia"},
    {"ano": 2013, "evento": "'The Last of Us' e lancado para o PlayStation 3"},
    {"ano": 2015, "evento": "a From Software lanca 'Bloodborne'"},
    {"ano": 2016, "evento": "'Pokemon GO' e lancado, levando a realidade aumentada para as ruas do mundo todo"},
    {"ano": 2017, "evento": "a Nintendo lanca o Nintendo Switch"},
    {"ano": 2017, "evento": "'The Legend of Zelda: Breath of the Wild' e lancado como jogo de lancamento do Switch"},
    {"ano": 2017, "evento": "'PlayerUnknown's Battlegrounds' (PUBG) populariza o genero battle royale"},
    {"ano": 2018, "evento": "'God of War' reinventa a franquia no PlayStation 4"},
    {"ano": 2018, "evento": "'Red Dead Redemption 2' e lancado pela Rockstar Games"},
    {"ano": 2020, "evento": "a Sony e a Microsoft lancam PlayStation 5 e Xbox Series X/S"},
    {"ano": 2020, "evento": "'Among Us', lancado em 2018, explode em popularidade mundial durante a pandemia"},
    {"ano": 2022, "evento": "a From Software lanca 'Elden Ring'"},
    {"ano": 2023, "evento": "a Larian Studios lanca 'Baldur's Gate 3'"},
    {"ano": 2023, "evento": "'The Legend of Zelda: Tears of the Kingdom' e lancado para o Nintendo Switch"},
    {"ano": 1935, "evento": "a Parker Brothers publica 'Monopoly' nos Estados Unidos, um dos jogos de tabuleiro mais vendidos da historia"},
    {"ano": 1960, "evento": "a Milton Bradley lanca a versao moderna de 'The Game of Life' (Jogo da Vida), celebrando 100 anos do jogo original"},
    {"ano": 1974, "evento": "Gary Gygax e Dave Arneson publicam 'Dungeons & Dragons', criando o genero de RPG de mesa"},
]


def evento_retro_ja_usado(evento):
    if not os.path.exists(ARQUIVO_HISTORICO_RETRO):
        return False
    with open(ARQUIVO_HISTORICO_RETRO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    return evento["evento"] in linhas[-30:]


def marcar_evento_retro_usado(evento):
    with open(ARQUIVO_HISTORICO_RETRO, "a", encoding="utf-8") as f:
        f.write(evento["evento"] + "\n")


def escolher_evento_retro():
    disponiveis = [e for e in GAMES_HISTORICOS if not evento_retro_ja_usado(e)]
    if not disponiveis:
        disponiveis = GAMES_HISTORICOS
    return random.choice(disponiveis)


def ja_foi_postada(link):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return link in f.read()


def marcar_como_postada(link):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def pegar_novidade():
    fontes_lista = list(FONTES.items())
    random.shuffle(fontes_lista)

    for nome_fonte, url_rss in fontes_lista:
        try:
            feed = feedparser.parse(url_rss, agent="Mozilla/5.0")
            if feed.bozo and not feed.entries:
                print(f"Fonte com problema: {nome_fonte} -> {url_rss}")
                continue
        except Exception as e:
            print(f"Fonte falhou: {nome_fonte} -> {url_rss} | Erro: {e}")
            continue

        for entrada in feed.entries[:5]:
            link = entrada.get("link")
            titulo = entrada.get("title")
            resumo = entrada.get("summary") or entrada.get("description") or ""

            if not link or not titulo:
                continue

            if not ja_foi_postada(link):
                print(f"Novidade encontrada em {nome_fonte}: {titulo[:60]}...")
                return titulo, resumo, link, nome_fonte

    return None, None, None, None


IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": palavra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboCulturaPop/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO


DIMENSOES_RATIO = {
    "16:9": (1280, 720),
    "1:1": (1024, 1024),
    "9:16": (720, 1280),
}


def gerar_imagem_pollinations(prompt, ratio="16:9"):
    """Gera uma imagem via Pollinations.ai (gratuito, sem chave, sem cota diaria).
    Retorna bytes da imagem ou None se falhar."""
    largura, altura = DIMENSOES_RATIO.get(ratio, (1280, 720))
    try:
        prompt_codificado = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        params = {
            "width": largura,
            "height": altura,
            "model": "flux",
            "seed": random.randint(1, 999999),
            "nologo": "true",
        }
        headers = {}
        if POLLINATIONS_TOKEN:
            headers["Authorization"] = f"Bearer {POLLINATIONS_TOKEN}"
        resposta = requests.get(url, params=params, headers=headers, timeout=120)
        resposta.raise_for_status()
        content_type = resposta.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise ValueError(f"Resposta nao parece ser uma imagem (Content-Type: {content_type})")
        return resposta.content
    except Exception as e:
        print(f"⚠️ Pollinations.ai falhou para o prompt '{prompt[:40]}...': {e}")
        return None


def hospedar_imagem(imagem_bytes, nome_arquivo="imagem.png"):
    """Sobe a imagem gerada para o imgbb.com (host gratuito via API) e retorna a URL publica.
    Catbox.moe bloqueia uploads vindos de IPs de datacenter (ex: GitHub Actions), por isso
    usamos o imgbb, que aceita chamadas de API normalmente."""
    if not IMGBB_API_KEY:
        print("Falha ao hospedar imagem: IMGBB_API_KEY nao configurada")
        return None
    try:
        b64 = base64.b64encode(imagem_bytes).decode("utf-8")
        resposta = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64, "name": nome_arquivo},
            timeout=30,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("success"):
            return dados["data"]["url"]
        raise ValueError(f"Resposta inesperada do imgbb: {dados}")
    except Exception as e:
        print(f"Falha ao hospedar imagem gerada: {e}")
        return None


def gerar_imagem_ia(prompt, ratio="16:9"):
    """Pipeline completo: gera a imagem no Pollinations.ai e hospeda no imgbb. Retorna URL ou None."""
    imagem_bytes = gerar_imagem_pollinations(prompt, ratio)
    if not imagem_bytes:
        return None
    return hospedar_imagem(imagem_bytes)


def _limpar_tag(texto):
    return re.sub(r"<[^>]+>", "", texto).strip()


def extrair_titulos_h2(html):
    return re.findall(r"<h2[^>]*>(.*?)</h2>", html, flags=re.IGNORECASE | re.DOTALL)


def contar_palavras_html(html):
    texto = re.sub(r"<[^>]+>", " ", html)
    return len(texto.split())


def calcular_qtd_imagens(wc, minimo, maximo, base_palavras, palavras_por_imagem_extra):
    if wc <= base_palavras:
        return minimo
    extras = (wc - base_palavras) // palavras_por_imagem_extra
    return min(maximo, minimo + extras)


def gerar_prompts_imagens_ia(titulo_post, secoes, quantidade, contexto_extra=""):
    """Pede a IA prompts de imagem em ingles: o primeiro no estilo 'capa/thumbnail de loja'
    para atrair clique, e os demais ligados a cada momento/secao do post."""
    qtd_secoes = max(0, quantidade - 1)
    secoes_usadas = secoes[:qtd_secoes]
    lista_secoes = "\n".join(f"- {s}" for s in secoes_usadas) or "- (sem subtitulos definidos, use o tema geral do post)"

    prompt = f"""
Voce e um diretor de arte criando prompts para um gerador de imagens por IA (estilo Stable Diffusion/Flux).
Titulo do post: "{titulo_post}"
{contexto_extra}

Preciso de exatamente {quantidade} prompts de imagem em INGLES, cada um em uma linha separada, SEM numeracao,
SEM aspas, SEM explicacoes - apenas os prompts, um por linha, nesta ordem:

1) A PRIMEIRA linha e a imagem de CAPA/THUMBNAIL: precisa parecer uma thumbnail profissional de
   loja/vitrine digital (estilo capa chamativa de streaming ou loja de jogos/filmes), altissimo impacto
   visual, cores vibrantes, composicao central, iluminacao dramatica, foco no elemento principal do
   tema, sem texto escrito na imagem, pensada para maximizar cliques.
2) As proximas linhas sao uma imagem para CADA um destes momentos/secoes do post (nesta ordem):
{lista_secoes}
   Cada prompt deve remeter visualmente ao conteudo daquela secao especifica, mantendo consistencia
   estetica com o tema geral.

Cada prompt: descritivo, rico em detalhes visuais (cenario, iluminacao, estilo artistico, composicao),
SEM citar nomes proprios de personagens, obras ou marcas registradas especificas - descreva visualmente
sem citar nomes proprios de obras protegidas. Responda APENAS com as {quantidade} linhas de prompt.
"""
    resposta = pedir_ia_groq(prompt, temperatura=0.8)
    linhas = [l.strip(" -\"") for l in resposta.strip().splitlines() if l.strip()]
    if len(linhas) < quantidade:
        while len(linhas) < quantidade:
            linhas.append(linhas[-1] if linhas else titulo_post)
    return linhas[:quantidade]


def montar_galeria_ia(titulo_post, corpo_html, minimo, maximo, contexto_extra=""):
    """Gera a galeria completa de imagens via Pollinations.ai. Lanca excecao se qualquer
    etapa falhar, para o chamador cair no fallback do Openverse."""
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY nao configurada")

    secoes_brutas = extrair_titulos_h2(corpo_html)
    secoes = [_limpar_tag(s) for s in secoes_brutas]

    wc = contar_palavras_html(corpo_html)
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=500, palavras_por_imagem_extra=250)
    if secoes:
        qtd = min(qtd, len(secoes) + 1)
    qtd = max(1, qtd)

    prompts = gerar_prompts_imagens_ia(titulo_post, secoes, qtd, contexto_extra)

    galeria = []
    for i, prompt in enumerate(prompts):
        url = gerar_imagem_ia(prompt, ratio="16:9")
        if not url:
            raise RuntimeError(f"Falha ao gerar/hospedar imagem {i + 1}/{qtd} da galeria")
        alt = titulo_post if i == 0 else (secoes[i - 1] if i - 1 < len(secoes) else titulo_post)
        galeria.append((url, alt))
        if i < len(prompts) - 1:
            time.sleep(INTERVALO_POLLINATIONS)  # respeita o rate limit do Pollinations.ai

    return galeria, secoes_brutas


def inserir_imagens_no_corpo(corpo_html, secoes_brutas, galeria):
    """Insere as imagens de secao (a partir do indice 1 da galeria) logo apos os respectivos <h2>."""
    novo_html = corpo_html
    imagens_secao = galeria[1:]
    for i, (url, alt) in enumerate(imagens_secao):
        if i >= len(secoes_brutas):
            break
        h2_bruto = secoes_brutas[i]
        padrao = re.compile(r"(<h2[^>]*>" + re.escape(h2_bruto) + r"</h2>)", re.IGNORECASE)
        img_html = gerar_tabela_imagem_blogger(url, alt)
        novo_html, _ = padrao.subn(lambda m: m.group(1) + img_html, novo_html, count=1)
    return novo_html


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return (
        '<table align="center" cellpadding="0" cellspacing="0" '
        'class="tr-caption-container" style="margin-left: auto; margin-right: auto;">'
        '<tbody><tr><td style="text-align: center;">'
        f'<img alt="{alt_title}" border="0" height="360" src="{url_img}" '
        f'title="{alt_title}" width="640" /></td></tr></tbody></table><br />'
    )


def pedir_ia_groq(prompt, temperatura=0.7):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def extrair_palavra_chave(titulo):
    prompt = (
        f"Baseado neste titulo: '{titulo}', de apenas UMA palavra-chave em ingles que "
        f"descreva visualmente o tema (ex: 'video game', 'retro console', 'board game', "
        f"'esports arena', 'mobile game'). Responda so a palavra."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(titulo):
    categorias_validas = list(CATEGORIAS_TAGS.keys())
    prompt = (
        f"Baseado neste titulo de noticia de games: '{titulo}', escolha a categoria mais adequada "
        f"entre: {', '.join(categorias_validas)}. Responda APENAS com a palavra da categoria."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return "console"


def gerar_titulo(titulo_original):
    prompt = (
        f"Crie um titulo inedito, chamativo, otimizado para SEO, em portugues do Brasil, "
        f"sem aspas, baseado nesta noticia de games: '{titulo_original}'. "
        f"Responda apenas o titulo, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo(titulo_original, resumo, nome_fonte):
    prompt = f"""
Voce e um redator (pesquisa varias fontes) especializado em games no sentido mais amplo possivel:
jogos de PC, console, mobile, arcade/fliperama, jogos de tabuleiro, RPG de mesa, card games e
esports, para um blog de fas muito engajado. Sabe todas as novidades, sabe traçar raciocinio,
memoria e transcrever de forma agradavel, engraçada, futuca bastidores, sabe uma ou outra
fofoquinha, sabe construir comunidade. Escreva com qualidade alta, sem pressa - capriche de verdade.

Traduza e reescreva completamente (nunca copie frases), em portugues do Brasil, esta
novidade (fonte: {nome_fonte}):
Titulo original: {titulo_original}
Resumo original: {resumo}

REGRAS IMPORTANTES:
- Se a informacao original for curta, EXPANDA com contexto real e relevante: historico
  da franquia/estudio/desenvolvedora, curiosidades de bastidores amplamente conhecidas,
  recepcao do publico, comparacoes com jogos anteriores da franquia ou genero. NAO invente
  fatos especificos (datas, numeros, declaracoes) que voce nao tenha certeza - contextualize
  com conhecimento geral real, nunca com invencoes especificas.
- NAO seja repetitivo em nenhuma hipotese: cada paragrafo tem que trazer informacao
  nova, sem reafirmar o que ja foi dito com outras palavras.
- Tamanho: entre 600 e 1200 palavras (pode passar de 1200 se o assunto pedir).

REGRAS DE FORMATO (HTML puro, sem Markdown):
1. Paragrafo de abertura envolvente.
2. NO MINIMO 3 subtitulos <h2> (ex: contexto, detalhes, repercussao/expectativa dos fas).
3. Insira 3 notas do autor engracada e leve dentro de <blockquote>, comentando com humor
   de fa gamer (nunca debochado ou ofensivo) espalhados pelo post.
4. Sempre incluir fontes para passar credibilidade.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


# --- MODO RETRO: usado quando nenhuma fonte tem noticia nova no momento ---
def gerar_titulo_retro(evento):
    prompt = (
        f"Fato real: em {evento['ano']}, {evento['evento']}.\n\n"
        f"Crie um titulo nostalgico, envolvente e chamativo para um post de blog de games "
        f"sobre esse fato, em portugues do Brasil, sem aspas, no estilo 'Voce nasceu em "
        f"[ano]? Entao sabe o que aconteceu nos games' ou 'Ha [X] anos...' (calcule X a partir "
        f"do ano informado, ano atual e 2026). Responda apenas o titulo, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo_retro(evento):
    prompt = f"""
Voce e um redator especializado em games (PC, console, mobile, arcade, tabuleiro, RPG de mesa,
card games e esports) para um blog de fas muito engajado, focado em nostalgia e comunidade.

Hoje nao ha noticia fresca nas fontes, entao a pauta de hoje e uma viagem no tempo: "hoje na
historia dos games". Fato real e confirmado para basear o artigo (NAO mude o ano nem invente
outros fatos especificos como datas/numeros - use APENAS este fato como ancora factual):

Ano: {evento['ano']}
Fato: {evento['evento']}

Escreva um artigo nostalgico e envolvente em portugues do Brasil sobre esse fato, no estilo
conversacional que conecta com o leitor pela memoria afetiva - por exemplo abrindo com algo
como "Voce nasceu em [ano]? Entao sabe o que rolava nos games!" ou "Ha [calcule os anos ate
2026] anos...". Explore:
- O contexto da epoca (o que mais estava acontecendo nos games e na cultura pop daquele ano).
- Por que esse marco foi importante e como ele influenciou os games que vieram depois.
- Curiosidades de bastidores amplamente conhecidas sobre esse fato (sem inventar numeros
  especificos que voce nao tenha certeza).
- Comparacoes com o cenario atual dos games - o que mudou, o que ainda ecoa hoje.

REGRAS IMPORTANTES:
- NAO invente fatos especificos (datas, numeros, declaracoes) alem do fato fornecido.
- NAO seja repetitivo: cada paragrafo traz informacao nova.
- Tamanho: entre 600 e 1000 palavras.

REGRAS DE FORMATO (HTML puro, sem Markdown):
1. Paragrafo de abertura nostalgico e envolvente, conectando com a memoria afetiva do leitor.
2. NO MINIMO 3 subtitulos <h2> (ex: contexto da epoca, por que importou, legado hoje).
3. Insira 3 notas do autor engracadas e leves dentro de <blockquote>, comentando com humor
   de fa gamer nostalgico (nunca debochado ou ofensivo) espalhados pelo post.
4. Termine convidando o leitor a comentar suas proprias lembrancas dessa epoca dos games.
"""
    return pedir_ia_groq(prompt, temperatura=0.8)


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Curtiu essa novidade?</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Deixe seu comentario, curta e compartilhe com a galera que também acompanha o assunto!</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
        <a href="#" onclick="window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(document.title + ' - ' + window.location.href), '_blank'); return false;" style="background-color: #25d366; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">WhatsApp</a>
        <a href="#" onclick="window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #1877f2; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">Facebook</a>
        <a href="#" onclick="window.open('https://twitter.com/intent/tweet?url=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #000; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">X</a>
    </div>
</div>
"""



def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return creds


def publicar_no_blogger(titulo, conteudo, tags):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {
        'kind': 'blogger#post',
        'title': titulo,
        'content': conteudo,
        'labels': tags,
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("Buscando novidade de games...")
    titulo_original, resumo, link, fonte = pegar_novidade()

    if titulo_original:
        print(f"Encontrado em [{fonte}]: {titulo_original[:100]}...")
        try:
            categoria = identificar_categoria(titulo_original)
            tags = CATEGORIAS_TAGS.get(categoria, ["games"])

            novo_titulo = gerar_titulo(titulo_original)
            corpo = gerar_artigo(titulo_original, resumo, fonte)

            try:
                galeria, secoes_brutas = montar_galeria_ia(
                    novo_titulo,
                    corpo,
                    minimo=QTD_MIN_IMAGENS,
                    maximo=QTD_MAX_IMAGENS,
                    contexto_extra=f"Resumo da noticia (fonte: {fonte}): {resumo}",
                )
                img_html = gerar_tabela_imagem_blogger(galeria[0][0], novo_titulo)
                corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
                print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
            except Exception as e:
                print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
                palavra_chave = extrair_palavra_chave(titulo_original)
                img_url = buscar_imagem_openverse(palavra_chave)
                img_html = gerar_tabela_imagem_blogger(img_url, novo_titulo)

            cta = gerar_cta()

            rodape = (
                '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
                '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
                f'Fonte da noticia original: <a href="{link}" rel="noopener noreferrer" target="_blank">{fonte}</a>'
                '</p>'
            )

            html_final = f"{img_html}{corpo}{cta}{rodape}"
            publicar_no_blogger(novo_titulo, html_final, tags)
            marcar_como_postada(link)
            print("Concluido!")
        except Exception as e:
            print(f"Erro durante geracao/publicacao: {e}")
    else:
        print("Nenhuma novidade nova encontrada nas fontes. Ativando modo retro (hoje na historia dos games)...")
        try:
            evento = escolher_evento_retro()
            print(f"Efemeride escolhida: {evento['ano']} - {evento['evento'][:80]}...")

            categoria = identificar_categoria(evento["evento"])
            tags = CATEGORIAS_TAGS.get(categoria, ["games"]) + ["retro games", "nostalgia"]
            tags = list(dict.fromkeys(tags))  # remove duplicatas mantendo a ordem

            novo_titulo = gerar_titulo_retro(evento)
            corpo = gerar_artigo_retro(evento)

            try:
                galeria, secoes_brutas = montar_galeria_ia(
                    novo_titulo,
                    corpo,
                    minimo=QTD_MIN_IMAGENS,
                    maximo=QTD_MAX_IMAGENS,
                    contexto_extra=f"Efemeride retro de {evento['ano']}: {evento['evento']}",
                )
                img_html = gerar_tabela_imagem_blogger(galeria[0][0], novo_titulo)
                corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
                print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
            except Exception as e:
                print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
                palavra_chave = extrair_palavra_chave(evento["evento"])
                img_url = buscar_imagem_openverse(palavra_chave)
                img_html = gerar_tabela_imagem_blogger(img_url, novo_titulo)

            cta = gerar_cta()

            rodape = (
                '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
                '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
                'Conteudo retro: nao ha noticia fresca no momento, entao trouxemos uma efemeride '
                'da historia dos games para matar a saudade.</p>'
            )

            html_final = f"{img_html}{corpo}{cta}{rodape}"
            publicar_no_blogger(novo_titulo, html_final, tags)
            marcar_evento_retro_usado(evento)
            print("Concluido (modo retro)!")
        except Exception as e:
            print(f"Erro durante geracao/publicacao do modo retro: {e}")
