import pandas as pd
import configparser
from models import DataLoader, IndexModel, SearchEngine

config_option = {
    'filepath': 'config.ini',
    'encoding': 'utf-8'
}
config = configparser.ConfigParser()
config.read(config_option['filepath'], config_option['encoding'])

# 数据模型：爬取和保存数据
data_loader = DataLoader(config_option)
print('grab data ...')
data_loader.grab_data()
print('save data ...')
data_loader.save_data()

# 索引模型：构建和保存索引
index_model = IndexModel(config_option)
print('make iindex ...')
index_model.make_iindex()
print('save iindex ...')
index_model.save_iindex()

# 搜索模型
search_engine = SearchEngine(config_option)
origin_data = pd.read_csv(config['PATH']['data'])
while True:
    query = input('Please Input Query: ')
    docis = search_engine.search(query)

    result = []
    max_num = 10
    max_len = 100
    for idx, doc in enumerate(docis):
        if idx >= max_num:
            break
        docid = doc[0]
        score = doc[1]
        result.append({
            'id': docid,
            'sc': score,
            'link': origin_data.at[docid, 'link'],
            'cont': origin_data.at[docid, 'cont'][:max_len] + '...',
            'title': origin_data.at[docid, 'title']
        })
    print(result)
