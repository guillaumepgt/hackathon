// Shared game rendering and animation functions

// Game rendering functions
function renderTicTacToe(state, container = document) {
    const boardDiv = container.querySelector('#game-board');
    if (!boardDiv) return;

    const board = state.board || [['', '', ''], ['', '', ''], ['', '', '']];
    let html = '';

    for (let i = 0; i < 3; i++) {
        html += '<div style="display: flex;">';
        for (let j = 0; j < 3; j++) {
            const cell = board[i][j] || '&nbsp;';
            const borderRight = j < 2 ? 'border-right: 2px solid #000;' : '';
            const borderBottom = i < 2 ? 'border-bottom: 2px solid #000;' : '';
            const cellStyle = `width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; ${borderRight} ${borderBottom}`;
            html += `<div style="${cellStyle}">${cell}</div>`;
        }
        html += '</div>';
    }

    boardDiv.innerHTML = html;
}

function renderMoonLander(state, container = document) {
    const canvas = container.querySelector('#game-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const ground_y = canvas.height - 48;
    const landing_pad = state.landing_pad;
    const worldBounds = state.world_bounds || { width: 100, height: 80 };
    const altitude = state.position?.altitude || 0;
    const shipX = (state.position?.x || 0) / worldBounds.width * canvas.width;
    const shipY = ground_y - (altitude / worldBounds.height * (ground_y - 24));

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw sky
    ctx.fillStyle = '#001122';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw ground
    ctx.fillStyle = '#666666';
    ctx.fillRect(0, ground_y, canvas.width, canvas.height - ground_y);

    // Draw landing pad
    ctx.fillStyle = '#00ff99';
    const padWidth = ((landing_pad.x2 - landing_pad.x1) / worldBounds.width) * canvas.width;
    const padX = (landing_pad.x1 / worldBounds.width) * canvas.width;
    ctx.fillRect(padX, ground_y, padWidth, 10);

    // Draw ship
    const tilt = state.tilt || 0;
    ctx.save();
    ctx.translate(shipX, shipY);
    ctx.rotate(-tilt);
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(0, -12);
    ctx.lineTo(-10, 10);
    ctx.lineTo(10, 10);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = '#8bd3ff';
    ctx.beginPath();
    ctx.moveTo(-8, 10);
    ctx.lineTo(-12, 16);
    ctx.moveTo(8, 10);
    ctx.lineTo(12, 16);
    ctx.stroke();
    ctx.restore();

    // Draw velocity vector (scaled)
    ctx.strokeStyle = '#ff0000';
    ctx.beginPath();
    ctx.moveTo(shipX, shipY);
    const endX = shipX + (state.velocity?.vx || 0) * 18;
    const endY = shipY - (state.velocity?.vy || 0) * 18;
    ctx.lineTo(endX, endY);
    ctx.stroke();

    // Draw stars (random but consistent)
    ctx.fillStyle = '#ffffff';
    let seed = 12345;
    for(let i = 0; i < 20; i++) {
        seed = (seed * 9301 + 49297) % 233280;
        const x = (seed / 233280) * canvas.width;
        seed = (seed * 9301 + 49297) % 233280;
        const y = (seed / 233280) * ground_y;
        ctx.fillRect(x, y, 1, 1);
    }

    // Update stats
    const statsDiv = container.querySelector('#game-stats');
    if (statsDiv) {
        statsDiv.innerHTML = `Fuel: ${state.fuel.toFixed(1)}<br>VX: ${state.velocity.vx.toFixed(2)}<br>VY: ${state.velocity.vy.toFixed(2)}<br>Tilt: ${state.tilt.toFixed(2)}`;
    }
}

function renderCarRacing(state, container = document) {
    const canvas = container.querySelector('#car-racing-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grass (outside road)
    ctx.fillStyle = '#4CAF50'; // Green
    ctx.fillRect(0, 0, 75, 400); // Left grass
    ctx.fillRect(525, 0, 75, 400); // Right grass

    // Draw road
    ctx.fillStyle = '#666666'; // Gray road
    ctx.fillRect(75, 0, 450, 400);

    // Draw lane lines
    ctx.strokeStyle = '#FFFFFF'; // White lines
    ctx.lineWidth = 4;
    ctx.setLineDash([10, 10]); // Dashed lines
    for (let i = 1; i < 3; i++) {
        ctx.beginPath();
        ctx.moveTo(75 + i * 150, 0);
        ctx.lineTo(75 + i * 150, 400);
        ctx.stroke();
    }
    ctx.setLineDash([]); // Reset to solid

    // Draw road edges
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(75, 0);
    ctx.lineTo(75, 400);
    ctx.moveTo(525, 0);
    ctx.lineTo(525, 400);
    ctx.stroke();

    // Draw obstacles (half lane width, centered, half height top-aligned)
    const obstacles = state.upcoming_obstacles || [];
    obstacles.forEach(obs => {
        const y = 345 - (obs.step - state.position) * 15;
        const laneLeft = 75 + obs.lane * 150;
        const obsWidth = 75; // Half lane width
        const obsX = laneLeft + (150 - obsWidth) / 2; // Centered
        const obsHeight = 7.5; // Half height
        if (y > 0 && y < 400) {
            // Draw barrier
            ctx.fillStyle = '#8B0000'; // Dark red
            ctx.fillRect(obsX, y, obsWidth, obsHeight);
            // Add warning stripes
            ctx.fillStyle = '#FFFF00'; // Yellow
            for (let i = 0; i < obsWidth; i += 20) {
                ctx.fillRect(obsX + i, y, 10, obsHeight);
            }
        }
    });

    // Draw car (centered in lane)
    const laneCenter = 150 + state.lane * 150; // 150, 300, 450
    const carX = laneCenter - 15;
    // Car body
    ctx.fillStyle = '#0000FF'; // Blue
    ctx.fillRect(carX, 350, 30, 15);
    // Car top
    ctx.fillStyle = '#87CEEB'; // Light blue
    ctx.fillRect(carX + 5, 345, 20, 8);
    // Wheels
    ctx.fillStyle = '#000000'; // Black
    ctx.fillRect(carX + 2, 362, 6, 3);
    ctx.fillRect(carX + 22, 362, 6, 3);

    // Draw position indicator
    ctx.fillStyle = 'black';
    ctx.font = '16px Arial';
    ctx.fillText('Position: ' + state.position, 10, 20);
}

function renderSnake(state, container = document) {
    const canvas = container.querySelector('#snake-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cellSize = 20;
    const boardSize = 20;

    // Clear canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid (optional, for debugging)
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let i = 0; i <= boardSize; i++) {
        ctx.beginPath();
        ctx.moveTo(i * cellSize, 0);
        ctx.lineTo(i * cellSize, boardSize * cellSize);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i * cellSize);
        ctx.lineTo(boardSize * cellSize, i * cellSize);
        ctx.stroke();
    }

    // Draw snake
    ctx.fillStyle = '#0f0';
    (state.snake || []).forEach(pos => {
        ctx.fillRect(pos[1] * cellSize, pos[0] * cellSize, cellSize, cellSize);
    });

    // Draw food
    ctx.fillStyle = '#f00';
    if (state.food) {
        ctx.fillRect(state.food[1] * cellSize, state.food[0] * cellSize, cellSize, cellSize);
    }

    // Update score
    const scoreEl = container.querySelector('#snake-score');
    if (scoreEl) scoreEl.textContent = state.score || 0;
}

function renderRushHour(state, container = document) {
    const canvas = container.querySelector('#rushhour-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const grid_size = state.grid_size;
    const vehicles = state.vehicles;
    const cellSize = 50;
    // Draw grid
    ctx.strokeStyle = '#ccc';
    for (let i = 0; i <= grid_size; i++) {
        ctx.beginPath();
        ctx.moveTo(i * cellSize, 0);
        ctx.lineTo(i * cellSize, grid_size * cellSize);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i * cellSize);
        ctx.lineTo((grid_size - 1) * cellSize, i * cellSize);
        ctx.stroke();
    }

    // Draw vehicles
    vehicles.forEach(vehicle => {
        const colorIndex = vehicle.id.charCodeAt(0) - 65;
        ctx.fillStyle = vehicle.id === 'X' ? '#f00' : colors[colorIndex % colors.length];
        const x = vehicle.pos[1] * cellSize;
        const y = vehicle.pos[0] * cellSize;
        const width = vehicle.orientation === 'h' ? vehicle.length * cellSize : cellSize;
        const height = vehicle.orientation === 'v' ? vehicle.length * cellSize : cellSize;
        ctx.fillRect(x, y, width, height);
        ctx.fillStyle = '#fff';
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(vehicle.id, x + width/2, y + height/2 + 7);
    });

    // Draw exit
    ctx.fillStyle = '#0f0';
    const exitX = (state.exit_pos[1]) * cellSize;
    const exitY = (state.exit_pos[0]) * cellSize;
    ctx.fillRect(exitX, exitY, cellSize, cellSize);
    ctx.fillStyle = '#fff';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('EXIT', exitX + cellSize/2, exitY + cellSize/2 + 4);

    // Update steps
    const stepsEl = container.querySelector('#rushhour-steps');
    if (stepsEl) stepsEl.textContent = state.steps;
}

function renderMaze(state, container = document) {
    const canvas = container.querySelector('#maze-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const grid = state.grid || [];
    const playerPos = state.player_pos || [0, 0];
    const height = grid.length;
    const width = height > 0 ? grid[0].length : 0;
    const cellSize = Math.min(500 / width, 500 / height);

    // Clear canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const cell = grid[y][x];
            let color = '#000'; // Default black for walls

            if (cell === '.') color = '#fff'; // Empty path
            else if (cell === 'S') color = '#0f0'; // Start
            else if (cell === 'E') color = '#ff0'; // Exit
            else if (cell === 'L') color = '#f00'; // Lava
            else if (cell === 'K') color = '#f0f'; // Key
            else if (cell === 'D') color = '#ffa500'; // Door
            else if (cell === '?') color = '#666'; // Unknown (fog of war)

            ctx.fillStyle = color;
            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);

            // Draw grid lines
            ctx.strokeStyle = '#333';
            ctx.lineWidth = 1;
            ctx.strokeRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
    }

    // Draw player
    ctx.fillStyle = '#00f';
    ctx.beginPath();
    ctx.arc(playerPos[0] * cellSize + cellSize/2, playerPos[1] * cellSize + cellSize/2,
            cellSize/3, 0, 2 * Math.PI);
    ctx.fill();

    // Update position info
    const infoDiv = canvas.parentElement.querySelector('div');
    if (infoDiv) {
        const hasKey = state.has_key ? 'Has Key' : 'No Key';
        const steps = state.steps || 0;
        const maxSteps = 100; // Could be passed in state
        infoDiv.innerHTML = `Position: (${playerPos[0]}, ${playerPos[1]}) | Steps: ${steps}/${maxSteps} | ${hasKey}`;
    }
}

