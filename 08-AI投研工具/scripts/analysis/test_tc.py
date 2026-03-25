import requests

def get_tencent_hk_data(codes):
    url = f"http://qt.gtimg.cn/q={','.join(codes)}"
    resp = requests.get(url, timeout=5)
    resp.encoding = 'gbk'
    lines = resp.text.strip().split('\n')
    for line in lines:
        if not line: continue
        parts = line.split('=')
        code = parts[0]
        vals = parts[1].replace('"', '').replace(';', '').split('~')
        print(f"--- {code} ---")
        for i, v in enumerate(vals[:50]):
            print(f"{i}: {v}")

get_tencent_hk_data(['hk01816', 'hk01072'])
