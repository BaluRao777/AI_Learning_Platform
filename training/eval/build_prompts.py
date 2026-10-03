"""Write training/eval/prompts.json: 20 evaluation topics x 4 level/mode combinations = 80 prompts.

    python training/eval/build_prompts.py

Prompts are built with the application's prompt construction
(backend/services/image_backends/sana_prompt.py) and the rule-based plan for
each combination. The topic descriptions were written for evaluation; they are
not copied from the training captions.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import COMBOS, build_prompts  # noqa: E402

TOPICS = {
    "Photosynthesis": "a green plant leaf taking in sunlight, water and carbon dioxide and giving out oxygen and sugar",
    "Water cycle": "the water cycle with evaporation from the sea, cloud formation, rainfall over mountains and rivers returning to the sea",
    "Structure of the Earth": "a cutaway of the Earth showing the crust, mantle, outer core and inner core as concentric layers",
    "Human heart": "the human heart with four chambers, major blood vessels and arrows showing the direction of blood flow",
    "Plant cell": "a plant cell with cell wall, nucleus, chloroplasts, large vacuole and mitochondria",
    "Solar system": "the Sun with the eight planets on their orbits in order of distance",
    "Volcano": "a cross-section of an erupting volcano with magma chamber, vent, lava flow and ash cloud",
    "Human digestive system": "the human digestive system from mouth through oesophagus, stomach and intestines",
    "Food chain": "a food chain from grass to grasshopper to frog to snake to eagle connected by arrows",
    "Electric circuit": "a simple electric circuit with a battery, a switch, connecting wires and a glowing bulb",
    "Refraction of light": "a ray of light bending as it passes from air into a glass block and out again",
    "Atom structure": "an atom with protons and neutrons in the nucleus and electrons on shells around it",
    "DNA double helix": "a DNA double helix with two twisted strands joined by paired bases",
    "Rock cycle": "the rock cycle linking igneous, sedimentary and metamorphic rocks with arrows for melting, erosion and pressure",
    "Neuron": "a nerve cell with dendrites, cell body, long axon with myelin sheath and axon terminals",
    "Human respiratory system": "the human respiratory system with nose, trachea, bronchi, two lungs and diaphragm",
    "Phases of the Moon": "the Moon at eight positions around the Earth showing its phases as lit by the Sun",
    "Plate tectonics": "two tectonic plates colliding, one sliding under the other, forming mountains and a deep ocean trench",
    "Life cycle of a butterfly": "the life cycle of a butterfly from egg to caterpillar to chrysalis to adult butterfly arranged in a circle",
    "Greenhouse effect": "sunlight entering the Earth's atmosphere and heat being trapped by a layer of greenhouse gases",
}


def main():
    prompts = []
    for topic, description in TOPICS.items():
        for level, mode in COMBOS:
            plain, with_trigger, seed = build_prompts(description, level, mode)
            prompts.append({"id": len(prompts), "topic": topic, "level": level, "mode": mode,
                            "prompt": plain, "lora_prompt": with_trigger, "seed": seed})
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(prompts, fh, indent=2)
    print(len(prompts), "prompts ->", path)


if __name__ == "__main__":
    main()
