from Spider import Crawl,Parse
from queue import Queue
import threading
from bs4 import BeautifulSoup

class TencentCrawl(Crawl):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'
    }

class TencentParse(Parse):
    def parse(self,html):
        html = BeautifulSoup(html,'lxml')
        tr_list = html.select('table.tablelist tr')[1:-1]
        for tr in tr_list:
            td_list = tr.select('td')
            job_name = td_list[0].a.text
            self.f.write(job_name + '\n')

def main():
    concurrent = 20
    conparse = 3
    task_q = Queue()  # 任务队列
    data_q = Queue()  # 数据队列
    f = open('tencent.json','w',encoding='utf-8')

    # 创建一个锁
    lock = threading.Lock()
    # lock.aquire()


    base_url = 'http://hr.tencent.com/position.php?start=%d'

    # 创建任务
    for i in range(0,990 + 1,10):
        fullurl = base_url % i
        task_q.put(fullurl)

    # 创建采集线程
    crawl_thread_list = []
    for i in range(concurrent):
        t = TencentCrawl(i + 1,task_q,data_q)
        t.start() # 启动线程
        crawl_thread_list.append(t)

    # 创建解析线程
    parse_thread_list = []
    for i in range(conparse):
        t = TencentParse(i + 1,crawl_thread_list,data_q,f,lock)
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