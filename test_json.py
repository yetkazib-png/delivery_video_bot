import json
p='service_account.json'
with open(p,'r',encoding='utf-8') as f:
    data=json.load(f)
print('OK:', data.get('client_email'))
