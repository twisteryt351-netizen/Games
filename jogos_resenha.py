import os
import urllib.parse
import re
import time
import base64
import random
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURACOES ---
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
QTD_MIN_IMAGENS = 5
QTD_MAX_IMAGENS = 10

# --- Tags/labels do Blogger por categoria (a IA escolhe a categoria certa) ---
CATEGORIAS_TAGS = {
    "console-retro": ["retro games", "console classico", "nostalgia"],
    "console-moderno": ["console", "playstation", "xbox", "nintendo"],
    "pc": ["pc gamer", "games", "steam"],
    "arcade": ["arcade", "fliperama", "pinball"],
    "mobile": ["jogos mobile", "celular", "games"],
    "tabuleiro": ["jogo de tabuleiro", "board game"],
    "card": ["card game", "tcg", "colecionavel"],
    "rpg-mesa": ["rpg de mesa", "rpg", "tabletop"],
    "rua": ["brincadeiras de rua", "infancia", "nostalgia"],
    "vr": ["realidade virtual", "vr games", "tecnologia"],
    "crossover": ["games na cultura pop", "filmes e series", "games"],
    "esports": ["esports", "competitivo", "games"],
}

# --- LISTA BASE DE TEMAS DE GAMES (historia completa: rua, tabuleiro, arcade, consoles, PC, mobile, VR) ---
TEMAS = [
    # --- A PRE-HISTORIA E O NASCIMENTO DOS VIDEO GAMES ---
    "o 'Tennis for Two' (1958), um dos primeiros jogos eletronicos da historia",
    "a criacao do 'Pong' pela Atari e o nascimento da industria dos video games",
    "o Magnavox Odyssey, o primeiro console domestico da historia",
    "o 'Space Invaders' e a febre que varreu os fliperamas do mundo",
    "o nascimento do 'Pac-Man' e seu impacto na cultura pop",
    "o 'Donkey Kong' e a estreia do personagem que se tornaria Mario",
    "o crash dos video games de 1983 e quase o fim da industria nos EUA",
    "a ascensao e queda dos fliperamas (arcades) como ponto de encontro social",
    "a historia do pinball (fliperama de bolinha) antes dos video games",
    "os primeiros jogos de fliperama que definiram generos inteiros",

    # --- CONSOLES CLASSICOS (ATARI, NES, MASTER SYSTEM) ---
    "o console Atari 2600 e a revolucao dos cartuchos intercambiaveis",
    "o legado do Atari no Brasil e os clones nacionais (Dactar, Dynavision)",
    "o NES (Nintendo Entertainment System) e o resgate da industria pos-crash",
    "o Master System e sua trajetoria unica e vitoriosa no Brasil pela Tectoy",
    "os jogos brasileiros exclusivos feitos pela Tectoy para o Master System",
    "a rivalidade Nintendo vs Sega no auge dos anos 80 e 90",
    "a historia do Game & Watch, os primeiros portateis da Nintendo",
    "os classicos escondidos do NES que poucos conhecem",
    "a cultura das locadoras de fita e cartuchos de video game no Brasil",
    "a historia da revista Video Game Brasil e o jornalismo gamer nos anos 90",

    # --- A GUERRA DOS 16-BITS (SNES, MEGA DRIVE) ---
    "a guerra de consoles dos anos 90: Super Nintendo vs Mega Drive",
    "o Super Nintendo (SNES) e sua biblioteca lendaria de RPGs e plataforma",
    "o Mega Drive e o carisma do Sonic the Hedgehog como resposta a Nintendo",
    "os jogos de luta que dominaram o SNES e o Mega Drive",
    "a chegada do Chrono Trigger e a era de ouro dos RPGs de 16-bits",
    "o Street Fighter II e a explosao dos jogos de luta em casa",
    "os acessorios bizarros da era 16-bits (Power Glove, Sega CD, 32X)",
    "a trilha sonora chiptune dos consoles de 16-bits e seu legado musical",

    # --- ARCADE E FLIPERAMA ---
    "a cultura dos fliperamas brasileiros nos anos 80 e 90",
    "os jogos de luta de arcade que formaram geracoes (Street Fighter, King of Fighters)",
    "os jogos de tiro sobre trilhos (light gun) dos fliperamas",
    "as maquinas de pinball classicas e sua epoca de ouro",
    "o fenomeno dos jogos de ritmo em arcade (Dance Dance Revolution)",
    "os recordes e a cultura competitiva dos arcades classicos",

    # --- CONSOLES 3D (PS1, N64, SATURN, DREAMCAST) ---
    "o PlayStation 1 e a entrada avassaladora da Sony na industria",
    "o Nintendo 64 e o pioneirismo dos analogicos e jogos 3D",
    "o Sega Saturn e por que ele nao conseguiu competir com o PS1",
    "o Sega Dreamcast, o console a frente do seu tempo que a Sega descontinuou cedo demais",
    "o Neo Geo, o console mais caro e exclusivo dos anos 90",
    "o Game Gear e a tentativa da Sega de competir com o Game Boy",
    "o Final Fantasy VII e a revolucao dos RPGs em 3D no PS1",
    "o Resident Evil e o nascimento do genero survival horror",
    "o Metal Gear Solid e o cinema interativo de Hideo Kojima",
    "o Crash Bandicoot e os mascotes exclusivos da era PS1",
    "o Spyro the Dragon e os plataformas 3D da era PS1",
    "o Tekken 3 e a evolucao dos jogos de luta em 3D",
    "o GoldenEye 007 e a revolucao dos FPS em console no N64",
    "o Ocarina of Time e por que ele e considerado um dos melhores games da historia",
    "o Banjo-Kazooie e a era dourada dos plataformas 3D da Rare",

    # --- GERACAO PS2/XBOX/GAMECUBE ---
    "o PlayStation 2, o console mais vendido da historia",
    "a entrada da Microsoft na industria com o primeiro Xbox",
    "o GameCube e a aposta ousada (e pouco compreendida) da Nintendo",
    "o GTA San Andreas e a explosao dos jogos de mundo aberto",
    "o GTA III e a revolucao que redefiniu o genero sandbox",
    "o Halo: Combat Evolved e o nascimento de um fenomeno no Xbox",
    "o Shadow of the Colossus e a arte minimalista nos video games",
    "o God of War (2005) e a brutalidade estilizada da era PS2",
    "o Silent Hill 2 e o horror psicologico nos video games",
    "o Devil May Cry e a criacao do genero hack-and-slash estiloso",

    # --- GERACAO PS3/XBOX 360/WII ---
    "a guerra de consoles PlayStation 3 vs Xbox 360",
    "o Nintendo Wii e a revolucao dos controles por movimento",
    "o Wii Sports e como ele mudou quem jogava video game",
    "o Call of Duty 4: Modern Warfare e a era de ouro dos FPS militares",
    "o BioShock e a narrativa filosofica dentro de Rapture",
    "o Portal e o humor negro da GLaDOS",
    "o The Elder Scrolls V: Skyrim e a obsessao por mundos abertos gigantes",
    "o Red Dead Redemption e o western nos video games",
    "o The Last of Us e a narrativa emocional que elevou os games a arte",
    "o Dark Souls e a criacao do genero Soulslike por Hidetaka Miyazaki",
    "o Minecraft e como um jogo indie de blocos conquistou o mundo",
    "o Rock Band e Guitar Hero e a febre dos jogos musicais",
    "o fenomeno indie Braid e a virada dos jogos autorais",

    # --- GERACAO PS4/XBOX ONE/SWITCH ---
    "o PlayStation 4 e a retomada de confianca da Sony junto aos jogadores",
    "o Xbox One e os tropecos de lancamento da Microsoft",
    "o Nintendo Switch e a genialidade de unir portatil e console de mesa",
    "o Zelda: Breath of the Wild e a reinvencao da formula da franquia",
    "o God of War (2018) e a reinvencao de Kratos como pai",
    "o Bloodborne e o horror gotico da From Software",
    "o Elden Ring e como a From Software conquistou o mainstream",
    "o Red Dead Redemption 2 e o realismo obsessivo da Rockstar",
    "o Grand Theft Auto V e por que ele nunca sai das paradas de vendas",
    "o fenomeno battle royale: do PUBG ao Fortnite",
    "o Among Us e a explosao inesperada de um jogo indie na pandemia",
    "o Hollow Knight e a nova era do metroidvania indie",
    "o Undertale e a subversao de expectativas em RPGs indie",
    "o Stardew Valley e o renascimento dos jogos de fazenda",
    "o Celeste e a representatividade e dificuldade nos jogos de plataforma",

    # --- GERACAO ATUAL (PS5, XBOX SERIES, E O FUTURO) ---
    "o PlayStation 5 e a era dos jogos com SSD ultrarrapido",
    "o Xbox Series X/S e a estrategia de assinatura Game Pass",
    "o Baldur's Gate 3 e o retorno triunfal dos RPGs classicos",
    "o Zelda: Tears of the Kingdom e a evolucao da fisica nos games",
    "os rumores e expectativas sobre a proxima geracao de consoles (o que se especula sobre PS6 e o futuro Xbox)",
    "a expectativa e tudo que se sabe ate agora sobre GTA VI",
    "a evolucao da franquia Grand Theft Auto do GTA 1 ate os dias de hoje",
    "o impacto dos jogos como servico (live service) na industria atual",
    "a ascensao dos remakes e remasters como estrategia da industria",

    # --- PORTATEIS (GAME BOY, PSP, DS, VITA, N-GAGE) ---
    "o Game Boy e como ele dominou os portateis por mais de uma decada",
    "o Pokemon Red e Blue e o nascimento de um dos maiores fenomenos da cultura pop",
    "o Nintendo DS e a tela dupla que reinventou os jogos portateis",
    "o Nintendo 3DS e a aposta (arriscada) do 3D sem oculos",
    "o Nintendo DSi e a evolucao silenciosa da linha DS",
    "o PSP (PlayStation Portable) e a tentativa da Sony de dominar os portateis",
    "o PS Vita e por que ele e lembrado como um console subestimado",
    "o Nokia N-Gage, o hibrido bizarro entre celular e console portatil",
    "os jogos de Game Boy Color e Game Boy Advance mais lembrados",
    "a nostalgia dos jogos portateis levados na mochila da escola",

    # --- MOBILE GAMES ---
    "a ascensao dos jogos de celular e como eles mudaram quem joga video game",
    "o Angry Birds e a explosao dos jogos mobile casuais",
    "o Candy Crush e a formula viciante dos jogos de puzzle mobile",
    "o Clash of Clans e o nascimento dos jogos de estrategia mobile competitivos",
    "o Pokemon GO e a revolucao da realidade aumentada nas ruas",
    "o Free Fire e o fenomeno battle royale mobile no Brasil",
    "o Genshin Impact e a ambicao de um RPG de mundo aberto no celular",
    "os jogos de Nokia como Snake e a nostalgia dos primeiros celulares",
    "a economia dos jogos free-to-play e as microtransacoes",

    # --- BRINCADEIRAS DE RUA E JOGOS FISICOS ---
    "a historia e as variacoes regionais do pega-pega pelo mundo",
    "o esconde-esconde e por que essa brincadeira atravessa geracoes",
    "a amarelinha e sua origem surpreendentemente antiga",
    "a queimada (bola queimada) e sua popularidade nas escolas brasileiras",
    "o pique-bandeira e suas variacoes regionais no Brasil",
    "a peteca, um dos jogos mais antigos e genuinamente brasileiros",
    "o boliche de rua improvisado e outras brincadeiras com materiais reciclados",
    "as brincadeiras de roda e cantigas infantis tradicionais",
    "o jogo de bolinha de gude e sua epoca de ouro nos patios escolares",
    "a empinada de pipa como brincadeira e competicao popular",

    # --- JOGOS DE TABULEIRO ---
    "a historia do Banco Imobiliario e sua adaptacao do Monopoly nos EUA",
    "a origem do Monopoly e a disputa sobre quem realmente o inventou",
    "o Jogo da Vida (The Game of Life) e sua jornada de mais de 160 anos",
    "o War e a paixao brasileira por conquistar o mundo no tabuleiro",
    "o Detetive (Cluedo) e o nascimento dos jogos de deducao",
    "o Xadrez e sua historia milenar como o jogo estrategico definitivo",
    "as Damas e sua simplicidade enganosamente profunda",
    "o Uno e como um jogo de cartas simples virou fenomeno mundial",
    "o Dominó e sua popularidade em rodas de bar e mesas de familia",
    "o Banco Imobiliario Brasileiro e as edicoes tematicas que marcaram geracoes",
    "o Perfil e a febre dos jogos de tabuleiro de perguntas nos anos 90 e 2000",
    "o Imagem & Acao e a mania dos jogos de mimica em familia",
    "o Catan e a revolucao dos jogos de tabuleiro modernos (euro games)",

    # --- CARD GAMES E COLECIONAVEIS ---
    "a criacao do Magic: The Gathering e o nascimento dos card games colecionaveis",
    "o Pokemon Trading Card Game e a febre de colecionar e trocar cartas",
    "o Yu-Gi-Oh! e como o anime impulsionou um dos maiores TCGs do mundo",
    "o Truco e sua paixao avassaladora no sul do Brasil",
    "o baralho comum e os jogos populares como buraco, sueca e paciencia",
    "a cultura dos torneios competitivos de card games ao redor do mundo",
    "o Hearthstone e a adaptacao digital bem-sucedida dos card games",

    # --- RPG DE MESA ---
    "a criacao do Dungeons & Dragons e o nascimento do RPG de mesa",
    "o Tormenta RPG e o fenomeno brasileiro de RPG de fantasia nacional",
    "o Vampiro: A Mascara e os RPGs de horror pessoal dos anos 90",
    "o GURPS e a filosofia de um sistema de RPG genérico e flexivel",
    "a cultura das mesas de RPG e a criacao de comunidade em torno do mestre e jogadores",
    "como o RPG de mesa influenciou diretamente os RPGs eletronicos",
    "a ascensao do RPG de mesa em lives e podcasts (estilo Critical Role)",

    # --- REALIDADE VIRTUAL ---
    "a historia e as tentativas fracassadas de realidade virtual nos anos 90",
    "o PSVR e a aposta da Sony em realidade virtual para consoles",
    "o Meta Quest e a popularizacao da VR standalone sem fios",
    "os jogos que definiram o que a realidade virtual pode oferecer",
    "o futuro da realidade virtual e realidade aumentada nos games",

    # --- GAMES NA CULTURA POP: FILMES, SERIES E CROSSOVERS ---
    "a adaptacao de 'The Last of Us' para serie de TV e sua recepcao",
    "o filme 'Super Mario Bros: O Filme' e as tentativas de adaptar games ao cinema",
    "a serie animada 'Arcane', baseada no universo de League of Legends",
    "a serie 'Fallout' e sua adaptacao do universo pos-apocaliptico dos games",
    "o filme 'Sonic the Hedgehog' e a receita de sucesso das adaptacoes recentes",
    "o filme de 'Mortal Kombat' e a longa historia de adaptacoes do jogo de luta",
    "o anime 'Pokemon' e seu impacto duradouro alem dos games",
    "a serie 'Cyberpunk: Edgerunners' e como ela salvou a reputacao do jogo",
    "os video games baseados em filmes e series e sua fama de qualidade duvidosa",
    "os easter eggs e referencias cruzadas entre franquias de games e cinema",

    # --- ESPORTS E CULTURA COMPETITIVA ---
    "a origem dos esports e os primeiros torneios competitivos de video game",
    "a historia do League of Legends e sua ascensao como maior esport do mundo",
    "a cena competitiva de Counter-Strike, do 1.6 ao CS2",
    "o Dota 2 e o torneio The International com premiacoes milionarias",
    "a cultura das lan houses brasileiras nos anos 2000 e o nascimento da cena competitiva nacional",
    "o Free Fire e a explosao dos esports mobile no Brasil",
]