function renderAdaptiveTrafficRacing(state, container = document) {
    const canvas = container.querySelector('#traffic-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const roadLeft = 78;
    const roadWidth = 370;
    const roadRight = roadLeft + roadWidth;
    const roadTop = 48;
    const roadBottom = canvas.height - 32;
    const laneWidth = roadWidth / 3;
    const playerY = roadBottom - 56;
    const playerX = roadLeft + state.lane * laneWidth + laneWidth / 2;
    const sidePanelX = roadRight + 22;
    const sidePanelWidth = canvas.width - sidePanelX - 18;

    const skyGradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    skyGradient.addColorStop(0, '#dbeafe');
    skyGradient.addColorStop(0.45, '#bfdbfe');
    skyGradient.addColorStop(1, '#a3b18a');
    ctx.fillStyle = skyGradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#3b3b45';
    ctx.fillRect(roadLeft, roadTop, roadWidth, roadBottom - roadTop);
    ctx.fillStyle = '#64748b';
    ctx.fillRect(roadLeft - 10, roadTop, 10, roadBottom - roadTop);
    ctx.fillRect(roadRight, roadTop, 10, roadBottom - roadTop);

    ctx.strokeStyle = '#f8fafc';
    ctx.lineWidth = 3;
    ctx.setLineDash([16, 14]);
    for (let lane = 1; lane < 3; lane++) {
        const x = roadLeft + lane * laneWidth;
        ctx.beginPath();
        ctx.moveTo(x, roadTop);
        ctx.lineTo(x, roadBottom);
        ctx.stroke();
    }
    ctx.setLineDash([]);

    for (let lane = 0; lane < 3; lane++) {
        const laneCenter = roadLeft + lane * laneWidth + laneWidth / 2;
        ctx.fillStyle = lane === state.lane ? '#ffffff' : 'rgba(255,255,255,0.6)';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`Lane ${lane}`, laneCenter, roadTop - 12);
    }

    // Distance scale and danger window
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.25)';
    ctx.lineWidth = 1;
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    for (let distance = -8; distance <= 28; distance += 4) {
        const y = playerY - distance * 9;
        if (y < roadTop || y > roadBottom) continue;
        ctx.beginPath();
        ctx.moveTo(roadLeft - 14, y);
        ctx.lineTo(roadRight + 14, y);
        ctx.stroke();
        ctx.fillStyle = '#0f172a';
        ctx.fillText(`${distance > 0 ? '+' : ''}${distance}`, 10, y + 4);
    }
    ctx.fillStyle = 'rgba(248, 113, 113, 0.18)';
    ctx.fillRect(roadLeft, playerY - 28, roadWidth, 56);

    const laneGaps = state.lane_gaps || [];
    laneGaps.forEach(gap => {
        if (!gap.safe_now) return;
        const x = roadLeft + gap.lane * laneWidth + 12;
        ctx.fillStyle = 'rgba(16, 185, 129, 0.15)';
        ctx.fillRect(x, roadTop + 8, laneWidth - 24, roadBottom - roadTop - 16);
    });

    // Nearby traffic
    (state.nearby_vehicles || []).forEach(vehicle => {
        const y = playerY - vehicle.distance * 9;
        if (y < roadTop - 24 || y > roadBottom + 24) return;
        const x = roadLeft + vehicle.lane * laneWidth + laneWidth / 2;
        const color = vehicle.relative_speed > 0 ? '#f97316' : '#ef4444';
        ctx.fillStyle = color;
        ctx.fillRect(x - 24, y - 18, 48, 36);
        ctx.fillStyle = '#111827';
        ctx.fillRect(x - 16, y - 8, 32, 12);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(vehicle.relative_speed > 0 ? `+${vehicle.relative_speed}` : `${vehicle.relative_speed}`, x, y - 24);
    });

    // Player car
    ctx.fillStyle = '#0ea5e9';
    ctx.fillRect(playerX - 26, playerY - 24, 52, 46);
    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(playerX - 16, playerY - 11, 32, 16);
    ctx.fillStyle = '#020617';
    ctx.fillRect(playerX - 22, playerY + 18, 10, 6);
    ctx.fillRect(playerX + 12, playerY + 18, 10, 6);
    ctx.fillStyle = '#082f49';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('YOU', playerX, playerY - 32);

    // Progress bar
    const progressRatio = Math.max(0, Math.min(1, (state.progress || 0) / (state.track_length || 1)));
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(20, 16, roadWidth + sidePanelWidth + 14, 16);
    ctx.fillStyle = '#22c55e';
    ctx.fillRect(20, 16, (roadWidth + sidePanelWidth + 14) * progressRatio, 16);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`Progress ${(state.progress || 0).toFixed(1)} / ${(state.track_length || 0).toFixed(0)}`, 20 + (roadWidth + sidePanelWidth + 14) / 2, 28);

    // Side panel: summary + sensor window
    ctx.fillStyle = 'rgba(15, 23, 42, 0.82)';
    ctx.fillRect(sidePanelX, roadTop, sidePanelWidth, roadBottom - roadTop);
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('Telemetry', sidePanelX + 12, roadTop + 22);

    const currentGap = laneGaps.find(gap => gap.lane === state.lane);
    const aheadText = currentGap && currentGap.ahead !== null ? currentGap.ahead.toFixed(1) : 'clear';
    const behindText = currentGap && currentGap.behind !== null ? currentGap.behind.toFixed(1) : 'clear';
    ctx.font = '12px Arial';
    ctx.fillText(`Lane: ${state.lane}`, sidePanelX + 12, roadTop + 46);
    ctx.fillText(`Speed: ${state.speed.toFixed(2)}`, sidePanelX + 12, roadTop + 64);
    ctx.fillText(`Step: ${(state.step || 0)} / ${(state.max_steps || 0)}`, sidePanelX + 12, roadTop + 82);
    ctx.fillText(`Ahead gap: ${aheadText}`, sidePanelX + 12, roadTop + 100);
    ctx.fillText(`Behind gap: ${behindText}`, sidePanelX + 12, roadTop + 118);
    ctx.fillText(`Last action: ${state.last_action || 'keep'}`, sidePanelX + 12, roadTop + 136);

    ctx.font = 'bold 13px Arial';
    ctx.fillText('Agent Sensor Window', sidePanelX + 12, roadTop + 166);

    const sensorWindow = state.sensor_window || [];
    const sensorGridTop = roadTop + 178;
    const sensorCellWidth = Math.floor((sidePanelWidth - 30) / 9);
    const sensorCellHeight = 18;
    sensorWindow.forEach((laneData, laneIndex) => {
        const rowY = sensorGridTop + laneIndex * (sensorCellHeight + 10);
        ctx.fillStyle = laneData.lane === state.lane ? '#93c5fd' : '#cbd5e1';
        ctx.font = 'bold 11px Arial';
        ctx.fillText(`L${laneData.lane}`, sidePanelX + 12, rowY + 12);
        laneData.cells.forEach((cell, cellIndex) => {
            const x = sidePanelX + 34 + cellIndex * sensorCellWidth;
            let fill = '#1f2937';
            if (cell.occupied) {
                fill = cell.relative_speed > 0 ? '#fb923c' : '#f87171';
            } else if (cell.occupied_t1 || cell.occupied_t2) {
                fill = '#475569';
            }
            ctx.fillStyle = fill;
            ctx.fillRect(x, rowY, sensorCellWidth - 2, sensorCellHeight);
            if (laneIndex === 0) {
                ctx.fillStyle = '#cbd5e1';
                ctx.font = '10px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(`${cell.offset}`, x + (sensorCellWidth - 2) / 2, rowY - 4);
            }
        });
    });

    ctx.fillStyle = '#cbd5e1';
    ctx.font = '11px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('Orange/red = occupied now, grey = occupied in recent history', sidePanelX + 12, sensorGridTop + 96);
    ctx.fillText('Offsets are distances relative to your car', sidePanelX + 12, sensorGridTop + 112);

    const statsDiv = container.querySelector('#traffic-stats');
    if (statsDiv) {
        statsDiv.innerHTML = `Lane: ${state.lane}<br>Speed: ${state.speed.toFixed(2)}<br>Progress: ${state.progress.toFixed(1)}/${state.track_length.toFixed(0)}<br>Step: ${(state.step || 0)}/${(state.max_steps || 0)}`;
    }
}

