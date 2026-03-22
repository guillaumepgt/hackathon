const PROXY = 'http://localhost:8765';
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

let sessionId = null, autoTimer = null, currentGame = null, memMap = {}, curState = null;

// ── CONFIG JEUX ──────────────────────────────────────────────────────────────

const GAMES = [
    { id: 6,  name: 'Brouillard',  icon: '🌫', color: '#00d4ff', type: 'maze' },
    { id: 7,  name: 'Lave',        icon: '🔥', color: '#ff6b35', type: 'maze' },
    { id: 8,  name: 'Clé / Porte', icon: '🔑', color: '#d29922', type: 'maze' },
    { id: 9,  name: 'Lave + Clé',  icon: '💀', color: '#f85149', type: 'maze' },
    { id: 5,  name: 'Traffic',     icon: '🚗', color: '#00e676', type: 'obs'  },
    { id: 10, name: 'Moon Lander', icon: '🚀', color: '#c792ea', type: 'obs'  },
    { id: 2,  name: 'Voitures',    icon: '🏎', color: '#ffab00', type: 'obs'  },
];

const CELL_COLORS = {
    '#': '#1a2332', '.': '#0d1f33', '?': '#070b0f',
    'S': '#1f6feb', 'E': '#238636', 'L': '#f85149',
    'K': '#d29922', 'D': '#8b4000',
};

const LEGEND_ITEMS = [
    { cell: 'player', color: '#00d4ff', label: 'Joueur'     },
    { cell: 'E',      color: '#238636', label: 'Sortie'     },
    { cell: '?',      color: '#070b0f', label: 'Brouillard' },
    { cell: '#',      color: '#1a2332', label: 'Mur'        },
    { cell: 'L',      color: '#f85149', label: 'Lave'       },
    { cell: 'K',      color: '#d29922', label: 'Clé'        },
    { cell: 'D',      color: '#8b4000', label: 'Porte'      },
    { cell: 'S',      color: '#1f6feb', label: 'Départ'     },
];

const OBS_SCHEMA = ['altitude','vx','vy','dx_pad','fuel','sin_θ','cos_θ','ω','leg_L','leg_R'];

// ── INIT ─────────────────────────────────────────────────────────────────────

function buildGameList() {
    const el = document.getElementById('game-list');
    GAMES.forEach(g => {
        const btn = document.createElement('button');
        btn.className = 'game-btn';
        btn.id = 'gbtn-' + g.id;
        btn.innerHTML = `
      <span class="gid" style="background:${g.color}22;color:${g.color}">${g.id}</span>
      <span>${g.icon} ${g.name}</span>`;
        btn.onclick = () => selectGame(g);
        el.appendChild(btn);
    });
}

function buildLegend() {
    const el = document.getElementById('legend');
    el.innerHTML = LEGEND_ITEMS.map(li => `
    <div class="li">
      <div class="lsq" style="background:${li.color};${li.cell==='player'?'border-radius:50%':''}"></div>
      ${li.label}
    </div>`).join('');
}

function selectGame(g) {
    currentGame = g;
    document.querySelectorAll('.game-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('gbtn-' + g.id)?.classList.add('active');
    log('Jeu sélectionné : ' + g.icon + ' ' + g.name, 'info');
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#1e2d3d';
    ctx.font = 'bold 14px JetBrains Mono,monospace';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('Prêt — lance une partie', canvas.width/2, canvas.height/2);
}

// ── API ──────────────────────────────────────────────────────────────────────

async function api(path, method = 'POST', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(PROXY + path, opts);
    const text = await r.text();
    let j; try { j = JSON.parse(text); } catch(_) { throw new Error(text); }
    if (!r.ok) { const e = new Error(r.status); e.data = j; throw e; }
    return j;
}

// ── LOG ──────────────────────────────────────────────────────────────────────

function log(msg, type = '') {
    const el = document.getElementById('log');
    const line = document.createElement('div');
    line.className = 'log-line ' + type;
    line.textContent = new Date().toLocaleTimeString() + ' ' + msg;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
}

// ── DRAW ─────────────────────────────────────────────────────────────────────

function drawGrid(s) {
    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    if (!s?.grid) return;

    const rows = s.grid.length, cols = s.grid[0].length;
    const sz = Math.min(W / cols, H / rows);

    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            const cell = s.grid[y][x];
            ctx.fillStyle = CELL_COLORS[cell] || '#111';
            ctx.fillRect(x*sz+1, y*sz+1, sz-2, sz-2);
            if (cell && !['?', '.', '#', 'S'].includes(cell)) {
                ctx.fillStyle = '#ffffffcc';
                ctx.font = `bold ${Math.max(8, sz*.42)}px JetBrains Mono,monospace`;
                ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                ctx.fillText(cell, x*sz+sz/2, y*sz+sz/2);
            }
        }
    }

    if (s.player_pos) {
        const [px, py] = s.player_pos;
        ctx.beginPath();
        ctx.arc(px*sz+sz/2, py*sz+sz/2, sz*.32, 0, Math.PI*2);
        ctx.fillStyle = currentGame?.color || '#00d4ff'; ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke();
    }
}

