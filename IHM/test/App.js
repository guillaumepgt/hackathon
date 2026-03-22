const PROXY = 'http://localhost:8765';
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

let sessionId = null, autoTimer = null, currentGame = null, memMap = {}, curState = null;

const GAMES = [
    { id:1,  name:'Tic-Tac-Toe',    icon:'⭕', color:'#c8d6e5', type:'ttt'     },
    { id:2,  name:'Car Racing',     icon:'🏎', color:'#ffab00', type:'car'     },
    { id:3,  name:'Snake',          icon:'🐍', color:'#00e676', type:'snake'   },
    { id:4,  name:'Rush Hour',      icon:'🚗', color:'#ff6b35', type:'rush'    },
    { id:5,  name:'Traffic Racing', icon:'🛣', color:'#00d4ff', type:'traffic' },
    { id:6,  name:'Fog Maze',       icon:'🌫', color:'#9c7bea', type:'maze'    },
    { id:7,  name:'Lava Maze',      icon:'🔥', color:'#ff6b35', type:'maze'    },
    { id:8,  name:'Key & Door',     icon:'🔑', color:'#d29922', type:'maze'    },
    { id:9,  name:'Lava + Key',     icon:'💀', color:'#f85149', type:'maze'    },
    { id:10, name:'Moon Lander',    icon:'🚀', color:'#c792ea', type:'lander'  },
];

const CELL_COLORS = {
    '#':'#1a2332', '.':'#0d1f33', '?':'#070b0f',
    'S':'#1f6feb', 'E':'#238636', 'L':'#f85149', 'K':'#d29922', 'D':'#8b4000',
};

const LEGEND_ITEMS = [
    { color:'#00d4ff', label:'Joueur',     round:true },
    { color:'#238636', label:'Sortie'      },
    { color:'#070b0f', label:'Brouillard'  },
    { color:'#1a2332', label:'Mur'         },
    { color:'#f85149', label:'Lave'        },
    { color:'#d29922', label:'Clé'         },
    { color:'#8b4000', label:'Porte'       },
    { color:'#1f6feb', label:'Départ'      },
];

const RUSH_COLORS = [
    '#e53935','#1e88e5','#43a047','#8e24aa','#fb8c00','#00acc1',
    '#6d4c41','#546e7a','#c0ca33','#f06292','#26a69a','#ff7043'
];

// ── BOOT : lit le paramètre ?id= dans l'URL ───────────────────────────────────

function boot() {
    const params = new URLSearchParams(location.search);
    const id = parseInt(params.get('id'));
    const game = GAMES.find(g => g.id === id);
    if (!game) { location.href = 'index.html'; return; }
    currentGame = game;

    // Titre de la page
    const title = document.getElementById('page-title');
    if (title) title.innerHTML = `${game.icon} <span style="color:${game.color}">${game.name}</span>`;
    document.title = `Hackathon 2026 — ${game.name}`;

    buildLegend();
    clearCanvas();
}

function buildLegend() {
    const el = document.getElementById('legend');
    if (!el) return;
    el.innerHTML = LEGEND_ITEMS.map(li =>
        `<div class="li"><div class="lsq" style="background:${li.color};${li.round?'border-radius:50%':''}"></div>${li.label}</div>`
    ).join('');
}

function clearCanvas() {
    const W=canvas.width, H=canvas.height;
    ctx.fillStyle='#000'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#1e2d3d'; ctx.font='bold 14px JetBrains Mono,monospace';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText('Lance une partie', W/2, H/2);
}

// ── API ──────────────────────────────────────────────────────────────────────

async function api(path, method='POST', body=null) {
    const opts={method, headers:{'Content-Type':'application/json'}};
    if (body) opts.body=JSON.stringify(body);
    const r=await fetch(PROXY+path, opts);
    const text=await r.text();
    let j; try{j=JSON.parse(text);}catch(_){throw new Error(text);}
    if (!r.ok){const e=new Error(r.status);e.data=j;throw e;}
    return j;
}

function log(msg, type='') {
    const el=document.getElementById('log');
    const line=document.createElement('div');
    line.className='log-line '+type;
    line.textContent=new Date().toLocaleTimeString()+' '+msg;
    el.appendChild(line);
    el.scrollTop=el.scrollHeight;
}