// Colors for Rush Hour vehicles
const colors = ['#008000', '#000080', '#800080', '#808000', '#800000', '#008080', '#808080', '#000000'];

// Main render function
function renderState(gameId, state, container = document) {
    if (gameId === 1) {
        renderTicTacToe(state, container);
    } else if (gameId === 2) {
        renderCarRacing(state, container);
    } else if (gameId === 3) {
        renderSnake(state, container);
    } else if (gameId === 4) {
        renderRushHour(state, container);
    } else if (gameId === 5) {
        renderAdaptiveTrafficRacing(state, container);
    } else if (gameId >= 6 && gameId <= 9) {
        renderMaze(state, container);
    } else if (gameId === 10) {
        renderMoonLander(state, container);
    }
}

// Animation functions
function startAnimation(gameId, history, containerId, onLoopComplete = null) {
    if (!history || history.length === 0) return;

    const container = document.getElementById(containerId);
    if (!container) return;

    let currentIndex = 0;
    renderState(gameId, history[currentIndex], container);
    currentIndex = (currentIndex + 1) % history.length;

    const interval = setInterval(() => {
        renderState(gameId, history[currentIndex], container);
        currentIndex = (currentIndex + 1) % history.length;

        // Check for newer games after each complete loop
        if (currentIndex === 0 && onLoopComplete) {
            onLoopComplete();
        }
    }, 250); // 4 moves per second

    return interval;
}

function stopAnimation(interval) {
    if (interval) {
        clearInterval(interval);
    }
}
