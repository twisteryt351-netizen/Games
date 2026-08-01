import os
import re
import json
import time
import html
import base64
import random
import urllib.parse
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
MODELO_IA = "llama-3.3-70b-versatile"

# --- GERACAO DE IMAGENS COM IA (Pollinations.ai) ---
# Usada apenas para a imagem ilustrativa do ARTIGO abaixo do jogo (nao para o jogo em si).
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # opcional
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

ARQUIVO_HISTORICO = "historico_jogos_html.txt"

# =====================================================================
# JOGOS ORIGINAIS (HTML5/JS puro, testados, auto-contidos, sem dependencia
# externa nenhuma). O robo troca apenas cores/titulo/flavor text a cada
# post - a LOGICA do jogo em si nunca muda, pra garantir que sempre funcione.
# =====================================================================

DINO_JS = "// ===== DINO RUNNER (auto-contido, teclado) =====\n(function () {\n  const canvas = document.getElementById('gameCanvas');\n  const ctx = canvas.getContext('2d');\n  const W = canvas.width, H = canvas.height;\n  const GROUND_Y = H - 40;\n\n  const player = { x: 60, y: GROUND_Y - 40, w: 34, h: 40, vy: 0, jumping: false };\n  const GRAVITY = 0.9;\n  const JUMP_FORCE = -15;\n\n  let obstacles = [];\n  let frame = 0;\n  let speed = 6;\n  let score = 0;\n  let best = parseInt(localStorage.getItem('dinoBest') || '0', 10) || 0;\n  let gameOver = false;\n  let started = false;\n\n  function reset() {\n    player.y = GROUND_Y - player.h;\n    player.vy = 0;\n    player.jumping = false;\n    obstacles = [];\n    frame = 0;\n    speed = 6;\n    score = 0;\n    gameOver = false;\n  }\n\n  function spawnObstacle() {\n    const h = 30 + Math.random() * 30;\n    obstacles.push({ x: W + 20, y: GROUND_Y - h, w: 20 + Math.random() * 15, h: h });\n  }\n\n  function jump() {\n    if (!started) { started = true; }\n    if (gameOver) { reset(); started = true; return; }\n    if (!player.jumping) {\n      player.vy = JUMP_FORCE;\n      player.jumping = true;\n    }\n  }\n\n  function update() {\n    if (!started || gameOver) return;\n    frame++;\n    if (frame % Math.max(40, 70 - Math.floor(score / 5)) === 0) spawnObstacle();\n\n    player.vy += GRAVITY;\n    player.y += player.vy;\n    if (player.y >= GROUND_Y - player.h) {\n      player.y = GROUND_Y - player.h;\n      player.vy = 0;\n      player.jumping = false;\n    }\n\n    obstacles.forEach(o => o.x -= speed);\n    obstacles = obstacles.filter(o => o.x + o.w > 0);\n\n    for (const o of obstacles) {\n      if (\n        player.x < o.x + o.w &&\n        player.x + player.w > o.x &&\n        player.y < o.y + o.h &&\n        player.y + player.h > o.y\n      ) {\n        gameOver = true;\n        if (score > best) {\n          best = score;\n          localStorage.setItem('dinoBest', String(best));\n        }\n      }\n    }\n\n    score += 1;\n    if (frame % 300 === 0) speed += 0.5;\n  }\n\n  function draw() {\n    ctx.clearRect(0, 0, W, H);\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#111';\n    ctx.fillRect(0, 0, W, H);\n\n    ctx.strokeStyle = '#888';\n    ctx.beginPath();\n    ctx.moveTo(0, GROUND_Y);\n    ctx.lineTo(W, GROUND_Y);\n    ctx.stroke();\n\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#4ade80';\n    ctx.fillRect(player.x, player.y, player.w, player.h);\n\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#f87171';\n    obstacles.forEach(o => ctx.fillRect(o.x, o.y, o.w, o.h));\n\n    ctx.fillStyle = '#e5e7eb';\n    ctx.font = '16px monospace';\n    ctx.fillText('Pontos: ' + score, 12, 24);\n    ctx.fillText('Recorde: ' + best, 12, 44);\n\n    if (!started) {\n      ctx.textAlign = 'center';\n      ctx.fillText('Pressione ESPA\u00c7O para come\u00e7ar', W / 2, H / 2);\n      ctx.textAlign = 'left';\n    } else if (gameOver) {\n      ctx.textAlign = 'center';\n      ctx.fillText('Fim de jogo! ESPA\u00c7O para tentar de novo', W / 2, H / 2);\n      ctx.textAlign = 'left';\n    }\n  }\n\n  function loop() {\n    update();\n    draw();\n    requestAnimationFrame(loop);\n  }\n\n  document.addEventListener('keydown', (e) => {\n    if (e.code === 'Space' || e.code === 'ArrowUp') {\n      e.preventDefault();\n      jump();\n    }\n  });\n  canvas.addEventListener('click', jump);\n\n  reset();\n  draw();\n  loop();\n})();\n"

