import json
import os

with open('cache_map.json', 'r') as f:
    data = json.load(f)

for key in ['4', '5', '6', '7', '12']:
    if key in data:
        del data[key]

with open('cache_map.json', 'w') as f:
    json.dump(data, f)
    
print("Purged bad cache entries!")
