import threading
from queue import Queue
import requests
from lxml import etree
from urllib import request
import json
import time
import random

concurrent = 3 # 定义并发采集线程数
conparse = 1 # 并发解析线程数

# 采集线程类
class Crawl(threading.Thread):
    def __init__(self,number,task_q,data_q):
        super(Crawl, self).__init__()
        self.number = number # 线程编号
        self.task_q = task_q
        self.data_q = data_q

    # 线程对象调用start方法时候被调用
    def run(self):
        print('%d号采集线程启动' % self.number)
        while not self.task_q.empty():
            fullurl = self.task_q.get()
            print('%d号线程采集：%s' % (self.number,fullurl))
            self.downloader(fullurl)
        print('%d号采集线程结束' % self.number)

    # 下载器
    def downloader(self,url,retry=3):
        try:
            response = requests.get(url)
            html = response.text
            time.sleep(random.random() * 3)
        except Exception as e:
            if retry > 0:
                return self.downloader(url,retry - 1)
            else:
                html = None
        if html is not None:
            self.data_q.put(html)

# 解析线程类
class Parse(threading.Thread):
    def __init__(self,number,task_thread_list,data_q,f,lock):
        super(Parse, self).__init__()
        self.data_q = data_q
        self.task_thread_list = task_thread_list
        self.number = number
        self.f = f
        self.is_parse = True
        self .lock = lock
    def run(self):
        print('%d号解析线程启动' % self.number)
        while self.is_parse:
            for t in self.task_thread_list:
                if t.is_alive(): # 判断是否存活
                    break
            else: # 没有执行break语句就进入else
                if self.data_q.empty():
                    self.is_parse = False

            if self.is_parse: # 有可能两个线程都进入判断，但是数据队列只有一个
                try:
                    html = self.data_q.get(timeout=1)
                    html = etree.HTML(html)
                except Exception as e:
                    print('no')
                    html = None

                if html is not None:
                    self.parse(html)
            else:
                break
        print('%d号解析线程结束' % self.number)

    def parse(self,html):
        # 获取所有段子div
        duanzi_div = html.xpath('//div[@id="content-left"]/div')

        for duanzi in duanzi_div:
            nick = duanzi.xpath('.//h2/text()')[0].strip('\n')
            age = duanzi.xpath(
                './/div[@class="articleGender womenIcon"]/text() | .//div[@class="articleGender manIcon"]/text()')
            age = age[0] if age else 0

            gender = duanzi.xpath('.//div[@class="author clearfix"]/div/@class')
            gender = gender[0] if gender else '中'
            if 'man' in gender:
                gender = '男'
            elif 'women' in gender:
                gender = '女'
            # 获取内容的span
            if duanzi.xpath('.//span[@class="contentForAll"]'):  # 有详情页
                detail_url = duanzi.xpath('.//a[@class="contentHerf"]/@href')[0]
                # detail_url = request.urljoin(response.url, detail_url)
                detail_url = 'https://www.qiushibaike.com' + detail_url
                # print(detail_url)
                response = requests.get(detail_url)
                con_html = response.text
                # print(con_html)
                con_html = etree.HTML(con_html)

                con_div = con_html.xpath('//div[@class="content"]')[0]

                content = con_div.xpath('string(.)').strip()

            else:  # 直接获取全部段子内容
                span = duanzi.xpath('.//div[@class="content"]/span')[0]
                content = span.xpath('string(.)').strip()

            laugh = duanzi.xpath('.//span[@class="stats-vote"]/i/text()')[0]
            comment = duanzi.xpath('.//span[@class="stats-comments"]//i/text()')[0]

            # 段子图片
            duanzi_pic = duanzi.xpath('.//duanzi[@class="illustration"]/@src')
            if duanzi_pic:
                pic_url = duanzi_pic[0]
                pic_url = request.urljoin(response.url, pic_url)

                # 下载段子图片
                fname = pic_url.split('/')[-1]
                request.urlretrieve(pic_url, './duanzi/' + fname)
            else:
                fname = ''
            # print(content)

            item = {
                'nick': nick,
                'age': age,
                'gender': gender,
                'content': content,
                'laugh': laugh,
                'comment': comment,
                'pic': fname
            }
            # 存储操作
            self.f.write(json.dumps(item, ensure_ascii=False) + '\n')


def main():
    task_q = Queue()  # 任务队列
    data_q = Queue()  # 数据队列
    f = open('duanzi.json','w',encoding='utf-8')

    # 创建一个锁
    lock = threading.Lock()
    # lock.aquire()


    base_url = 'https://www.qiushibaike.com/8hr/page/%d/'

    # 创建任务
    for i in range(1,5):
        fullurl = base_url % i
        task_q.put(fullurl)

    # 创建采集线程
    crawl_thread_list = []
    for i in range(concurrent):
        t = Crawl(i + 1,task_q,data_q)
        t.start() # 启动线程
        crawl_thread_list.append(t)

    # 创建解析线程
    parse_thread_list = []
    for i in range(conparse):
        t = Parse(i + 1,crawl_thread_list,data_q,f,lock)
        t.start()
        parse_thread_list.append(t)

    # 等待线程执行完毕
    for t in crawl_thread_list:
        t.join()
    # 解析线程
    for t in parse_thread_list:
        t.join()

    f.close()


if __name__ == '__main__':
    main()