function drawObs(s) {
    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    if (!s) return;

    const obs = s.observation || [];
    const lines = [];

    if (s.lane !== undefined) {
        lines.push('TRAFFIC RACING', '─────────────────');
        lines.push('Lane     : ' + s.lane);
        lines.push('Speed    : ' + (s.speed ?? '—'));
        lines.push('Progress : ' + (s.progress ?? '—') + ' / 130');
        if (s.lane_gaps) {
            Object.entries(s.lane_gaps).forEach(([ln, g]) => {
                lines.push(`Lane ${ln}: ahead=${g.ahead??'∞'}  behind=${g.behind??'∞'}`);
            });
        }
    } else if (obs.length > 0) {
        lines.push('OBSERVATION VECTOR', '─────────────────');
        obs.forEach((v, i) => {
            const name = (OBS_SCHEMA[i] || 'obs['+i+']').padEnd(10);
            const bar = '█'.repeat(Math.max(0, Math.round((v + 1) * 8)));
            lines.push(`${name} ${v.toFixed(4)}  ${bar}`);
        });
    } else {
        lines.push(JSON.stringify(s, null, 2));
    }

    ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    lines.forEach((line, i) => {
        if (i === 0) {
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 13px JetBrains Mono,monospace';
        } else if (line.startsWith('─')) {
            ctx.fillStyle = '#1e2d3d';
            ctx.font = '11px JetBrains Mono,monospace';
        } else {
            ctx.fillStyle = currentGame?.color || '#00d4ff';
            ctx.font = '11px JetBrains Mono,monospace';
        }
        ctx.fillText(line, 16, 16 + i * 18);
    });
}

function drawState(s) {
    if (!s) return;
    curState = s;
    if (s.grid) drawGrid(s);
    else drawObs(s);
    document.getElementById('s-steps').textContent = s.steps ?? s.step ?? '—';
}

// ── GAME CONTROL ─────────────────────────────────────────────────────────────

async function startGame() {
    if (!currentGame) { log('Sélectionne un jeu !', 'err'); return; }
    stopAuto(); memMap = {};
    log('Connexion jeu ' + currentGame.id + '...', 'info');
    try {
        const r = await api('/api/newgame/', 'POST', { idgame: currentGame.id });
        sessionId = r.gamesessionid;
        log('Session ' + sessionId + ' créée', 'ok');
        let s = r.state;
        if (!s) {
            const r2 = await api('/api/get_state/?gamesessionid=' + sessionId, 'GET');
            s = r2.state;
        }
        drawState(s);
        setSessionUI(sessionId, 'RUNNING');
        setControls(true);
    } catch(e) {
        if (e.message === '409' && e.data?.existing_session_id) {
            sessionId = e.data.existing_session_id;
            log('Session existante reprise : ' + sessionId, 'warn');
            setSessionUI(sessionId, 'RESUMED');
            setControls(true);
            try {
                const r2 = await api('/api/get_state/?gamesessionid=' + sessionId, 'GET');
                drawState(r2.state);
            } catch(_) {}
        } else {
            log('Erreur : ' + (e.data?.error || e.message), 'err');
        }
    }
}

async function stopGame() {
    stopAuto();
    if (!sessionId) return;
    try {
        await api('/api/stop_game/', 'POST', { gamesessionid: sessionId });
        log('Session ' + sessionId + ' stoppée', 'warn');
    } catch(_) {}
    sessionId = null;
    setSessionUI('—', 'OFFLINE');
    setControls(false);
}

