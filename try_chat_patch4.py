import os

with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """
            has_living_memory = False
            for star in self.context.get_all_stars():
                if star.name == "LivingMemory":
                    has_living_memory = True
                    break
"""

new_code = """
            has_living_memory = False
            for star in self.context.get_all_stars():
                if star.name and "livingmemory" in star.name.lower():
                    has_living_memory = True
                    break
"""

content = content.replace(old_code, new_code)
with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch 4 applied.")
