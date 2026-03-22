import pickle
from collections import Counter

from hackathon_rl_envs.tictactoe_rl import TicTacToeEnv


MODEL_PATH = "tictactoe_q.pkl"
EPISODES = 10000


def state_key(obs):
    return tuple(float(x) for x in obs.tolist())


def main():
    with open(MODEL_PATH, "rb") as f:
        q_table = pickle.load(f)  # dict[state_tuple] -> list[Q-values]

    env = TicTacToeEnv(seed=999)
    results = Counter()
    total_reward = 0.0

    for _ in range(EPISODES):
        obs, info = env.reset()
        done = False
        last_reward = 0.0
        final_result = "unknown"

        while not done:
            s = state_key(obs)
            mask = info["action_mask"]
            valid_actions = [i for i, v in enumerate(mask) if v == 1]

            qvals = q_table.get(s)
            if qvals is None:
                # état non vu: prend la 1ère action valide
                action = valid_actions[0]
            else:
                action = max(valid_actions, key=lambda a: qvals[a])

            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            last_reward = reward
            if done:
                final_result = info.get("result", "unknown")

        results[final_result] += 1
        total_reward += float(last_reward)

    wins = results["win"]
    losses = results["lose"]
    ties = results["tie"]
    print(f"Episodes: {EPISODES}")
    print(f"Win:  {wins} ({wins/EPISODES:.1%})")
    print(f"Lose: {losses} ({losses/EPISODES:.1%})")
    print(f"Tie:  {ties} ({ties/EPISODES:.1%})")
    print(f"Avg terminal reward: {total_reward/EPISODES:.4f}")


if __name__ == "__main__":
    main()