SNAKE_JS = "// ===== SNAKE (auto-contido, teclado) =====\n(function () {\n  const canvas = document.getElementById('gameCanvas');\n  const ctx = canvas.getContext('2d');\n  const W = canvas.width, H = canvas.height;\n  const CELL = 20;\n  const COLS = Math.floor(W / CELL);\n  const ROWS = Math.floor(H / CELL);\n\n  let snake, dir, nextDir, food, score, best, gameOver, started, tickCount;\n  best = parseInt(localStorage.getItem('snakeBest') || '0', 10) || 0;\n\n  function randCell() {\n    return { x: Math.floor(Math.random() * COLS), y: Math.floor(Math.random() * ROWS) };\n  }\n\n  function placeFood() {\n    let f;\n    do {\n      f = randCell();\n    } while (snake.some(s => s.x === f.x && s.y === f.y));\n    food = f;\n  }\n\n  function reset() {\n    snake = [{ x: Math.floor(COLS / 2), y: Math.floor(ROWS / 2) }];\n    dir = { x: 1, y: 0 };\n    nextDir = { x: 1, y: 0 };\n    score = 0;\n    gameOver = false;\n    tickCount = 0;\n    placeFood();\n  }\n\n  function setDir(dx, dy) {\n    if (!started) { started = true; }\n    if (gameOver) { reset(); started = true; return; }\n    // impede virar 180 graus direto sobre o proprio corpo\n    if (dx === -dir.x && dy === -dir.y && snake.length > 1) return;\n    nextDir = { x: dx, y: dy };\n  }\n\n  function update() {\n    if (!started || gameOver) return;\n    tickCount++;\n    if (tickCount % 6 !== 0) return; // controla a velocidade do jogo\n\n    dir = nextDir;\n    const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };\n\n    if (head.x < 0 || head.x >= COLS || head.y < 0 || head.y >= ROWS) {\n      gameOver = true;\n      if (score > best) { best = score; localStorage.setItem('snakeBest', String(best)); }\n      return;\n    }\n    if (snake.some(s => s.x === head.x && s.y === head.y)) {\n      gameOver = true;\n      if (score > best) { best = score; localStorage.setItem('snakeBest', String(best)); }\n      return;\n    }\n\n    snake.unshift(head);\n    if (head.x === food.x && head.y === food.y) {\n      score += 1;\n      placeFood();\n    } else {\n      snake.pop();\n    }\n  }\n\n  function draw() {\n    ctx.clearRect(0, 0, W, H);\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#111';\n    ctx.fillRect(0, 0, W, H);\n\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#f87171';\n    ctx.fillRect(food.x * CELL, food.y * CELL, CELL - 2, CELL - 2);\n\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#4ade80';\n    snake.forEach(s => ctx.fillRect(s.x * CELL, s.y * CELL, CELL - 2, CELL - 2));\n\n    ctx.fillStyle = '#e5e7eb';\n    ctx.font = '16px monospace';\n    ctx.fillText('Pontos: ' + score, 12, 20);\n    ctx.fillText('Recorde: ' + best, 12, 40);\n\n    if (!started) {\n      ctx.textAlign = 'center';\n      ctx.fillText('Use as SETAS para come\u00e7ar', W / 2, H / 2);\n      ctx.textAlign = 'left';\n    } else if (gameOver) {\n      ctx.textAlign = 'center';\n      ctx.fillText('Fim de jogo! Pressione uma SETA para reiniciar', W / 2, H / 2);\n      ctx.textAlign = 'left';\n    }\n  }\n\n  function loop() {\n    update();\n    draw();\n    requestAnimationFrame(loop);\n  }\n\n  document.addEventListener('keydown', (e) => {\n    if (e.code === 'ArrowUp') { e.preventDefault(); setDir(0, -1); }\n    else if (e.code === 'ArrowDown') { e.preventDefault(); setDir(0, 1); }\n    else if (e.code === 'ArrowLeft') { e.preventDefault(); setDir(-1, 0); }\n    else if (e.code === 'ArrowRight') { e.preventDefault(); setDir(1, 0); }\n  });\n\n  // Suporte a toque (mobile): cria 4 botoes de direcao sobre o canvas\n  const touchWrap = document.getElementById('touchControls');\n  if (touchWrap) {\n    touchWrap.querySelectorAll('[data-dir]').forEach(btn => {\n      btn.addEventListener('click', () => {\n        const d = btn.getAttribute('data-dir');\n        if (d === 'up') setDir(0, -1);\n        else if (d === 'down') setDir(0, 1);\n        else if (d === 'left') setDir(-1, 0);\n        else if (d === 'right') setDir(1, 0);\n      });\n    });\n  }\n\n  reset();\n  draw();\n  loop();\n})();\n"

