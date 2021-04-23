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

    docid = [doc[0] for doc in docis]
    conts = origin_data.loc[origin_data['id'].isin(docid)]
    print(conts)
