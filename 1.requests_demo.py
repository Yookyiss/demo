import requests

# 发起GET 类型请求
# base_url = 'http://www.baidu.com'
# base_url = 'https://www.hao123.com/'
# base_url = 'http://www.xicidaili.com'
base_url = 'http://www.baidu.com/s?wd=ip'

headers = {
    'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'
}

proxy = {
    'http' : 'http://alice:123456@120.78.166.84:6666',
    'https' : 'http://alice:123456@120.78.166.84:6666',
}

# 加上请求头和代理
response = requests.get(base_url,headers=headers,proxies=proxy)
response.encoding = 'utf-8'

# print(type(response.content)) # 返回btyes
# print(type(response.text)) # 返回str
print(response.text)

# 发起POST 请求
# requests.post()
