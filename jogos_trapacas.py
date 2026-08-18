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

# --- Tags/labels do Blogger por categoria (a IA escolhe a categoria certa) ---
CATEGORIAS_TAGS = {
    "cheat-code": ["cheat code", "codigo secreto", "macete"],
    "move-input": ["combo", "golpe especial", "luta"],
    "secret-unlock": ["segredo", "desbloqueavel", "easter egg"],
    "detonado": ["detonado", "guia", "walkthrough"],
    "puzzle": ["puzzle", "quebra-cabeca", "guia"],
    "retro": ["retro games", "nostalgia", "games classicos"],
    "moderno": ["games", "dicas", "truques"],
}

# --- BASE DE MACETES, CHEATS, COMBOS E DICAS DE DETONADO (fatos reais e documentados) ---
# Fornecer o macete pronto para a IA evita que ela invente codigos/comandos incorretos,
# igual fazemos no modo retro do robo de novidades.
ARQUIVO_HISTORICO = "historico_jogos_trapacas.txt"

# --- BASE DE MACETES, CHEATS, COMBOS E DICAS DE DETONADO (fatos reais e documentados) ---
# Fornecer o macete pronto para a IA evita que ela invente codigos/comandos incorretos.
MACETES = [
    {"jogo": "Contra", "plataforma": "NES", "tipo": "cheat-code",
     "macete": "o famoso Codigo Konami (Cima, Cima, Baixo, Baixo, Esquerda, Direita, Esquerda, Direita, B, A, Start) da 30 vidas em vez de 3, e se tornou o cheat code mais celebre da historia dos games"},
    {"jogo": "Grand Theft Auto: San Andreas", "plataforma": "PS2/PC", "tipo": "cheat-code",
     "macete": "digitar HESOYAM no teclado (ou o codigo equivalente no controle) restaura vida, armadura e da dinheiro instantaneamente"},
    {"jogo": "Grand Theft Auto: Vice City", "plataforma": "PS2/PC", "tipo": "cheat-code",
     "macete": "o codigo THUGSTOOLS entrega ao jogador um arsenal completo de armas basicas instantaneamente"},
    {"jogo": "Street Fighter II", "plataforma": "Arcade/SNES", "tipo": "move-input",
     "macete": "o Hadouken de Ryu e Ken se executa com o comando classico: Baixo, Diagonal-baixo-frente, Frente + Soco"},
    {"jogo": "Street Fighter II", "plataforma": "Arcade/SNES", "tipo": "move-input",
     "macete": "o Shoryuken (dragon punch) se executa com Frente, Baixo, Diagonal-baixo-frente + Soco"},
    {"jogo": "Mortal Kombat II", "plataforma": "Arcade", "tipo": "move-input",
     "macete": "a Fatality de Liu Kang (transformacao em dragao) se executa agachando e girando o direcional em 360 graus"},
    {"jogo": "Mortal Kombat", "plataforma": "Arcade", "tipo": "move-input",
     "macete": "o golpe icônico 'Get Over Here' do Scorpion (arpao/lança) se executa com Baixo, Frente + Soco, puxando o oponente para perto"},
    {"jogo": "Dragon Ball Z: Super Butouden 2", "plataforma": "SNES", "tipo": "secret-unlock",
     "macete": "segurando L+R no controle 2 durante a tela de titulo/inicio da partida, o jogo roda em velocidade mais rapida"},
    {"jogo": "Sonic the Hedgehog 2", "plataforma": "Mega Drive", "tipo": "secret-unlock",
     "macete": "na tela de titulo, segure Cima e pressione A, C, para cima, C, para baixo, C, para esquerda, C, para direita, C, para acessar o famoso menu de selecao de fase (Level Select)"},
    {"jogo": "Age of Empires II", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "digitar 'HOW DO YOU TURN THIS ON' na caixa de chat durante a partida libera todas as tecnologias e faz o jogador enxergar o mapa inteiro"},
    {"jogo": "Age of Empires II", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "o codigo de chat 'ROCK ON' concede 1000 unidades de pedra instantaneamente"},
    {"jogo": "Command & Conquer: Red Alert", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "existe um modo de jogador extra escondido acessivel via linha de comando, alem de codigos de mapa completo bem documentados pela comunidade da epoca"},
    {"jogo": "GoldenEye 007", "plataforma": "Nintendo 64", "tipo": "secret-unlock",
     "macete": "completar certas fases dentro do tempo limite ('Agent' ou dificuldades maiores) desbloqueia cheats extras como mira automatica e modo Paintball"},
    {"jogo": "The Legend of Zelda: Ocarina of Time", "plataforma": "Nintendo 64", "tipo": "detonado",
     "macete": "a musica 'Song of Storms', tocada com a ocarina no padrao Baixo, Direcional-direita, Cima, Baixo, Direcional-direita, Cima, e essencial para avancar em varios pontos do jogo, incluindo fazer o moinho girar"},
    {"jogo": "Resident Evil", "plataforma": "PlayStation", "tipo": "detonado",
     "macete": "o classico puzzle do piano na mansao exige tocar as teclas indicadas pela partitura encontrada para revelar uma passagem secreta"},
    {"jogo": "Pokemon Vermelho/Azul", "plataforma": "Game Boy", "tipo": "secret-unlock",
     "macete": "o bug do MissingNo., acessado atraves de uma sequencia especifica envolvendo o Velho Homem de Cinnabar Island e o Nadador de Cinnabar Coast, duplicava o sexto item do inventario"},
    {"jogo": "Doom", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "o codigo IDDQD ativa o modo deus (invencibilidade), e o IDKFA da todas as armas, municao e chaves"},
    {"jogo": "The Sims", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "abrir o console com Ctrl+Shift+C e digitar 'motherlode' (ou 'rosebud' nos jogos mais antigos) concede uma boa quantia de dinheiro simoleons"},
    {"jogo": "Minecraft", "plataforma": "PC/Console", "tipo": "detonado",
     "macete": "para encontrar diamantes de forma eficiente na versao classica, a estrategia consagrada era escavar em 'strip mining' na camada 11 (Y=11), a altura ideal para maximizar as chances de encontrar o minerio"},
    {"jogo": "Super Mario 64", "plataforma": "Nintendo 64", "tipo": "secret-unlock",
     "macete": "e possivel completar o jogo com apenas 70 estrelas coletadas para enfrentar Bowser na fase final, sem precisar das 120 estrelas completas"},
    {"jogo": "Elden Ring", "plataforma": "PC/Console", "tipo": "detonado",
     "macete": "o boss Margit pode ser enfraquecido com o item Pote Fumegante de Espinho de Carro de Guerra (Stormcaller ou similares) e Torrent (o cavalo) ajuda a driblar alguns de seus combos mais dificeis"},
    {"jogo": "Dark Souls", "plataforma": "PC/Console", "tipo": "detonado",
     "macete": "levar o anel Covetous Silver Serpent Ring aumenta o drop de almas, e farmar os Titanite Demons e uma estrategia classica para upar equipamentos com seguranca"},
    {"jogo": "Cave Story", "plataforma": "PC", "tipo": "secret-unlock",
     "macete": "e possivel obter o final verdadeiro do jogo evitando pegar a Machine Gun no Grasstown e completando a Sacred Cave, o que altera todo o terceiro ato"},
    {"jogo": "Chrono Trigger", "plataforma": "SNES", "tipo": "secret-unlock",
     "macete": "o jogo possui multiplos finais alternativos desbloqueaveis dependendo de quando o jogador decide enfrentar o chefe final Lavos ao longo da campanha, incentivando novas jogadas (New Game+)"},
    {"jogo": "GTA V", "plataforma": "PS4/PS5/Xbox/PC", "tipo": "cheat-code",
     "macete": "no controle, o codigo Cima, Cima, Baixo, Baixo, Esquerda, Direita, Esquerda, Direita, X/Quadrado, Circulo/B, L1/LB, R1/RB (varia por versao) invoca um paraquedas instantaneamente"},
    {"jogo": "The Legend of Zelda: Breath of the Wild", "plataforma": "Switch", "tipo": "detonado",
     "macete": "cozinhar refeicoes combinando ingredientes com efeitos iguais (ex: varios itens de resistencia ao frio) multiplica a duracao do efeito, uma mecanica pouco explicada mas essencial para sobreviver em areas extremas"},
    {"jogo": "Undertale", "plataforma": "PC", "tipo": "secret-unlock",
     "macete": "para conseguir a rota Pacifista Verdadeira e preciso nao matar nenhum inimigo E completar eventos opcionais especificos com personagens secundarios antes de enfrentar o Julgamento Final"},
    {"jogo": "Banjo-Kazooie", "plataforma": "Nintendo 64", "tipo": "secret-unlock",
     "macete": "o jogo esconde um code final ('Stop N Swop') que permitiria itens transferiveis para a sequencia, um dos easter eggs mais lendarios e discutidos da era N64"},
    {"jogo": "World of Warcraft", "plataforma": "PC", "tipo": "detonado",
     "macete": "farmar reputacao com faccoes especificas antes de certas expansoes e uma estrategia classica veterana para desbloquear receitas, monturas e equipamentos exclusivos mais cedo"},
    {"jogo": "Half-Life 2", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "com o console de desenvolvedor ativado, o comando 'god' ativa invencibilidade e 'noclip' permite atravessar paredes livremente"},
    {"jogo": "Diablo II", "plataforma": "PC", "tipo": "detonado",
     "macete": "o famoso 'Pindleskin run', matar repetidamente o chefe secundario Pindleskin, era uma das rotas de farm de itens raros mais eficientes da comunidade"},
    {"jogo": "Tekken 3", "plataforma": "PlayStation", "tipo": "secret-unlock",
     "macete": "completar o modo Arcade com certos personagens sem usar continues desbloqueava personagens secretos como Dr. Bosconovitch e Gon"},
    {"jogo": "Banco Imobiliario", "plataforma": "Tabuleiro", "tipo": "detonado",
     "macete": "uma estrategia classica de tabuleiro e priorizar comprar as propriedades laranja e vermelha, as mais visitadas estatisticamente por quem sai da prisao, maximizando o retorno de alugueis"},
    {"jogo": "War", "plataforma": "Tabuleiro", "tipo": "detonado",
     "macete": "controlar continentes inteiros (como a Oceania, com poucos territorios de fronteira) garante bonus de exercito por turno, uma das estrategias mais consagradas do jogo"},
    {"jogo": "Xadrez", "plataforma": "Tabuleiro", "tipo": "detonado",
     "macete": "a abertura Italiana e uma das mais estudadas e recomendadas para iniciantes, priorizando controle do centro do tabuleiro e desenvolvimento rapido das pecas"},
    {"jogo": "Magic: The Gathering", "plataforma": "Card Game", "tipo": "detonado",
     "macete": "a 'curva de mana' (distribuir os custos das cartas do deck de forma equilibrada) e um dos fundamentos mais importantes para construir um deck competitivo"},
    {"jogo": "Pokemon Trading Card Game", "plataforma": "Card Game", "tipo": "detonado",
     "macete": "manter uma proporcao equilibrada entre cartas de Pokemon, Energia e Treinador (uma regra classica e cerca de 60% Pokemon/Treinador para 40% Energia) e a base de decks solidos"},
    {"jogo": "Dungeons & Dragons", "plataforma": "RPG de Mesa", "tipo": "detonado",
     "macete": "a regra da 'vantagem' (rolar dois dados de 20 lados e usar o maior resultado) e uma mecanica central introduzida na 5a edicao para simplificar bonus situacionais"},
    {"jogo": "Angry Birds", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "mirar para acertar estruturas de sustentacao na base das construcoes costuma causar mais dano em cadeia do que atirar direto nos porcos"},
    {"jogo": "Candy Crush Saga", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "combinar um doce listrado com um envolto em embrulho (wrapped candy) cria uma explosao tripla que limpa uma area enorme do tabuleiro"},
    {"jogo": "Pokemon GO", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "arremessar a Pokebola com um 'Curveball' (girando o dedo antes de soltar) concede XP bonus e aumenta a chance de captura"},
    {"jogo": "Free Fire", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "aterrissar em pontos menos populares do mapa e priorizar looting antes de entrar em confronto e uma estrategia classica para sobreviver mais tempo em battle royale"},
    {"jogo": "Duck Hunt", "plataforma": "NES", "tipo": "secret-unlock",
     "macete": "usando a Zapper (pistola de luz), apontar bem proximo a tela aumenta drasticamente a taxa de acerto, um truque conhecido por jogadores da epoca"},
    {"jogo": "Mega Man 2", "plataforma": "NES", "tipo": "detonado",
     "macete": "a ordem classica recomendada para enfrentar os chefes explora as fraquezas em cadeia entre as armas roubadas, por exemplo usando o Metal Blade contra varios chefes por sua alta versatilidade"},
    {"jogo": "Castlevania", "plataforma": "NES", "tipo": "cheat-code",
     "macete": "na tela de selecao de dificuldade, o codigo Cima, Cima, Baixo, Baixo, Esquerda, Direita, Esquerda, Direita, B, A permite comecar direto no estagio de escolha do jogador"},
    {"jogo": "Metal Gear Solid", "plataforma": "PlayStation", "tipo": "secret-unlock",
     "macete": "para vencer o chefe Psycho Mantis, e preciso literalmente trocar o controle da porta 1 para a porta 2 do PlayStation, pois o personagem 'le a mente' do jogador atraves do controle"},
]


