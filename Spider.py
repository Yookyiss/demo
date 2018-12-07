import threading
from queue import Queue
import requests
from lxml import etree
from urllib import request
import json
import time
import random


# 采集线程类
class Crawl(threading.Thread):
    headers = {}

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
            response = requests.get(url,headers=self.headers)
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
                    # print(html)
                except Exception as e:
                    html = None

                if html is not None:
                    self.parse(html)
            else:
                break
        print('%d号解析线程结束' % self.number)

    def parse(self,html):
        pass