// ── DRAW DISPATCH ─────────────────────────────────────────────────────────────

function drawState(s) {
    if (!s) return;
    curState=s;
    document.getElementById('s-steps').textContent=s.steps??s.step??s.moves??'—';
    const t=currentGame?.type;
    if      (t==='ttt')     drawTTT(s);
    else if (t==='car')     drawCar(s);
    else if (t==='snake')   drawSnake(s);
    else if (t==='rush')    drawRush(s);
    else if (t==='traffic') drawTraffic(s);
    else if (t==='maze')    drawMaze(s);
    else if (t==='lander')  drawLander(s);
}

// ── JEU 1 ────────────────────────────────────────────────────────────────────

function drawTTT(s) {
    const W=canvas.width,H=canvas.height;
    ctx.fillStyle='#f5f5f0'; ctx.fillRect(0,0,W,H);
    const board=s.board, sz=Math.min(W,H)*0.78, ox=(W-sz)/2, oy=(H-sz)/2, cell=sz/3;
    ctx.strokeStyle='#333'; ctx.lineWidth=3;
    for (let i=1;i<3;i++){
        ctx.beginPath();ctx.moveTo(ox+i*cell,oy);ctx.lineTo(ox+i*cell,oy+sz);ctx.stroke();
        ctx.beginPath();ctx.moveTo(ox,oy+i*cell);ctx.lineTo(ox+sz,oy+i*cell);ctx.stroke();
    }
    ctx.font=`bold ${cell*.55}px JetBrains Mono,monospace`;
    ctx.textAlign='center'; ctx.textBaseline='middle';
    for (let r=0;r<3;r++) for (let c=0;c<3;c++){
        const v=board[r][c]; if(!v) continue;
        ctx.fillStyle=v==='X'?'#1a1a1a':'#cc2200';
        ctx.fillText(v, ox+c*cell+cell/2, oy+r*cell+cell/2);
    }
    ctx.fillStyle='#666'; ctx.font='13px JetBrains Mono,monospace';
    ctx.fillText('Tour : '+(s.current_player||'—'), W/2, oy+sz+22);
}

canvas.addEventListener('click', e=>{
    if (currentGame?.type!=='ttt'||!sessionId) return;
    const rect=canvas.getBoundingClientRect();
    const mx=(e.clientX-rect.left)*(canvas.width/rect.width);
    const my=(e.clientY-rect.top)*(canvas.height/rect.height);
    const W=canvas.width,H=canvas.height,sz=Math.min(W,H)*0.78;
    const ox=(W-sz)/2,oy=(H-sz)/2,cell=sz/3;
    const c=Math.floor((mx-ox)/cell),r=Math.floor((my-oy)/cell);
    if (r>=0&&r<3&&c>=0&&c<3) act(''+r+c);
});

// ── JEU 2 ────────────────────────────────────────────────────────────────────

function drawCar(s) {
    const W=canvas.width,H=canvas.height;
    ctx.fillStyle='#3a7d44'; ctx.fillRect(0,0,W,H);
    const roadX=W*0.12,roadW=W*0.76,laneW=roadW/3;
    ctx.fillStyle='#555'; ctx.fillRect(roadX,0,roadW,H);
    ctx.strokeStyle='#fff'; ctx.lineWidth=3; ctx.setLineDash([20,20]);
    for (let i=1;i<3;i++){ctx.beginPath();ctx.moveTo(roadX+i*laneW,0);ctx.lineTo(roadX+i*laneW,H);ctx.stroke();}
    ctx.setLineDash([]);
    const playerLane=s.lane??1,playerPos=s.position??0,RANGE=15;
    (s.upcoming_obstacles??[]).forEach(ob=>{
        const dist=ob.step-playerPos; if(dist<0||dist>RANGE) return;
        const px=roadX+ob.lane*laneW+laneW/2,py=H*0.9-(dist/RANGE)*H*0.8;
        const ow=laneW*0.7,oh=H*0.06;
        ctx.fillStyle='#cc2200'; ctx.fillRect(px-ow/2,py-oh/2,ow,oh);
        ctx.fillStyle='#ffcc00';
        for (let i=0;i<5;i+=2) ctx.fillRect(px-ow/2+i*(ow/5),py-oh/2,ow/5,oh);
    });
    const cx=roadX+playerLane*laneW+laneW/2,cy=H*0.85,cw=laneW*0.35,ch=H*0.07;
    ctx.fillStyle='#2196f3'; ctx.beginPath(); ctx.roundRect(cx-cw/2,cy-ch/2,cw,ch,4); ctx.fill();
    ctx.fillStyle='#90caf9'; ctx.fillRect(cx-cw/3,cy-ch/2+2,cw*2/3,ch*0.3);
    ctx.fillStyle='#000a'; ctx.fillRect(5,5,140,28);
    ctx.fillStyle='#fff'; ctx.font='bold 13px JetBrains Mono,monospace';
    ctx.textAlign='left'; ctx.fillText('Position: '+playerPos,10,23);
}