FLAPPY_JS = "// ===== FLAPPY CLONE (auto-contido, teclado) =====\n(function () {\n  const canvas = document.getElementById('gameCanvas');\n  const ctx = canvas.getContext('2d');\n  const W = canvas.width, H = canvas.height;\n\n  const bird = { x: 80, y: H / 2, r: 14, vy: 0 };\n  const GRAVITY = 0.5;\n  const FLAP = -8;\n  const GAP = 140;\n  const PIPE_W = 50;\n  const PIPE_SPEED = 3;\n\n  let pipes = [];\n  let frame = 0;\n  let score = 0;\n  let best = parseInt(localStorage.getItem('flappyBest') || '0', 10) || 0;\n  let gameOver = false;\n  let started = false;\n\n  function reset() {\n    bird.y = H / 2;\n    bird.vy = 0;\n    pipes = [];\n    frame = 0;\n    score = 0;\n    gameOver = false;\n  }\n\n  function spawnPipe() {\n    const margin = 40;\n    const top = margin + Math.random() * (H - GAP - margin * 2);\n    pipes.push({ x: W + PIPE_W, top: top, bottom: top + GAP, scored: false });\n  }\n\n  function flap() {\n    if (!started) { started = true; }\n    if (gameOver) { reset(); started = true; return; }\n    bird.vy = FLAP;\n  }\n\n  function update() {\n    if (!started || gameOver) return;\n    frame++;\n    if (frame % 90 === 0) spawnPipe();\n\n    bird.vy += GRAVITY;\n    bird.y += bird.vy;\n\n    pipes.forEach(p => p.x -= PIPE_SPEED);\n    pipes = pipes.filter(p => p.x + PIPE_W > -10);\n\n    if (bird.y - bird.r < 0 || bird.y + bird.r > H) {\n      gameOver = true;\n    }\n\n    for (const p of pipes) {\n      const hitX = bird.x + bird.r > p.x && bird.x - bird.r < p.x + PIPE_W;\n      const hitY = bird.y - bird.r < p.top || bird.y + bird.r > p.bottom;\n      if (hitX && hitY) gameOver = true;\n\n      if (!p.scored && p.x + PIPE_W < bird.x) {\n        p.scored = true;\n        score += 1;\n      }\n    }\n\n    if (gameOver && score > best) {\n      best = score;\n      localStorage.setItem('flappyBest', String(best));\n    }\n  }\n\n  function draw() {\n    ctx.clearRect(0, 0, W, H);\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#111';\n    ctx.fillRect(0, 0, W, H);\n\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#4ade80';\n    pipes.forEach(p => {\n      ctx.fillRect(p.x, 0, PIPE_W, p.top);\n      ctx.fillRect(p.x, p.bottom, PIPE_W, H - p.bottom);\n    });\n\n    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#facc15';\n    ctx.beginPath();\n    ctx.arc(bird.x, bird.y, bird.r, 0, Math.PI * 2);\n    ctx.fill();\n\n    ctx.fillStyle = '#e5e7eb';\n    ctx.font = '16px monospace';\n    ctx.fillText('Pontos: ' + score, 12, 24);\n    ctx.fillText('Recorde: ' + best, 12, 44);\n\n    if (!started) {\n      ctx.textAlign = 'center';\n      ctx.fillText('Pressione ESPA\u00c7O para come\u00e7ar', W / 2, H / 2);\n      ctx.textAlign = 'left';\n    } else if (gameOver) {\n      ctx.textAlign = 'center';\n      ctx.fillText('Fim de jogo! ESPA\u00c7O para tentar de novo', W / 2, H / 2);\n      ctx.textAlign = 'left';\n    }\n  }\n\n  function loop() {\n    update();\n    draw();\n    requestAnimationFrame(loop);\n  }\n\n  document.addEventListener('keydown', (e) => {\n    if (e.code === 'Space' || e.code === 'ArrowUp') {\n      e.preventDefault();\n      flap();\n    }\n  });\n  canvas.addEventListener('click', flap);\n\n  reset();\n  draw();\n  loop();\n})();\n"

