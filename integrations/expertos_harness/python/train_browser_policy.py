import argparse
import json
from pathlib import Path
from expertos_bridge.action_policy import train

p=argparse.ArgumentParser(description='Train experimental small browser-action policy')
p.add_argument('--data',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--epochs',type=int,default=10)
p.add_argument('--demo',action='store_true')
a=p.parse_args()
examples=[json.loads(row) for row in a.data.read_text(encoding='utf-8').splitlines() if row.strip()]
print(json.dumps(train(examples,a.output,epochs=a.epochs,demo=a.demo),indent=2))