def macete_ja_usado(macete):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    chave = f"{macete['jogo']}|{macete['macete'][:40]}"
    return chave in linhas[-40:]


def marcar_macete_usado(macete):
    chave = f"{macete['jogo']}|{macete['macete'][:40]}"
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(chave + "\n")


def escolher_macete():
    disponiveis = [m for m in MACETES if not macete_ja_usado(m)]
    if not disponiveis:
        disponiveis = MACETES
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


def extrair_palavra_chave(macete):
    prompt = (
        f"Jogo: '{macete['jogo']}' ({macete['plataforma']}). De apenas UMA palavra-chave em "
        f"ingles que descreva visualmente esse jogo/genero (ex: 'retro console', 'fighting game', "
        f"'board game', 'arcade cabinet'). Responda so a palavra."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(macete):
    categorias_validas = list(CATEGORIAS_TAGS.keys())
    prompt = (
        f"Tipo do macete: '{macete['tipo']}'. Jogo: '{macete['jogo']}' ({macete['plataforma']}). "
        f"Escolha a categoria mais adequada entre: {', '.join(categorias_validas)}. "
        f"Responda APENAS com a palavra da categoria."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return macete["tipo"] if macete["tipo"] in categorias_validas else "moderno"


def gerar_titulo(macete):
    prompt = (
        f"Jogo: {macete['jogo']} ({macete['plataforma']})\n"
        f"Macete/dica: {macete['macete']}\n\n"
        f"Crie um titulo chamativo, otimizado para SEO, em portugues do Brasil, sem aspas, "
        f"para um post de blog sobre esse macete/cheat/dica de jogo. Use palavras como "
        f"'macete', 'segredo', 'como fazer', 'truque' ou similar para atrair cliques de "
        f"quem busca esse tipo de conteudo. Responda apenas o titulo, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo(macete):
    prompt = f"""
Voce e um redator especializado em macetes, cheats, combos e detonados de games em todas as
suas formas (PC, console, mobile, arcade, tabuleiro, RPG de mesa, card games), para um blog de
fas muito engajado e voltado para ajudar o jogador. Escreva com qualidade alta, capriche de
verdade, e construa comunidade com o leitor.

O macete de hoje (fato real e confirmado - NAO mude os comandos/codigos nem invente outros
alem deste, use APENAS este como ancora factual e desenvolva o artigo em torno dele):

Jogo: {macete['jogo']} ({macete['plataforma']})
Tipo: {macete['tipo']}
Macete/dica: {macete['macete']}

REGRAS IMPORTANTES:
- Explique o macete de forma clara e didatica, passo a passo, reafirmando o comando/codigo
  exatamente como fornecido acima (nao altere nem invente variacoes que voce nao tenha certeza).
- EXPANDA com contexto real e relevante: por que esse macete existe (bug, recurso intencional
  dos desenvolvedores, tradicao da comunidade), historia do jogo, curiosidades de bastidores
  amplamente conhecidas, e por que os jogadores adoram esse tipo de segredo.
- NAO invente fatos especificos (datas, numeros, nomes) que voce nao tenha certeza.
- NAO seja repetitivo: cada paragrafo traz informacao nova.
- Tamanho: entre 500 e 900 palavras.

REGRAS DE FORMATO (HTML puro, sem Markdown):
1. Paragrafo de abertura envolvente que gera curiosidade sobre o macete.
2. Um subtitulo <h2> com o passo a passo claro de como executar o macete/cheat.
3. NO MINIMO 2 outros subtitulos <h2> (ex: contexto/historia do jogo, curiosidades sobre o
   macete, por que ele funciona).
4. Insira 2 notas do autor engracadas e leves dentro de <blockquote>, com comentarios de fa
   gamer (nunca debochado ou ofensivo).
5. Termine convidando o leitor a comentar outros macetes que conhece desse ou de outros jogos.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


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
    print("Sorteando macete/cheat/dica de games do dia...")
    macete = escolher_macete()
    print(f"Macete escolhido: {macete['jogo']} ({macete['plataforma']}) - {macete['macete'][:80]}...")

    try:
        categoria = identificar_categoria(macete)
        tags = CATEGORIAS_TAGS.get(categoria, ["games"]) + [macete["jogo"], macete["plataforma"]]
        tags = list(dict.fromkeys(tags))  # remove duplicatas mantendo a ordem

        titulo = gerar_titulo(macete)
        corpo = gerar_artigo(macete)

        try:
            galeria, secoes_brutas = montar_galeria_ia(
                titulo,
                corpo,
                minimo=QTD_MIN_IMAGENS,
                maximo=QTD_MAX_IMAGENS,
                contexto_extra=f"Jogo: {macete['jogo']} ({macete['plataforma']}). Macete: {macete['macete']}",
            )
            img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
            corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
            print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
        except Exception as e:
            print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
            palavra_chave = extrair_palavra_chave(macete)
            img_url = buscar_imagem_openverse(palavra_chave)
            img_html = gerar_tabela_imagem_blogger(img_url, titulo)

        cta = gerar_cta()

        aviso = (
            '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
            '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
            'Macetes e cheats fazem parte da cultura dos games desde sempre - use com moderacao '
            'para nao estragar a graca da primeira jogatina!</p>'
        )

        html_final = f"{img_html}{corpo}{cta}{aviso}"
        publicar_no_blogger(titulo, html_final, tags)
        marcar_macete_usado(macete)
        print("Concluido!")
    except Exception as e:
        print(f"Erro durante geracao/publicacao: {e}")
