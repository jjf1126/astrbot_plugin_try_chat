import json

schema_path = '/AstrBot/data/plugins/astrbot_plugin_try_chat/_conf_schema.json'
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = json.load(f)

schema['decision_memory_keyword'] = {
    "default": "最近的约定",
    "description": "判定时记忆搜索关键词",
    "hint": "在判断是否适合聊天时，调用记忆插件使用的固定搜索关键词。",
    "type": "string"
}

with open(schema_path, 'w', encoding='utf-8') as f:
    json.dump(schema, f, ensure_ascii=False, indent=4)
print("Schema updated")
