#!/usr/bin/env python3
"""Entropy Garden — generates a random algorithm + seed for the live canvas animation."""
import random
from utils import today, write_feed, feed_exists

ALGORITHMS = [
    ("dla", "diffusion-limited aggregation"),
    ("flow_field", "Perlin flow field"),
    ("cellular", "Rule 110 cellular automaton"),
    ("game_of_life", "Conway's Game of Life"),
]

def generate():
    name = f"{today()}-entropy-garden"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    algo, desc = random.choice(ALGORITHMS)
    seed = random.randint(1, 0xFFFFFFFF)
    
    write_feed(name, {
        "type": "entropy_garden",
        "timestamp": f"{today()}T23:00:00",
        "algorithm": algo,
        "seed": seed,
        "meta": f"{desc} · seed 0x{seed:08x} · von Neumann neighborhood",
    })

if __name__ == '__main__':
    generate()
