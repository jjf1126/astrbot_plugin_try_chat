import sys
import os
sys.path.append("/AstrBot")
from astrbot.core.star.star import star_registry
print([s.name for s in star_registry])
