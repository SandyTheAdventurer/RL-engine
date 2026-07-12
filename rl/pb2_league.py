import optuna
import numpy as np
import copy
import torch
import random
from rl.gail import GAIL
from rl.env import EngineEnv, sys_config
from rl.vec_env import MultiEngineEnv

class PB2League:
    def __init__(self, pop_size, num_envs, device):
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        self.pop_size = pop_size
        self.num_envs = num_envs
        self.device = device
        
        self.study = optuna.create_study(direction="maximize")
        self.population = []
        
        print(f"Initializing PB2 League with {pop_size} agents...")
        for i in range(pop_size):
            agent = type("Agent", (object,), {})()
            agent.id = i
            agent.env = MultiEngineEnv(num_envs=num_envs, frame_skip=4)
            agent.gail = GAIL(agent.env, boss_dir=None, device=device)
            
            agent.trial = self.study.ask()
            agent.gen_lr = agent.trial.suggest_float("gen_lr", 1e-5, 1e-3, log=True)
            agent.disc_lr = agent.trial.suggest_float("disc_lr", 1e-5, 1e-3, log=True)
            agent.score = 0.0
            self.population.append(agent)

    def get_champion(self):
        self.population.sort(key=lambda x: x.score, reverse=True)
        return self.population[0]

    def apply_learning_rates(self):
        for agent in self.population:
            for param_group in agent.gail.gen_optimizer.param_groups: 
                param_group['lr'] = agent.gen_lr
            for param_group in agent.gail.discriminator.optim.param_groups: 
                param_group['lr'] = agent.disc_lr

    def evolve(self):

        for agent in self.population:
            self.study.tell(agent.trial, agent.score)
            

        self.population.sort(key=lambda x: x.score, reverse=True)
        cutoff = self.pop_size // 2
        top_agents = self.population[:cutoff]
        bottom_agents = self.population[cutoff:]
        
        print(f"\n--- EVOLUTION RESULTS ---")
        

        for agent in top_agents:
            agent.trial = self.study.ask()
            agent.gen_lr = np.clip(agent.gen_lr * agent.trial.suggest_float("gen_lr_mult", 0.8, 1.2), 1e-6, 1e-2)
            agent.disc_lr = np.clip(agent.disc_lr * agent.trial.suggest_float("disc_lr_mult", 0.8, 1.2), 1e-6, 1e-2)


        for bottom in bottom_agents:
            top = random.choice(top_agents)
            print(f"Agent {bottom.id} (Score {bottom.score:.2f}) was killed. Replaced by Agent {top.id} (Score {top.score:.2f})!")
            

            bottom.gail.generator.load_state_dict(copy.deepcopy(top.gail.generator.state_dict()))
            bottom.gail.boss.load_state_dict(copy.deepcopy(top.gail.boss.state_dict()))
            bottom.gail.discriminator.load_state_dict(copy.deepcopy(top.gail.discriminator.state_dict()))
            bottom.gail.gen_optimizer.load_state_dict(copy.deepcopy(top.gail.gen_optimizer.state_dict()))
            bottom.gail.discriminator.optim.load_state_dict(copy.deepcopy(top.gail.discriminator.optim.state_dict()))
            

            bottom.trial = self.study.ask()
            bottom.gen_lr = np.clip(top.gen_lr * bottom.trial.suggest_float("gen_lr_mult", 0.5, 2.0), 1e-6, 1e-2)
            bottom.disc_lr = np.clip(top.disc_lr * bottom.trial.suggest_float("disc_lr_mult", 0.5, 2.0), 1e-6, 1e-2)