JOGOS = {
    "dino": {
        "nome_tecnico": "corrida infinita com pulos (estilo dinossauro do Chrome)",
        "genero": "arcade de reflexo / corrida infinita",
        "controles": "ESPAÇO ou seta para CIMA para pular os obstáculos",
        "js": DINO_JS,
        "touch_controls_html": "",
    },
    "snake": {
        "nome_tecnico": "cobrinha clássica (Snake)",
        "genero": "arcade clássico de grade",
        "controles": "SETAS do teclado para mudar de direção e comer",
        "js": SNAKE_JS,
        "touch_controls_html": (
            '<div id="touchControls" class="touch-controls">'
            '<button data-dir="up" aria-label="Cima">▲</button>'
            '<div class="touch-row">'
            '<button data-dir="left" aria-label="Esquerda">◀</button>'
            '<button data-dir="right" aria-label="Direita">▶</button>'
            "</div>"
            '<button data-dir="down" aria-label="Baixo">▼</button>'
            "</div>"
        ),
    },
    "flappy": {
        "nome_tecnico": "voo com obstáculos (estilo passarinho que bate asas)",
        "genero": "arcade de reflexo / desvio de obstáculos",
        "controles": "ESPAÇO ou clique para bater asas e desviar dos canos",
        "js": FLAPPY_JS,
        "touch_controls_html": "",
    },
}


# --- ROTACAO: evita repetir o mesmo mini-game no dia seguinte ---
def escolher_jogo():
    ultimo = None
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            linhas = f.read().splitlines()
        if linhas:
            try:
                ultimo = json.loads(linhas[-1]).get("jogo_id")
            except Exception:
                ultimo = None
    candidatos = [k for k in JOGOS.keys() if k != ultimo] or list(JOGOS.keys())
    return random.choice(candidatos)


def marcar_jogo_usado(jogo_id, titulo_tema):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(json.dumps({"jogo_id": jogo_id, "titulo": titulo_tema}, ensure_ascii=False) + "\n")