// ── JEU 3 ────────────────────────────────────────────────────────────────────

function drawSnake(s) {
    const W=canvas.width,H=canvas.height,GRID=20,sz=Math.min(W,H)/GRID;
    ctx.fillStyle='#0a0a0a'; ctx.fillRect(0,0,W,H);
    ctx.strokeStyle='#111'; ctx.lineWidth=0.5;
    for (let i=0;i<=GRID;i++){
        ctx.beginPath();ctx.moveTo(i*sz,0);ctx.lineTo(i*sz,H);ctx.stroke();
        ctx.beginPath();ctx.moveTo(0,i*sz);ctx.lineTo(W,i*sz);ctx.stroke();
    }
    (s.snake??[]).forEach(([x,y],i)=>{
        ctx.fillStyle=i===0?'#00e676':'#00c853'; ctx.fillRect(x*sz+1,y*sz+1,sz-2,sz-2);
    });
    const [fx,fy]=s.food??[0,0];
    ctx.fillStyle='#f44336'; ctx.fillRect(fx*sz+1,fy*sz+1,sz-2,sz-2);
    ctx.fillStyle='#fff'; ctx.font='bold 14px JetBrains Mono,monospace';
    ctx.textAlign='center'; ctx.textBaseline='top';
    ctx.fillText('Score: '+(s.score??0), W/2, 6);
}

// ── JEU 4 ────────────────────────────────────────────────────────────────────

function drawRush(s) {
    const W=canvas.width,H=canvas.height,GRID=s.grid_size??6;
    const sz=Math.min(W,H)/(GRID+0.5),ox=(W-sz*GRID)/2,oy=(H-sz*GRID)/2;
    ctx.fillStyle='#111'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#1a1a1a'; ctx.fillRect(ox,oy,sz*GRID,sz*GRID);
    ctx.strokeStyle='#333'; ctx.lineWidth=1;
    for (let i=0;i<=GRID;i++){
        ctx.beginPath();ctx.moveTo(ox+i*sz,oy);ctx.lineTo(ox+i*sz,oy+sz*GRID);ctx.stroke();
        ctx.beginPath();ctx.moveTo(ox,oy+i*sz);ctx.lineTo(ox+sz*GRID,oy+i*sz);ctx.stroke();
    }
    const [ex,ey]=s.exit_pos??[GRID,2];
    ctx.fillStyle='#00e676'; ctx.fillRect(ox+ex*sz,oy+ey*sz,sz*0.4,sz);
    ctx.fillStyle='#fff'; ctx.font=`bold ${sz*0.2}px JetBrains Mono,monospace`;
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText('EXIT', ox+ex*sz+sz*0.2, oy+ey*sz+sz/2);
    (s.vehicles??[]).forEach((v,idx)=>{
        const [vx,vy]=v.pos,isX=v.id==='X',pad=3;
        const color=isX?'#e53935':RUSH_COLORS[idx%RUSH_COLORS.length];
        let rx,ry,rw,rh;
        if (v.orientation==='h'){rx=ox+vx*sz+pad;ry=oy+vy*sz+pad;rw=v.length*sz-pad*2;rh=sz-pad*2;}
        else                    {rx=ox+vx*sz+pad;ry=oy+vy*sz+pad;rw=sz-pad*2;rh=v.length*sz-pad*2;}
        ctx.fillStyle=color; ctx.beginPath(); ctx.roundRect(rx,ry,rw,rh,4); ctx.fill();
        ctx.fillStyle='#fff'; ctx.font=`bold ${sz*0.28}px JetBrains Mono,monospace`;
        ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(v.id,rx+rw/2,ry+rh/2);
    });
    ctx.fillStyle='#666'; ctx.font='12px JetBrains Mono,monospace';
    ctx.textAlign='center'; ctx.textBaseline='bottom';
    ctx.fillText('Steps: '+(s.steps??0), W/2, H-4);
}

