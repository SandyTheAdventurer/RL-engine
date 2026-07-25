from collections import deque
import numpy as np


class ExpertBuffer:
    """Moving window of recent expert matches for GAIL.

    Whole matches are stored so eviction never splits a trajectory and
    match boundaries survive as done flags for the LSTM discriminator.
    The newest match is always kept, even if it alone exceeds max_frames.
    """

    def __init__(self, max_matches=8, max_frames=4096):
        self.max_matches = max_matches
        self.max_frames = max_frames
        self.matches = deque()

    def __len__(self):
        return sum(len(obs) for obs, _ in self.matches)

    def add_match(self, obs, actions):
        if len(obs) == 0:
            return
        self.matches.append((np.asarray(obs, dtype=np.float32),
                             np.asarray(actions, dtype=np.float32)))
        while len(self.matches) > 1 and (
                len(self.matches) > self.max_matches or len(self) > self.max_frames):
            self.matches.popleft()

    def arrays(self):
        """Concatenated (obs, actions, dones); dones[t]=1 marks the first
        frame of a match, where the discriminator resets its LSTM state."""
        obs = np.concatenate([m[0] for m in self.matches])
        actions = np.concatenate([m[1] for m in self.matches])
        dones = np.zeros(len(obs), dtype=np.float32)
        idx = 0
        for m in self.matches:
            dones[idx] = 1.0
            idx += len(m[0])
        return obs, actions, dones
