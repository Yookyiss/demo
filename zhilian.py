import requests
import re
import threading
from queue import Queue
from lxml import etree
import datetime
import pymysql
import time





class Crawl(threading.Thread):
    def __init__(self,task_q,data_q):
        super(Crawl, self).__init__()
        self.task_q = task_q
        self.date_q = data_q
    def run(self):
        while not self.task_q.empty():
            full_url = self.task_q.get()
            self.downloader(full_url)
        print('task_over')


    def downloader(self,full_url):
        response = requests.get(full_url)
        response.encoding = 'utf-8'
        self.date_q.put(response.text)

class Parse(threading.Thread):
    def __init__(self,data_q,crawl_list,lock,connect):
        super(Parse, self).__init__()
        self.date_q = data_q
        self.crawl_list = crawl_list
        self.lock = lock
        self.connect = connect
        self.cursor = self.connect.cursor()
        self.switch = True
        self.item = {}
        self.pattern = re.compile(r'\d+')
    def run(self):
        while self.switch:
            for i in self.crawl_list:
                if i.is_alive():
                    break
            else:
                if self.date_q.empty():
                    print('false')
                    self.switch = False
                    break
            try:
                html = self.date_q.get(timeout=3)
                self.parse(html)
            except Exception as e:
                print(e)
                continue
        print('data_over')


    def parse(self,html):
        print('ok')
        # 从所得json数据中解析职位路由的正则
        pattern = re.compile(r'https://jobs.zhaopin.com/.*?htm')
        res = pattern.findall(html)
        # 访问职位地址并且解析
        for i in res:
            print(i)
            response = requests.get(i)
            response.encoding = 'utf-8'
            self.info_parse(response)



    def info_parse(self,response):
        html = etree.HTML(response.text)


        # 处理所得数据 个别页面布局特殊 为节省代码 用try
        try:

            self.item['job_name'] = html.xpath('//h1[@class="l info-h3"]/text()')[0]
            self.item['salary_low'], self.item['salary_top'] = self.process_money(html.xpath('//div[@class="l info-money"]/strong/text()')[0])
            self.item['location'] = html.xpath('//div[@class="info-three l"]/span[1]')[0]
            self.item['location'] = self.item['location'].xpath('string(.)')
            self.item['work_years_low'], self.item['work_years_top'] = self.process_years(
                    html.xpath('//div[@class="info-three l"]/span[2]/text()')[0])
            self.item['education'] = html.xpath('//div[@class="info-three l"]/span[2]/text()')[0]
            self.item['nature'] = '实习' if '实习' in html.xpath('//h1[@class="l info-h3"]/text()')[0] else '全职'
            self.item['date_time'] = datetime.datetime.now().strftime('%Y-%m-%d')
            self.item['work_desc'] = html.xpath('//div[@class="pos-ul"]')[0]
            self.item['work_desc'] = self.item['work_desc'].xpath('string(.)')
            self.item['address'] = html.xpath('//ul[@class="promulgator-ul cl"]/li')[-1]
            self.item['address'] = self.item['address'].xpath('string(.)').strip()

            self.item['company'] = html.xpath('//h3/a/text()')[0]
            self.item['crawl_time'] = datetime.datetime.now().strftime('%Y-%m-%d')
            self.item['url'] = response.url
            self.item['info_from'] = '智联'
            rule = re.compile(r"var JobWelfareTab = '(.*?)';")
            res = rule.search(response.text).group(1)
            self.item['lure'] = res


            sql = 'insert into job_copy(url,job_name,salary_low,salary_top,location,work_years_low,work_years_top,education,nature,info_from,date_time,work_desc,address,company,crawl_time,lure) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on duplicate key update salary_low=VALUES(salary_low),salary_top=values(salary_top)'

            # 获取线程锁 防止存入mysql发生混乱
            self.lock.acquire()
            # try防止因为sql语句错误导致线程锁得不到释放，从而使整个“进程”卡死
            try:
                self.cursor.execute(sql,(self.item["url"],self.item["job_name"],self.item["salary_low"],self.item["salary_top"],self.item["location"],self.item["work_years_low"],self.item["work_years_top"],self.item["education"],self.item["nature"],self.item["info_from"],self.item["date_time"],''.join(self.item["work_desc"]),self.item["address"],self.item["company"],self.item["crawl_time"],self.item['lure']))
                self.connect.commit()
            except:
                print('sql error')
            self.lock.release()
        except Exception as e:
            print(e)




    def process_money(self,response):
        if '面议' in response:
            return 0,0
        salary_low = response.split('/')[0].split('-')[0]
        salary_top = self.pattern.search(response.split('/')[0].split('-')[1]).group()
        # print(salary_top)
        return salary_low,salary_top

    def process_years(self,response):
        if '不限' in response or '无' in response:
            low = 0
            top = 0
        elif '以上' in response:
            low = self.pattern.search(response).group()
            top = 100
        elif '以下' in response:
             top = self.pattern.search(response).group()
             low = 0
        else:
            base = response.split('-')
            low = base[0]
            top = self.pattern.search(base[1]).group()
        return low,top




def main():
    connect = pymysql.connect('localhost','root','123456','mydb')
    lock = threading.Lock()
    #智联api数据接口 参数为最新发布的全国地区的数据
    base_url = 'https://fe-api.zhaopin.com/c/i/sou?start=%d&pageSize=60&cityId=489&workExperience=-1&education=-1&companyType=-1&employmentType=-1&jobWelfareTag=-1&kt=3&_v=0.37511224&x-zp-page-request-id=589651eb69c74209af8d444aaa83d330-1542016984843-602865'
    task_q = Queue()
    data_q = Queue()
    for i in range(200):
        full_url = base_url % (i * 60)
        task_q.put(full_url)

    crawl_list = []
    parse_list = []
    # 爬取职位地址的线程
    for i in range(10):
        re = Crawl(task_q, data_q)
        re.start()
        crawl_list.append(re)
    # 访问职位地址并且解析和存入数据库的线程
    for i in range(100):
        re = Parse(data_q,crawl_list,lock,connect)
        re.start()
        parse_list.append(re)
    # 等待爬取职位地址的线程 全部结束
    for i in crawl_list:
        i.join()
    # 等待访问职位地址并且解析和存入数据库的线程 全部结束
    for i in parse_list:
        i.join()
    connect.commit()



if __name__ == '__main__':


    main()