ARQUIVO_HISTORICO = "historico_jogos_resenha.txt"


def tema_ja_usado(tema):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    # Evita repetir o mesmo tema exato nos últimos 30 ciclos (lista bem maior agora)
    return tema in linhas[-30:]


def marcar_tema_usado(tema):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(tema + "\n")


def escolher_tema():
    disponiveis = [t for t in TEMAS if not tema_ja_usado(t)]
    if not disponiveis:
        disponiveis = TEMAS
    return random.choice(disponiveis)


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
            headers={"User-Agent": "RoboResenhaJogos/1.0"},
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
   estetica com o tema geral (tom nostalgico/documental).

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
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=1400, palavras_por_imagem_extra=250)
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


def pedir_ia_groq(prompt, temperatura=0.7, max_tokens=None):
    kwargs = {
        "messages": [{"role": "user", "content": prompt}],
        "model": MODELO_IA,
        "temperature": temperatura,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = groq_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


def gerar_esqueleto(instrucao_tema):
    """ETAPA 1: Sorteia um ângulo e pede um esqueleto detalhado.
    A injeção do ângulo garante posts inéditos no futuro."""
    
    angulos = [
        "Foco em Bastidores e Desenvolvimento (como foi criado, perrengues de produção, equipe, segredos de criação).",
        "Análise Crítica e Temática (o que fez esse jogo/console/brincadeira funcionar, design, mecânicas, simbolismo).",
        "Impacto Cultural e Legado (como mudou a indústria, revolução no gênero, obras que foram influenciadas por ele).",
        "Curiosidades Pouco Conhecidas e Easter Eggs (fatos estranhos, detalhes imperceptíveis, mitos e verdades).",
        "Visão Nostálgica e Recepção no Brasil (como chegou por aqui, dublagem/localização, febre entre os fãs na época, lan houses, videolocadoras).",
        "Comparação com o Cenário Atual (o que mudou, o que ainda influencia os games/brincadeiras de hoje, o que ficou datado)."
    ]
    angulo_sorteado = random.choice(angulos)
    
    prompt = f"""
Você é um roteirista de documentários sobre a história dos games em seu sentido mais amplo: video
games de PC e console, arcade/fliperama, jogos de tabuleiro, card games, RPG de mesa, brincadeiras
de rua, jogos mobile e realidade virtual.

Tema central de hoje: {instrucao_tema}

⚠️ ÂNGULO OBRIGATÓRIO PARA A MATÉRIA DE HOJE:
"{angulo_sorteado}"

Primeiro, ANTES de escrever o artigo, monte um ESQUELETO detalhado guiado por esse ângulo:
- Confirme o tema principal e o ângulo escolhido.
- Liste de 6 a 8 tópicos/seções que o artigo vai cobrir (o suficiente para um artigo longo e denso).
- Para cada tópico, escreva 1-2 frases resumindo o que será abordado, SEM repetir informação.

Responda apenas com esse esqueleto, em texto simples (sem HTML).
"""
    return pedir_ia_groq(prompt, temperatura=0.6)


def gerar_artigo_completo(esqueleto):
    """ETAPA 2: Pede o artigo completo usando o esqueleto como guia obrigatório."""
    prompt = f"""
Você é um redator de games premiado, cronista! Escreve artigos estilo documentário/resenha
para um blog de fãs muito engajado sobre games em todas as suas formas: video games de PC e
console, arcade, tabuleiro, card games, RPG de mesa, brincadeiras de rua, mobile e VR. Escreva
com MUITO capricho, sem pressa - este é um artigo de destaque do blog.
Você pesquisa a fundo, sabe traçar raciocínio, memória e transcrever de forma agradável,
engraçada, futuca bastidores, sabe uma ou outra fofoquinha e constrói comunidade.

Use este esqueleto como guia OBRIGATÓRIO, desenvolvendo cada tópico dele em profundidade,
sem pular nenhum e sem repetir informação entre seções:

{esqueleto}

REGRAS DE CONTEÚDO:
- Baseie-se em fatos históricos e culturais reais sobre o tema. NÃO invente datas ou números sem certeza.
- Escreva de forma agradável e envolvente, com tom nostálgico e conversacional que constrói comunidade.
- PROIBIDO repetir a mesma frase ou ideia. Cada parágrafo deve avançar a narrativa.
- Se o tema envolver lançamentos futuros ou rumores (ex: próxima geração de consoles), deixe
  claro no texto que se trata de expectativa/especulação, e não de fato confirmado.
- Tamanho OBRIGATÓRIO: no MÍNIMO 1600 palavras. Desenvolva bem cada seção - se precisar,
  aprofunde mais em curiosidades, comparações e contexto histórico para atingir esse tamanho
  com qualidade, sem enrolação ou repetição.

REGRAS DE FORMATO (HTML puro, sem Markdown):
1. Comece direto com um parágrafo de abertura instigante (sem h1).
2. Cada tópico do esqueleto vira um subtítulo <h2> próprio.
3. Inclua PELO MENOS 3 notas do autor engraçadas e leves, cada uma dentro de <blockquote>, com
   comentários de fã gamer nostálgico, espalhadas ao longo do post.
4. Não inclua links no corpo do texto.
5. Termine com um parágrafo de fechamento reflexivo sobre o legado do tema, convidando o leitor
   a comentar suas próprias lembranças ou opiniões.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


def gerar_titulo(esqueleto):
    prompt = (
        f"Baseado neste esqueleto de artigo:\n{esqueleto}\n\n"
        f"Crie um título de blog envolvente, nostálgico, otimizado para SEO, em português "
        f"do Brasil, sem aspas. Responda apenas o título, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def extrair_palavra_chave(esqueleto):
    prompt = (
        f"Baseado neste esqueleto de artigo:\n{esqueleto}\n\n"
        f"Dê apenas UMA palavra-chave em inglês que descreva visualmente o tema principal "
        f"(ex: 'retro console', 'arcade cabinet', 'board game', 'tabletop rpg', 'vintage video game'). "
        f"Responda só a palavra."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(esqueleto):
    categorias_validas = list(CATEGORIAS_TAGS.keys())
    prompt = (
        f"Baseado neste esqueleto de artigo sobre games:\n{esqueleto}\n\n"
        f"Escolha a categoria mais adequada entre: {', '.join(categorias_validas)}. "
        f"Responda APENAS com a palavra da categoria."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return "console-retro"


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Gostou dessa viagem no tempo?</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Curta, deixe seu comentário contando suas lembranças do assunto e compartilhe com quem também vai se emocionar!</p>
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
    print("Gerando resenha/documentario de games...")
    instrucao_tema = escolher_tema()
    print(f"Tema sorteado: {instrucao_tema}")

    esqueleto = gerar_esqueleto(instrucao_tema)
    print("Esqueleto e ângulo gerados. Escrevendo artigo completo...")

    corpo = gerar_artigo_completo(esqueleto)
    titulo = gerar_titulo(esqueleto)

    categoria = identificar_categoria(esqueleto)
    tags = CATEGORIAS_TAGS.get(categoria, ["games"]) + ["resenha", "documentario", "games"]
    tags = list(dict.fromkeys(tags))  # remove duplicatas mantendo a ordem

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"Esqueleto/tema do artigo: {esqueleto[:600]}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
    except Exception as e:
        print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
        palavra_chave = extrair_palavra_chave(esqueleto)
        img_url = buscar_imagem_openverse(palavra_chave)
        img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    cta = gerar_cta()

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">Artigo de caráter '
        'cultural, histórico e opinativo sobre games, com fins de entretenimento e nostalgia.</p>'
    )

    html_final = f"{img_html}{corpo}{cta}{aviso}"
    publicar_no_blogger(titulo, html_final, tags)
    marcar_tema_usado(instrucao_tema)
    print("Concluído com sucesso!")
