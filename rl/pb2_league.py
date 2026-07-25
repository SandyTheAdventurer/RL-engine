import logging
import optuna
import numpy as np
import copy
import random
import torch
from rl.gail import GAIL
from rl.vec_env import MultiEngineEnv
from rl.config import gen_lr_range, disc_lr_range

logger = logging.getLogger("rl.pb2")

class PB2Agent:
    def __init__(self, agent_id, num_envs, device, trial):
        self.id = agent_id
        self.env = MultiEngineEnv(num_envs=num_envs)
        self.gail = GAIL(self.env, boss_dir=None, device=device)
        self.trial = trial
        glr_min, glr_max = gen_lr_range()
        dlr_min, dlr_max = disc_lr_range()
        self.gen_lr = self.trial.suggest_float("gen_lr", glr_min, glr_max, log=True)
        self.disc_lr = self.trial.suggest_float("disc_lr", dlr_min, dlr_max, log=True)
        self.score = 0.0
        self.persistent_state = None

    def init_persistent_states(self, device, num_envs):
        obs, _ = self.env.reset()
        done = np.zeros(num_envs, dtype=bool)
        gen_lstm = (
            torch.zeros(self.gail.generator.lstm.num_layers, num_envs, self.gail.generator.lstm.hidden_size).to(device),
            torch.zeros(self.gail.generator.lstm.num_layers, num_envs, self.gail.generator.lstm.hidden_size).to(device),
        )
        boss_lstm = (
            torch.zeros(self.gail.boss.lstm.num_layers, num_envs, self.gail.boss.lstm.hidden_size).to(device),
            torch.zeros(self.gail.boss.lstm.num_layers, num_envs, self.gail.boss.lstm.hidden_size).to(device),
        )
        disc_lstm = (
            torch.zeros(1, num_envs, self.gail.discriminator.lstm.hidden_size).to(device),
            torch.zeros(1, num_envs, self.gail.discriminator.lstm.hidden_size).to(device),
        )
        self.persistent_state = (obs, done, gen_lstm, boss_lstm, disc_lstm)

    def get_states(self, device, num_envs):
        if self.persistent_state is None:
            self.init_persistent_states(device, num_envs)
        return self.persistent_state

    def save_states(self, obs, done, gen_lstm, boss_lstm, disc_lstm):
        self.persistent_state = (obs, done, gen_lstm, boss_lstm, disc_lstm)

class PB2League:
    def __init__(self, pop_size, num_envs, device):
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        self.pop_size = pop_size
        self.num_envs = num_envs
        self.device = device
        
        self.study = optuna.create_study(direction="maximize")
        self.population = []
        
        logger.info("Initializing PB2 League with %d agents...", pop_size)
        for i in range(pop_size):
            agent = PB2Agent(i, num_envs, device, self.study.ask())
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
            for param_group in agent.gail.boss_optimizer.param_groups:
                param_group['lr'] = agent.gen_lr

    def evolve(self, cycle_num=None):

        for agent in self.population:
            self.study.tell(agent.trial, agent.score)
            

        self.population.sort(key=lambda x: x.score, reverse=True)
        cutoff = self.pop_size // 2
        top_agents = self.population[:cutoff]
        bottom_agents = self.population[cutoff:]
        
        logger.info("--- EVOLUTION RESULTS (Cycle %s) ---", cycle_num)
        

        for agent in top_agents:
            agent.trial = self.study.ask()
            agent.gen_lr = np.clip(agent.gen_lr * agent.trial.suggest_float("gen_lr_mult", 0.8, 1.2), 1e-6, 1e-2)
            agent.disc_lr = np.clip(agent.disc_lr * agent.trial.suggest_float("disc_lr_mult", 0.8, 1.2), 1e-6, 1e-2)


        for bottom in bottom_agents:
            top = random.choice(top_agents)
            logger.info("Agent %d (Score %.2f) killed, replaced by Agent %d (Score %.2f)", bottom.id, bottom.score, top.id, top.score)
            

            bottom.gail.generator.load_state_dict(copy.deepcopy(top.gail.generator.state_dict()))
            bottom.gail.boss.load_state_dict(copy.deepcopy(top.gail.boss.state_dict()))
            bottom.gail.discriminator.load_state_dict(copy.deepcopy(top.gail.discriminator.state_dict()))
            bottom.gail.gen_optimizer.load_state_dict(copy.deepcopy(top.gail.gen_optimizer.state_dict()))
            bottom.gail.boss_optimizer.load_state_dict(copy.deepcopy(top.gail.boss_optimizer.state_dict()))
            bottom.gail.discriminator.optim.load_state_dict(copy.deepcopy(top.gail.discriminator.optim.state_dict()))
            bottom.gail.load_normalizer(copy.deepcopy(top.gail.save_normalizer()))
            
            bottom.persistent_state = copy.deepcopy(top.persistent_state)
            

            bottom.trial = self.study.ask()
            bottom.gen_lr = np.clip(top.gen_lr * bottom.trial.suggest_float("gen_lr_mult", 0.5, 2.0), 1e-6, 1e-2)
            bottom.disc_lr = np.clip(top.disc_lr * bottom.trial.suggest_float("disc_lr_mult", 0.5, 2.0), 1e-6, 1e-2)
