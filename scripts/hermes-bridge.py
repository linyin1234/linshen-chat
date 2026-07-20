#!/usr/bin/env python3
import json,sys,os,urllib.request,datetime
D='https://api.deepseek.com/v1/chat/completions'
K='DEEPSEEK_KEY_REMOVED'
P='/opt/linshen/scripts/hermes-tasks.json'
def main():
 t=sys.stdin.read().strip()
 if not t:sys.exit(1)
 b={'model':'deepseek-chat','messages':[{'role':'system','content':'你是林深助手。简洁温暖。'},{'role':'user','content':f'任务:{t}'}],'max_tokens':1024}
 try:
  r=urllib.request.Request(D,json.dumps(b).encode(),{'Content-Type':'application/json','Authorization':f'Bearer {K}'})
  print(json.loads(urllib.request.urlopen(r,timeout=60).read())['choices'][0]['message']['content'])
 except Exception as e:
  x=json.load(open(P)) if os.path.exists(P) else []
  x.append({'time':datetime.datetime.now().isoformat(),'task':t,'status':'pending'})
  json.dump(x,open(P,'w'),ensure_ascii=False,indent=2)
  print('saved')
if __name__=='__main__':main()