async function act(action) {
    if (!sessionId) return;
    try {
        const r = await api('/api/act/', 'POST', { gamesessionid: sessionId, action });
        if (r.state) drawState(r.state);
        if (r.status === 'win') {
            log('VICTOIRE !', 'ok');
            document.getElementById('s-status').textContent = 'WIN';
            setControls(false); stopAuto(); sessionId = null;
        } else if (r.status === 'lose' || r.status === 'max_steps') {
            log('Défaite (' + r.status + ')', 'err');
            document.getElementById('s-status').textContent = 'LOSE';
            setControls(false); stopAuto(); sessionId = null;
        }
    } catch(e) {
        log('Act error : ' + (e.data?.error || e.message), 'err');
    }
}

// ── AUTO-PLAY ────────────────────────────────────────────────────────────────

function bfsAction(s) {
    if (!s?.grid) {
        const actions = ['accelerate','keep','left','right','brake','idle','main','stabilize'];
        return actions[Math.floor(Math.random() * 3)];
    }

    for (let y = 0; y < s.grid.length; y++)
        for (let x = 0; x < s.grid[y].length; x++) {
            const ch = s.grid[y][x];
            if (ch && ch !== '?') memMap[x + ',' + y] = ch;
        }

    const [sx, sy] = s.player_pos;
    const exit = s.exit_pos;
    const has_key = s.has_key ?? false;
    const mv = [['up',0,-1],['down',0,1],['left',-1,0],['right',1,0]];
    const par = { [sx+','+sy]: null }, q = [[sx, sy]];
    let found = null;

    outer: while (q.length) {
        const [cx, cy] = q.shift();
        for (const [name, dx, dy] of mv) {
            const nx = cx+dx, ny = cy+dy, k = nx+','+ny;
            if (k in par) continue;
            if (exit && nx === exit[0] && ny === exit[1]) { par[k] = [cx,cy,name]; found = k; break outer; }
            const ch = memMap[k];
            if (!ch)                      { par[k] = [cx,cy,name]; found = k; break outer; }
            if (ch === '#' || ch === 'L') continue;
            if (ch === 'D' && !has_key)   continue;
            par[k] = [cx,cy,name]; q.push([nx,ny]);
        }
    }

    if (!found) return mv[Math.floor(Math.random() * 4)][0];
    let cur = found;
    while (par[cur] && par[par[cur][0]+','+par[cur][1]] !== null)
        cur = par[cur][0] + ',' + par[cur][1];
    return par[cur]?.[2] ?? 'up';
}

function toggleAuto() {
    if (autoTimer) {
        stopAuto();
    } else {
        document.getElementById('btn-auto').textContent = '⏸ Stop auto';
        const speed = +document.getElementById('speed').value;
        autoTimer = setInterval(async () => {
            if (!curState || !sessionId) { stopAuto(); return; }
            await act(bfsAction(curState));
        }, speed);
    }
}

function stopAuto() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    document.getElementById('btn-auto').textContent = '⚡ Auto-play';
}

// ── UI HELPERS ───────────────────────────────────────────────────────────────

function setControls(on) {
    ['btn-stop','btn-auto','k-up','k-down','k-left','k-right']
        .forEach(id => document.getElementById(id).disabled = !on);
}

function setSessionUI(id, status) {
    document.getElementById('s-id').textContent = id;
    document.getElementById('s-status').textContent = status;
}

// ── EVENTS ───────────────────────────────────────────────────────────────────

document.getElementById('speed').addEventListener('input', e => {
    document.getElementById('speed-val').textContent = e.target.value + 'ms';
    if (autoTimer) { stopAuto(); toggleAuto(); }
});

document.addEventListener('keydown', e => {
    if (!sessionId) return;
    const m = { ArrowUp:'up', ArrowDown:'down', ArrowLeft:'left', ArrowRight:'right' };
    if (m[e.key]) { e.preventDefault(); act(m[e.key]); }
});

// ── BOOT ─────────────────────────────────────────────────────────────────────

buildGameList();
buildLegend();
selectGame(GAMES[0]);