// ── JEU 5 ────────────────────────────────────────────────────────────────────

function drawTraffic(s) {
    const W=canvas.width,H=canvas.height,LANES=3;
    const laneW=W/(LANES+0.6),roadX=(W-laneW*LANES)/2;
    ctx.fillStyle='#1a2e1a'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#2d5a1b'; ctx.fillRect(0,0,roadX-2,H); ctx.fillRect(roadX+laneW*LANES+2,0,W,H);
    ctx.fillStyle='#2d3a2d'; ctx.fillRect(roadX,0,laneW*LANES,H);
    ctx.strokeStyle='rgba(255,255,255,0.7)'; ctx.lineWidth=3; ctx.setLineDash([25,25]);
    for (let i=1;i<LANES;i++){ctx.beginPath();ctx.moveTo(roadX+i*laneW,0);ctx.lineTo(roadX+i*laneW,H);ctx.stroke();}
    ctx.setLineDash([]);
    const prog=s.progress??0,maxProg=s.track_length??130;
    const barW=W*0.6,barH=8,barX=(W-barW)/2,barY=6;
    ctx.fillStyle='#111'; ctx.fillRect(barX,barY,barW,barH);
    ctx.fillStyle='#00e676'; ctx.fillRect(barX,barY,barW*Math.min(prog/maxProg,1),barH);
    ctx.fillStyle='#fff'; ctx.font='bold 11px JetBrains Mono,monospace'; ctx.textAlign='center';
    ctx.fillText('Progress '+prog.toFixed(1)+' / '+maxProg, W/2, barY+barH+12);
    const playerLane=s.lane??1,playerY=H*0.82,unitH=H/10;
    (s.sensor_window??[]).forEach(laneData=>{
        laneData.cells.forEach(cell=>{
            if (!cell.occupied) return;
            const lx=roadX+laneData.lane*laneW+laneW/2,ly=playerY-cell.offset*unitH;
            const cw2=laneW*0.55,ch2=unitH*0.7;
            ctx.fillStyle=cell.offset<0?'#f44336':'#ff8c00';
            ctx.beginPath(); ctx.roundRect(lx-cw2/2,ly-ch2/2,cw2,ch2,3); ctx.fill();
            ctx.fillStyle='#111'; ctx.fillRect(lx-cw2/3,ly-ch2/2+ch2*0.2,cw2*2/3,ch2*0.25);
            if (cell.relative_speed!==0){
                ctx.fillStyle='#fff'; ctx.font=`${unitH*0.2}px JetBrains Mono,monospace`; ctx.textAlign='center';
                ctx.fillText((cell.relative_speed>0?'+':'')+cell.relative_speed.toFixed(2),lx,ly-ch2/2-3);
            }
        });
    });
    const px=roadX+playerLane*laneW+laneW/2,cw=laneW*0.55,ch=unitH*0.8;
    ctx.fillStyle='#2196f3'; ctx.beginPath(); ctx.roundRect(px-cw/2,playerY-ch/2,cw,ch,4); ctx.fill();
    ctx.fillStyle='#90caf9'; ctx.fillRect(px-cw/3,playerY-ch/2+3,cw*2/3,ch*0.3);
    ctx.fillStyle='#fff'; ctx.font=`bold ${ch*0.22}px JetBrains Mono,monospace`;
    ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText('YOU',px,playerY);
    ctx.fillStyle='#000c'; ctx.fillRect(4,22,155,72);
    ctx.fillStyle='#fff'; ctx.font='bold 11px JetBrains Mono,monospace';
    ctx.textAlign='left'; ctx.textBaseline='top';
    const spd=typeof s.speed==='number'?s.speed.toFixed(2):'—';
    ctx.fillText('Lane  : '+playerLane,10,26);
    ctx.fillText('Speed : '+spd,10,40);
    ctx.fillText('Step  : '+(s.step??'—')+'/'+(s.max_steps??82),10,54);
    ctx.fillText('Action: '+(s.last_action??'—'),10,68);
}

