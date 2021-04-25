import requests
from lxml import etree
import pandas as pd
import configparser
import re
import time
import math
import json
import jieba

class DataLoader():
    '''grab data from website, the format of data is as follows:
    |---------------------------------------------------|
    |    id    |     link   |     cont     |    title   |
    |---------------------------------------------------|
    |  page id |  page link | page content | page title |
    |---------------------------------------------------|
    |  ......  |   ......   |    ......    |   ......   |
    |---------------------------------------------------|
    '''
    def __init__(self, option):
        config = configparser.ConfigParser()
        config.read(option['filepath'], option['encoding'])
        self.option = option
        self.config = config

        self.data_path = config['PATH']['data']
        self.data = []

    def get_entry(self):
        baseurl = 'http://his.cssn.cn/lsx/sjls/'
        entries = []
        for idx in range(5):
            entry = baseurl if idx == 0 else baseurl + 'index_' + str(idx) + '.shtml'
            entries.append(entry)
        return entries

    def parse4links(self, entries):
        links = []
        headers = {
            'USER-AGENT': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        }
        for entry in entries:
            try:
                response = requests.get(url = entry, headers = headers)
                html = response.text.encode(response.encoding).decode('utf-8')
                time.sleep(0.5)
            except:
                continue

            html_parser = etree.HTML(html)
            link = html_parser.xpath('//div[@class="ImageListView"]/ol/li/a/@href')
            link_filtered = [url for url in link if 'www' not in url]
            link_complete = [entry + url.lstrip('./') for url in link_filtered]
            links.extend(link_complete)

        return links

    def parse4datas(self, entries):
        datas = []
        headers = {
            'USER-AGENT': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        }
        data_count = 0
        for entry in entries:
            try:
                response = requests.get(url = entry, headers = headers)
                html = response.text.encode(response.encoding).decode('utf-8')
                time.sleep(0.2)
            except:
                continue

            html_parser = etree.HTML(html)
            title = html_parser.xpath('//span[@class="TitleFont"]/text()')
            content = html_parser.xpath('//div[@class="TRS_Editor"]//p//text()')
            content = [cont.replace('\u3000', '').replace('\xa0', '').replace('\n', '').replace('\t', '') for cont in content]
            content = [cont for cont in content if len(cont) > 30 and not re.search(r'[《|》]', cont)]

            if len(title) != 0 or len(content) != 0:
                data_count += 1
                datas.append({
                    'id'  : data_count,
                    'link': entry,
                    'cont': '\t'.join(content),
                    'title': title[0]
                })

        return datas

    def grab_data(self):
        entries = self.get_entry()
        links = self.parse4links(entries)
        datas = self.parse4datas(links)
        self.data = pd.DataFrame(datas)

    def save_data(self):
        self.data.to_csv(self.data_path, index = None)

class IndexModel():
    '''convert data to inverted index(iindex), the format of iindex is as follows:
    {
        word: {
            'df': document_frequency,
            'ds': [{
                'id': document_id,
                'dl': document_length,
                'tf': term_frequency
            }, ...]
        },
        ...
    }
    '''
    def __init__(self, option):
        config = configparser.ConfigParser()
        config.read(option['filepath'], option['encoding'])
        self.option = option
        self.config = config

        self.data_path = config['PATH']['data']
        self.iindex_path = config['PATH']['iindex']
        self.stopword_path = config['PATH']['stopword']

        self.stopwords = self.load_stopwords()
        self.iindex = {}

    def load_stopwords(self):
        with open(self.stopword_path, 'r', encoding = 'utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def format(self, contents):
        doc_dict = {}
        contents = [word for word in contents if word not in self.stopwords]
        for word in contents:
            if word in doc_dict:
                doc_dict[word] = doc_dict[word] + 1
            else:
                doc_dict[word] = 1
        return doc_dict

    def make_iindex(self):
        df = pd.read_csv(self.data_path)
        TOTAL_DOC_NUM = 0
        TOTAL_DOC_LEN = 0
        for row in df.itertuples():
            doc_id = getattr(row, 'id')
            cont = getattr(row, 'cont')

            TOTAL_DOC_NUM += 1
            TOTAL_DOC_LEN += len(cont)

            cuts = jieba.lcut_for_search(cont)
            word2freq = self.format(cuts)
            for word in word2freq:
                meta = {
                    'id': doc_id,
                    'dl': len(word2freq),
                    'tf': word2freq[word]
                }
                if word in self.iindex:
                    self.iindex[word]['df'] = self.iindex[word]['df'] + 1
                    self.iindex[word]['ds'].append(meta)
                else:
                    self.iindex[word] = {}
                    self.iindex[word]['df'] = 1
                    self.iindex[word]['ds'] = []
                    self.iindex[word]['ds'].append(meta)

        self.config.set('DATA', 'TOTAL_DOC_NUM', str(TOTAL_DOC_NUM))
        self.config.set('DATA', 'AVG_DOC_LEN', str(TOTAL_DOC_LEN / TOTAL_DOC_NUM))
        with open(self.option['filepath'], 'w', encoding = self.option['encoding']) as config_file:
            self.config.write(config_file)

    def save_iindex(self):
        fd = open(self.iindex_path, 'w', encoding = 'utf-8')
        json.dump(self.iindex, fd, ensure_ascii = False)
        fd.close()

class SearchEngine():
    def __init__(self, option):
        config = configparser.ConfigParser()
        config.read(option['filepath'], option['encoding'])
        self.option = option
        self.config = config

        self.iindex_path = config['PATH']['iindex']
        self.stopword_path = config['PATH']['stopword']

        self.stopwords = self.load_stopwords()
        self.iindex = self.read_iindex()

        self.N = float(config['DATA']['TOTAL_DOC_NUM'])
        self.AVGDL = float(config['DATA']['AVG_DOC_LEN'])

        self.k1 = float(config['PARA']['k1'])
        self.k2 = float(config['PARA']['k2'])
        self.b  = float(config['PARA']['b'])

    def load_stopwords(self):
        with open(self.stopword_path, 'r', encoding = 'utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def read_iindex(self):
        with open(self.iindex_path, 'r', encoding = 'utf-8') as f:
            return json.load(f)

    def format(self, contents):
        doc_dict = {}
        contents = [word for word in contents if word not in self.stopwords]
        for word in contents:
            if word in doc_dict:
                doc_dict[word] = doc_dict[word] + 1
            else:
                doc_dict[word] = 1
        return doc_dict

    def search(self, query):
        '''BM25
        detail information can refer to https://en.wikipedia.org/wiki/Okapi_BM25
        '''
        query = jieba.lcut_for_search(query)
        word2freq = self.format(query)
        BM25_scores = {}
        for word in word2freq:
            data = self.iindex.get(word)
            if not data:
                continue
            BM25_score = 0
            qf = word2freq[word]
            df = data['df']
            ds = data['ds']
            W = math.log((self.N - df + 0.5) / (df + 0.5))
            for doc in ds:
                doc_id = doc['id']
                tf = doc['tf']
                dl = doc['dl']
                K = self.k1 * (1 - self.b + self.b * (dl / self.AVGDL))
                R = (tf * (self.k1 + 1) / (tf + K)) * (qf * (self.k2 + 1) / (qf + self.k2))
                BM25_score = W * R
                BM25_scores[doc_id] = BM25_scores[doc_id] + BM25_score if doc_id in BM25_scores else BM25_score

        BM25_scores = sorted(BM25_scores.items(), key = lambda item: item[1])
        BM25_scores.reverse()
        return BM25_scores
