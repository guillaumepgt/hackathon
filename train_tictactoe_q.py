import random
import pickle
from collections import defaultdict

from hackathon_rl_envs.tictactoe_rl import TicTacToeEnv

EPISODES = 2000000
ALPHA = 0.1
GAMMA = 0.99
EPS_START = 1.0
EPS_END = 0.05
EPS_DECAY = 0.99995


def state_key(obs):
    return tuple(float(x) for x in obs.tolist())


env = TicTacToeEnv(seed=123)
Q = defaultdict(lambda: [0.0] * env.action_space.n)

eps = EPS_START
for ep in range(EPISODES):
    # seed variable par épisode
    obs, info = env.reset(seed=123 + ep)
    done = False

    while not done:
        s = state_key(obs)
        mask = info["action_mask"]
        valid_actions = [i for i, v in enumerate(mask) if v == 1]

        # epsilon-greedy masqué
        if random.random() < eps:
            a = random.choice(valid_actions)
        else:
            qvals = Q[s]
            a = max(valid_actions, key=lambda x: qvals[x])

        obs2, r, terminated, truncated, info2 = env.step(a)
        done = terminated or truncated
        s2 = state_key(obs2)

        if done:
            target = r
        else:
            next_valid = [i for i, v in enumerate(info2["action_mask"]) if v == 1]
            best_next = max((Q[s2][i] for i in next_valid), default=0.0)
            target = r + GAMMA * best_next

        Q[s][a] += ALPHA * (target - Q[s][a])
        obs, info = obs2, info2

    eps = max(EPS_END, eps * EPS_DECAY)

    if (ep + 1) % 10000 == 0:
        print(f"episode={ep+1} eps={eps:.3f}")

with open("tictactoe_q.pkl", "wb") as f:
    pickle.dump(dict(Q), f)

print("Saved: tictactoe_q.pkl")