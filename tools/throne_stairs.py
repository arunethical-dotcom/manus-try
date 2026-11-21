import numpy as np


def align_treads(sprite):
    """Repair the vertical join in the 1459-pixel-wide Throne Hall exterior."""
    if sprite.shape[1] != 1459:
        raise ValueError("Stair repair coordinates require the 1459 px exterior")
    left, right = 729, 815
    source = sprite[1466:, left+104:right+104].astype(float)
    target = sprite[1466:, left:right]
    x = np.arange(left, right)
    mix = np.minimum(np.clip((x-left)/45, 0, 1), np.clip((right-1-x)/12, 0, 1))
    blend = mix[None, :, None]
    target[:] = np.rint(target * (1-blend) + source * blend)