// ── JEUX 6-9 ─────────────────────────────────────────────────────────────────

function drawMaze(s) {
    const W=canvas.width,H=canvas.height;
    ctx.fillStyle='#000'; ctx.fillRect(0,0,W,H);
    if (!s?.grid) return;
    const rows=s.grid.length,cols=s.grid[0].length,sz=Math.min(W/cols,H/rows);
    for (let y=0;y<rows;y++) for (let x=0;x<cols;x++){
        const cell=s.grid[y][x];
        ctx.fillStyle=CELL_COLORS[cell]||'#111'; ctx.fillRect(x*sz+1,y*sz+1,sz-2,sz-2);
        if (cell&&!['?','.',',','#','S'].includes(cell)){
            ctx.fillStyle='#ffffffcc'; ctx.font=`bold ${Math.max(8,sz*.42)}px JetBrains Mono,monospace`;
            ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(cell,x*sz+sz/2,y*sz+sz/2);
        }
    }
    if (s.player_pos){
        const [px,py]=s.player_pos;
        ctx.beginPath(); ctx.arc(px*sz+sz/2,py*sz+sz/2,sz*.32,0,Math.PI*2);
        ctx.fillStyle=currentGame?.color||'#00d4ff'; ctx.fill();
        ctx.strokeStyle='#fff'; ctx.lineWidth=1.5; ctx.stroke();
    }
}

// ── JEU 10 ───────────────────────────────────────────────────────────────────

function drawLander(s) {
    const W=canvas.width,H=canvas.height;
    ctx.fillStyle='#060d1a'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#ffffff';
    for (let i=0;i<60;i++){const sx=(i*137.5)%W,sy=(i*97.3)%(H*0.85),r=i%4===0?1.2:0.6;ctx.beginPath();ctx.arc(sx,sy,r,0,Math.PI*2);ctx.fill();}
    const groundY=H*0.88;
    ctx.fillStyle='#3a3a3a'; ctx.fillRect(0,groundY,W,H-groundY);
    ctx.strokeStyle='#555'; ctx.lineWidth=1; ctx.beginPath();ctx.moveTo(0,groundY);ctx.lineTo(W,groundY);ctx.stroke();
    const world=s.world_bounds??{width:100,height:80};
    const pad=s.landing_pad??{x1:40,x2:60};
    const toX=wx=>(wx/world.width)*W, toY=wy=>groundY-(wy/world.height)*(groundY-20);
    const padX1=toX(pad.x1),padX2=toX(pad.x2);
    ctx.fillStyle='#00e676'; ctx.fillRect(padX1,groundY-4,padX2-padX1,4);
    for (let i=0;i<=5;i++){const lx=padX1+(padX2-padX1)*i/5;ctx.fillStyle=i%2===0?'#00e676':'#fff';ctx.beginPath();ctx.arc(lx,groundY-2,2,0,Math.PI*2);ctx.fill();}
    const pos=s.position??{},vel=s.velocity??{};
    const shipX=toX(pos.x??world.width/2),shipY=toY(pos.altitude??0),tilt=s.tilt??0;
    ctx.save(); ctx.translate(shipX,shipY); ctx.rotate(tilt);
    ctx.fillStyle='#e0e0e0'; ctx.beginPath();ctx.moveTo(0,-14);ctx.lineTo(8,10);ctx.lineTo(-8,10);ctx.closePath();ctx.fill();
    ctx.fillStyle='#f44336'; ctx.fillRect(-8,4,16,3);
    ctx.strokeStyle='#888'; ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(-6,10);ctx.lineTo(-10,16);ctx.stroke();
    ctx.beginPath();ctx.moveTo(6,10);ctx.lineTo(10,16);ctx.stroke();
    ctx.restore();
    if (s.leg_contact_left) {ctx.fillStyle='#00e676';ctx.beginPath();ctx.arc(shipX-10,groundY,3,0,Math.PI*2);ctx.fill();}
    if (s.leg_contact_right){ctx.fillStyle='#00e676';ctx.beginPath();ctx.arc(shipX+10,groundY,3,0,Math.PI*2);ctx.fill();}
    const fuel=s.fuel??0;
    ctx.fillStyle='#000c'; ctx.fillRect(4,4,145,80);
    ctx.fillStyle='#fff'; ctx.font='bold 11px JetBrains Mono,monospace';
    ctx.textAlign='left'; ctx.textBaseline='top';
    ctx.fillText('Fuel : '+fuel.toFixed(1),10,8);
    ctx.fillText('VX   : '+(vel.vx??0).toFixed(3),10,22);
    ctx.fillText('VY   : '+(vel.vy??0).toFixed(3),10,36);
    ctx.fillText('Tilt : '+(s.tilt??0).toFixed(3),10,50);
    ctx.fillText('Alt  : '+(pos.altitude??0).toFixed(2),10,64);
    const fuelPct=fuel/100,bx=W-24,bh=H*0.4,by=(H-bh)/2;
    ctx.fillStyle='#111'; ctx.fillRect(bx,by,16,bh);
    ctx.fillStyle=fuelPct>0.3?'#00e676':'#ff5722'; ctx.fillRect(bx,by+bh*(1-fuelPct),16,bh*fuelPct);
    ctx.strokeStyle='#444'; ctx.lineWidth=1; ctx.strokeRect(bx,by,16,bh);
    ctx.fillStyle='#888'; ctx.font='9px JetBrains Mono,monospace';
    ctx.textAlign='center'; ctx.fillText('FUEL',bx+8,by+bh+12);
}

