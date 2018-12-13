

f = '{"responseMessage":"暂存成功！","responseCode":"1","cusCiqNo":"I20180000000035872","preEntryId":""}'
import json

t = json.loads(f)
print(t)

for i,v in enumerate(t):
    print(i)
    print(v)