# --- MONTAGEM DO HTML DO JOGO (auto-contido, embutido via iframe srcdoc) ---
def montar_html_jogo(jogo_info, titulo_tema, cor_primaria, cor_acento, cor_fundo, instrucao_extra):
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --primary: {cor_primaria};
    --accent: {cor_acento};
    --bg: {cor_fundo};
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0; height: 100%;
    background: var(--bg);
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    display: flex; align-items: center; justify-content: center;
  }}
  #gameWrap {{
    width: 100%; max-width: 820px; padding: 14px;
    display: flex; flex-direction: column; align-items: center; gap: 8px;
  }}
  h2 {{ color: var(--primary); margin: 4px 0; font-size: 18px; text-align: center; }}
  #gameCanvas {{
    width: 100%; max-width: 800px; height: auto; aspect-ratio: 800 / 300;
    background: var(--bg); border: 2px solid var(--primary); border-radius: 10px;
    touch-action: none;
  }}
  .info {{ color: #cbd5e1; font-size: 13px; text-align: center; max-width: 700px; }}
  .botoes {{ display: flex; gap: 10px; margin-top: 4px; }}
  .botoes button {{
    background: var(--primary); color: #0b0f1a; border: none; border-radius: 8px;
    padding: 8px 14px; font-weight: 700; cursor: pointer; font-size: 13px;
  }}
  .touch-controls {{ display: flex; flex-direction: column; align-items: center; gap: 4px; margin-top: 4px; }}
  .touch-row {{ display: flex; gap: 40px; }}
  .touch-controls button {{
    background: var(--accent); color: #0b0f1a; border: none; border-radius: 8px;
    width: 44px; height: 44px; font-size: 18px; cursor: pointer;
  }}
  @media (min-width: 700px) {{ .touch-controls {{ display: none; }} }}
</style>
</head>
<body>
  <div id="gameWrap">
    <h2>{html.escape(titulo_tema)}</h2>
    <canvas id="gameCanvas" width="800" height="300"></canvas>
    <p class="info">{html.escape(instrucao_extra)} — Controles: {html.escape(jogo_info['controles'])}</p>
    {jogo_info['touch_controls_html']}
    <div class="botoes">
      <button onclick="document.getElementById('gameWrap').requestFullscreen && document.getElementById('gameWrap').requestFullscreen()">⛶ Tela cheia</button>
    </div>
  </div>
  <script>
{jogo_info['js']}
  </script>
</body>
</html>"""


def montar_iframe_embed(jogo_info, titulo_tema, cor_primaria, cor_acento, cor_fundo, instrucao_extra):
    html_doc = montar_html_jogo(jogo_info, titulo_tema, cor_primaria, cor_acento, cor_fundo, instrucao_extra)
    srcdoc_escapado = html.escape(html_doc, quote=True)
    return (
        '<div style="max-width: 820px; margin: 0 auto;">'
        f'<iframe srcdoc="{srcdoc_escapado}" width="100%" height="460" '
        'style="border:0; border-radius: 14px; display:block; max-width:820px; margin:0 auto;" '
        'allowfullscreen loading="lazy" title="Jogo online"></iframe>'
        "</div><br />"
    )


# --- PIPELINE DE IMAGEM (Pollinations.ai + imgbb, com fallback Openverse) - usada so no ARTIGO ---
IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": palavra_chave, "license_type": "commercial", "page_size": 3, "mature": "false"},
            headers={"User-Agent": "RoboJogosHTML/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"⚠️ Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO


def gerar_imagem_pollinations(prompt, ratio="16:9"):
    dimensoes = {"16:9": (1280, 720), "1:1": (1024, 1024)}
    largura, altura = dimensoes.get(ratio, (1280, 720))
    try:
        prompt_codificado = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        params = {"width": largura, "height": altura, "model": "flux",
                  "seed": random.randint(1, 999999), "nologo": "true"}
        headers = {}
        if POLLINATIONS_TOKEN:
            headers["Authorization"] = f"Bearer {POLLINATIONS_TOKEN}"
        resposta = requests.get(url, params=params, headers=headers, timeout=120)
        resposta.raise_for_status()
        if "image" not in resposta.headers.get("Content-Type", ""):
            raise ValueError("Resposta nao parece ser uma imagem")
        return resposta.content
    except Exception as e:
        print(f"⚠️ Pollinations.ai falhou: {e}")
        return None


def hospedar_imagem(imagem_bytes, nome_arquivo="imagem.png"):
    if not IMGBB_API_KEY:
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
    except Exception as e:
        print(f"⚠️ Falha ao hospedar imagem: {e}")
    return None


def obter_imagem_artigo(prompt):
    try:
        imagem_bytes = gerar_imagem_pollinations(prompt, ratio="16:9")
        if imagem_bytes:
            url = hospedar_imagem(imagem_bytes)
            if url:
                return url
    except Exception as e:
        print(f"⚠️ Pipeline de imagem via IA falhou: {e}")
    return buscar_imagem_openverse("retro arcade game pixel art")


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return (
        '<table align="center" cellpadding="0" cellspacing="0" '
        'class="tr-caption-container" style="margin-left: auto; margin-right: auto;">'
        '<tbody><tr><td style="text-align: center;">'
        f'<img alt="{alt_title}" border="0" style="max-width: 100%; height: auto; border-radius: 8px;" '
        f'src="{url_img}" title="{alt_title}" /></td></tr></tbody></table><br />'
    )


def pedir_ia_groq(prompt, temperatura=0.7):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    texto = response.choices[0].message.content.strip()
    if texto.startswith("```json"):
        texto = texto[7:]
    elif texto.startswith("```"):
        texto = texto[3:]
    if texto.endswith("```"):
        texto = texto[:-3]
    return texto.strip()


def gerar_tema_visual(jogo_info):
    """Pede a IA um 'reskin' (titulo fantasia + paleta de cores + descricao) para o
    jogo de hoje. So muda aparencia/flavor - a logica do jogo permanece intacta."""
    prompt = f"""
Voce e um diretor de arte de jogos casuais. Hoje o mini-game do blog e do tipo:
"{jogo_info['nome_tecnico']}" (genero: {jogo_info['genero']}).

Crie um tema visual ORIGINAL e criativo para essa rodada (sem usar nomes de personagens ou
marcas registradas de terceiros - crie algo original). Responda APENAS com um JSON valido,
sem markdown, no formato exato:

{{
  "titulo_tema": "nome fantasia curto e chamativo em portugues para esse jogo hoje",
  "cor_primaria": "#RRGGBB",
  "cor_acento": "#RRGGBB",
  "cor_fundo": "#RRGGBB (escura, para contraste)",
  "descricao_curta": "uma frase curta descrevendo o personagem/tema em portugues"
}}
"""
    resposta = pedir_ia_groq(prompt, temperatura=0.9)
    try:
        dados = json.loads(resposta)
        for campo in ["titulo_tema", "cor_primaria", "cor_acento", "cor_fundo", "descricao_curta"]:
            if campo not in dados or not dados[campo]:
                raise ValueError(f"Campo ausente: {campo}")
        if not re.match(r"^#[0-9A-Fa-f]{6}$", dados["cor_primaria"]):
            raise ValueError("cor_primaria invalida")
        if not re.match(r"^#[0-9A-Fa-f]{6}$", dados["cor_acento"]):
            raise ValueError("cor_acento invalida")
        if not re.match(r"^#[0-9A-Fa-f]{6}$", dados["cor_fundo"]):
            raise ValueError("cor_fundo invalida")
        return dados
    except Exception as e:
        print(f"⚠️ Tema visual da IA invalido, usando padrao: {e}")
        return {
            "titulo_tema": "Corrida Arcade do Dia",
            "cor_primaria": "#4ade80",
            "cor_acento": "#f87171",
            "cor_fundo": "#0b0f1a",
            "descricao_curta": "Um desafio arcade rapido para testar seus reflexos.",
        }


def gerar_artigo_seo(jogo_info, tema):
    prompt = f"""
Voce e um redator especializado em games casuais, escrevendo para um blog que hospeda um
mini-game jogavel direto na pagina, com foco em SEO para ranquear no Google.

Jogo de hoje: "{tema['titulo_tema']}" - {tema['descricao_curta']}
Genero: {jogo_info['genero']} ({jogo_info['nome_tecnico']})
Controles: {jogo_info['controles']}

Escreva um artigo curto em portugues do Brasil sobre esse jogo, para publicar LOGO ABAIXO do
jogo embutido na pagina. O artigo deve ajudar o post a ranquear bem no Google para buscas
como "jogo online gratis", "jogar no navegador", etc, além de dar dicas reais para o jogador.

REGRAS DE FORMATO (HTML puro, sem Markdown):
1. Paragrafo de abertura convidando o leitor a jogar, mencionando que e gratis e roda direto
   no navegador sem precisar baixar nada.
2. Subtitulo <h2>Como Jogar</h2> explicando os controles de forma clara.
3. Subtitulo <h2>Dicas para Pontuar Mais</h2> com 3-4 dicas praticas e genericas para esse
   genero de jogo (reflexo, timing, ritmo - sem inventar mecanicas que o jogo nao tem).
4. Subtitulo <h2>A Historia por Tras desse Estilo de Jogo</h2> contextualizando brevemente a
   origem e popularidade desse genero de jogo arcade/casual ao longo dos anos (sem inventar
   fatos especificos que voce nao tenha certeza).
5. Insira 1 nota do autor leve e engraçada dentro de <blockquote>.
6. Termine convidando o leitor a comentar sua pontuacao e desafiar os amigos.
7. Tamanho: entre 350 e 600 palavras.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


def gerar_cta_compartilhar():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Zerou? Manda pra galera!</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Compartilhe com os amigos e vejam quem tira a maior pontuação!</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
        <a href="#" onclick="window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(document.title + ' - ' + window.location.href), '_blank'); return false;" style="background-color: #25d366; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">WhatsApp</a>
        <a href="#" onclick="window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #1877f2; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">Facebook</a>
        <a href="#" onclick="window.open('https://twitter.com/intent/tweet?url=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #000; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">X</a>
    </div>
</div>
"""


def identificar_tags(jogo_id, jogo_info):
    base = {
        "dino": ["corrida infinita", "jogo de reflexo"],
        "snake": ["jogo classico", "jogo de grade"],
        "flappy": ["jogo de desvio", "jogo de reflexo"],
    }.get(jogo_id, ["jogo arcade"])
    return base + ["jogo online", "jogo gratis", "jogar no navegador", "html5 game", "games"]


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
    blogger = build("blogger", "v3", credentials=creds)
    corpo_postagem = {"kind": "blogger#post", "title": titulo, "content": conteudo, "labels": tags}
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"🎮 Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("Escolhendo o mini-game do dia...")
    jogo_id = escolher_jogo()
    jogo_info = JOGOS[jogo_id]
    print(f"Jogo escolhido: {jogo_id} ({jogo_info['genero']})")

    tema = gerar_tema_visual(jogo_info)
    print(f"Tema de hoje: {tema['titulo_tema']}")

    embed_html = montar_iframe_embed(
        jogo_info,
        tema["titulo_tema"],
        tema["cor_primaria"],
        tema["cor_acento"],
        tema["cor_fundo"],
        tema["descricao_curta"],
    )

    artigo = gerar_artigo_seo(jogo_info, tema)

    try:
        prompt_img = (
            f"Vibrant colorful arcade game cover art, {jogo_info['genero']}, "
            f"{tema['descricao_curta']}, digital art, no text, high energy, playful"
        )
        img_url = obter_imagem_artigo(prompt_img)
        img_html = gerar_tabela_imagem_blogger(img_url, tema["titulo_tema"])
    except Exception as e:
        print(f"⚠️ Falha na imagem do artigo, seguindo sem ela: {e}")
        img_html = ""

    cta = gerar_cta_compartilhar()
    tags = identificar_tags(jogo_id, jogo_info)

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic; margin-top: 15px;">'
        "Jogo original, criado para rodar direto no navegador. Divirta-se!</p>"
    )

    html_final = f"{embed_html}{img_html}{artigo}{cta}{aviso}"
    publicar_no_blogger(f"{tema['titulo_tema']} - Jogo Online Grátis", html_final, tags)
    marcar_jogo_usado(jogo_id, tema["titulo_tema"])
    print("Concluído!")