// ── GAME CONTROL ─────────────────────────────────────────────────────────────

async function startGame() {
    stopAuto(); memMap={};
    log('Connexion jeu '+currentGame.id+'...','info');
    try {
        const r=await api('/api/newgame/','POST',{idgame:currentGame.id});
        sessionId=r.gamesessionid;
        log('Session '+sessionId+' créée','ok');
        let s=r.state;
        if (!s){const r2=await api('/api/get_state/?gamesessionid='+sessionId,'GET');s=r2.state;}
        drawState(s); setSessionUI(sessionId,'RUNNING'); setControls(true);
    } catch(e) {
        if (e.message==='409'&&e.data?.existing_session_id){
            sessionId=e.data.existing_session_id;
            log('Session reprise : '+sessionId,'warn');
            setSessionUI(sessionId,'RESUMED'); setControls(true);
            try{const r2=await api('/api/get_state/?gamesessionid='+sessionId,'GET');drawState(r2.state);}catch(_){}
        } else { log('Erreur : '+(e.data?.error||e.message),'err'); }
    }
}

async function stopGame() {
    stopAuto(); if (!sessionId) return;
    try{await api('/api/stop_game/','POST',{gamesessionid:sessionId});log('Stoppée','warn');}catch(_){}
    sessionId=null; setSessionUI('—','OFFLINE'); setControls(false);
}

async function act(action) {
    if (!sessionId) return;
    try {
        const r=await api('/api/act/','POST',{gamesessionid:sessionId,action});
        if (r.state) drawState(r.state);
        if (r.status==='win'){
            log('VICTOIRE !','ok');
            document.getElementById('s-status').textContent='WIN';
            document.getElementById('s-score').textContent='+pts';
            setControls(false); stopAuto(); sessionId=null;
        } else if (r.status==='lose'||r.status==='max_steps'){
            log('Défaite ('+r.status+')','err');
            document.getElementById('s-status').textContent='LOSE';
            setControls(false); stopAuto(); sessionId=null;
        }
    } catch(e){log('Err: '+(e.data?.error||e.message),'err');}
}

// ── AUTO-PLAY ────────────────────────────────────────────────────────────────

function autoAction(s) {
    if (!s) return 'up';
    const t=currentGame?.type;
    if (t==='ttt'){const b=s.board;for(let r=0;r<3;r++)for(let c=0;c<3;c++)if(!b[r][c])return''+r+c;return'00';}
    if (t==='car'){
        const obs=s.upcoming_obstacles??[],pos=s.position??0,lane=s.lane??1;
        const danger=obs.filter(o=>o.step===pos+1||o.step===pos+2);
        if(danger.some(o=>o.lane===lane)){
            if(lane>0&&!danger.some(o=>o.lane===lane-1))return'move_left';
            if(lane<2&&!danger.some(o=>o.lane===lane+1))return'move_right';
        }
        return 'stay';
    }
    if (t==='snake'){
        const snake=s.snake??[[0,0]],[hx,hy]=snake[0],[fx,fy]=s.food??[0,0];
        const body=new Set(snake.map(([x,y])=>x+','+y));
        const dirs=[['up',hx,hy-1],['down',hx,hy+1],['left',hx-1,hy],['right',hx+1,hy]];
        const safe=dirs.filter(([,nx,ny])=>nx>=0&&nx<20&&ny>=0&&ny<20&&!body.has(nx+','+ny));
        if(!safe.length)return'up';
        const toward=safe.find(([,nx,ny])=>(fx<hx&&nx<hx)||(fx>hx&&nx>hx)||(fy<hy&&ny<hy)||(fy>hy&&ny>hy));
        return(toward??safe[0])[0];
    }
    if (t==='rush') return 'move_X_right';
    if (t==='traffic'){
        const lane=s.lane??1,speed=s.speed??1,gaps=s.lane_gaps??[];
        const cur=gaps.find(g=>g.lane===lane),ahead=cur?.ahead??999;
        if(ahead<8){const alt=gaps.filter(g=>g.lane!==lane&&(g.ahead??0)>12);if(alt.length)return alt[0].lane<lane?'left':'right';return'brake';}
        if(speed<8&&ahead>15)return'accelerate';
        return 'keep';
    }
    if (t==='maze') return bfsAction(s);
    if (t==='lander'){
        const obs=s.observation??[],alt=obs[0]??10,vy=obs[2]??0,dx=obs[3]??0;
        const theta=Math.asin(Math.max(-1,Math.min(1,obs[5]??0)));
        if(Math.abs(dx)>5)return dx>0?'main_left':'main_right';
        if(vy<-0.8||alt>20)return'main';
        if(Math.abs(theta)>0.1)return'stabilize';
        return 'idle';
    }
    return 'up';
}

function bfsAction(s) {
    if (!s?.grid) return 'up';
    for (let y=0;y<s.grid.length;y++) for (let x=0;x<s.grid[y].length;x++){const ch=s.grid[y][x];if(ch&&ch!=='?')memMap[x+','+y]=ch;}
    const [sx,sy]=s.player_pos,exit=s.exit_pos,has_key=s.has_key??false;
    const mv=[['up',0,-1],['down',0,1],['left',-1,0],['right',1,0]];
    const par={[sx+','+sy]:null},q=[[sx,sy]];let found=null;
    outer:while(q.length){
        const [cx,cy]=q.shift();
        for(const [name,dx,dy] of mv){
            const nx=cx+dx,ny=cy+dy,k=nx+','+ny;
            if(k in par)continue;
            if(exit&&nx===exit[0]&&ny===exit[1]){par[k]=[cx,cy,name];found=k;break outer;}
            const ch=memMap[k];
            if(!ch){par[k]=[cx,cy,name];found=k;break outer;}
            if(ch==='#'||ch==='L')continue;
            if(ch==='D'&&!has_key)continue;
            par[k]=[cx,cy,name];q.push([nx,ny]);
        }
    }
    if(!found)return mv[Math.floor(Math.random()*4)][0];
    let cur=found;
    while(par[cur]&&par[par[cur][0]+','+par[cur][1]]!==null)cur=par[cur][0]+','+par[cur][1];
    return par[cur]?.[2]??'up';
}

function toggleAuto(){
    if(autoTimer){stopAuto();return;}
    document.getElementById('btn-auto').textContent='⏸ Stop auto';
    autoTimer=setInterval(async()=>{if(!curState||!sessionId){stopAuto();return;}await act(autoAction(curState));},1150);
}
function stopAuto(){
    if(autoTimer){clearInterval(autoTimer);autoTimer=null;}
    document.getElementById('btn-auto').textContent='⚡ Auto-play';
}
function setControls(on){['btn-stop','btn-auto','k-up','k-down','k-left','k-right'].forEach(id=>document.getElementById(id).disabled=!on);}
function setSessionUI(id,status){document.getElementById('s-id').textContent=id;document.getElementById('s-status').textContent=status;}

document.addEventListener('keydown',e=>{
    if(!sessionId)return;
    const m={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right'};
    if(m[e.key]){e.preventDefault();act(m[e.key]);}
});

boot();