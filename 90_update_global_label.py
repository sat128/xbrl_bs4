import os
import re
import glob
import pandas as pd
from bs4 import BeautifulSoup

########## タクソノミファイルのファイルパスを指定 ##########
path_taxonomy = 'タクソノミを保存したファイルパスを指定してください'

########## taxonomy_global_label.tsvが保存されているパスを指定 ##########
path_global_label = 'taxonomy_global_label.tsvが保存されているファイルパスを指定してください'



def get_global_label(arg_path):
    '''
    金融庁が公開しているEDINETタクソノミから、XBRLタグ名と日本語ラベルの対応関係を示す、日本語ラベルマスタを作成する関数
    引数(arg_path)：*_lab.xmlのファイルパス
    '''
    # labファイルの読み込み
    with open(arg_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # link:locタグのみ抽出
    link_loc = soup.find_all('link:loc')

    # ラベル情報用dictを格納するカラのリストを作成
    list_locator = []

    # ラベル情報をループ処理で取得
    for each_loc in link_loc:
        dict_locator = {}
        shema = each_loc.get('xlink:href').split(sep='#')[0]
        dict_locator['xmlns_jpcrp_ymd'] = re.findall(r'\d{4}-\d{2}-\d{2}', shema)[0]
        dict_locator['xlink_href'] = each_loc.get('xlink:href')
        dict_locator['shema'] = shema
        dict_locator['label_for_join'] = each_loc.get('xlink:href').split(sep='#')[1]
        dict_locator['loc_label'] = each_loc.get('xlink:label')
        list_locator.append(dict_locator)

    # ラベル情報取得結果をDFに    
    df_locator = pd.DataFrame(list_locator)

    # link:labelArcタグのみ抽出
    link_arc = soup.find_all('link:labelarc')

    # ラベル情報用dictを格納するカラのリストを作成
    list_arc = []

    # ラベル情報をループ処理で取得
    for each_arc in link_arc:
        dict_arc = {}
        dict_arc['arc_role'] = each_arc.get('xlink:arcrole')
        dict_arc['loc_label'] = each_arc.get('xlink:from')
        dict_arc['xlink_label'] = each_arc.get('xlink:to')
        list_arc.append(dict_arc)

    # ラベル情報取得結果をDFに    
    df_arc = pd.DataFrame(list_arc)

    # link:labelタグのみ抽出
    link_label = soup.find_all('link:label')

    # ラベル情報用dictを格納するカラのリストを作成
    list_resource = []

    # ラベル情報をループ処理で取得
    for each_label in link_label:
        dict_resource = {}
        dict_resource['xlink_label'] = each_label.get('xlink:label')
        dict_resource['xlink_role'] = each_label.get('xlink:role')
        dict_resource['xml_lang'] = each_label.get('xml:lang')
        dict_resource['label_text'] = each_label.text
        list_resource.append(dict_resource)

    # ラベル情報取得結果をDFに    
    df_resource = pd.DataFrame(list_resource)

    # locとarcの結合
    df_merged = pd.merge(df_locator, df_arc, on='loc_label', how='inner')
    df_merged = pd.merge(df_merged, df_resource, on='xlink_label', how='inner')

    return df_merged
    

# ベースとなるDFの定義
df_global_label = pd.DataFrame(columns=[
    'xmlns_jpcrp_ymd', 'xlink_href', 'shema', 'label_for_join', 'loc_label',
    'arc_role', 'xlink_label', 'xlink_role', 'xml_lang', 'label_text'
    ])


# 各labファイルのパスを格納するリストの定義
list_path_taxonomy = []

# 各labファイルの検索
list_path_taxonomy.extend(glob.glob(path_taxonomy + '**/jpcrp/**/label/**_lab.xml', recursive=True))
list_path_taxonomy.extend(glob.glob(path_taxonomy + '**/jppfs/**/label/**_lab.xml', recursive=True))
list_path_taxonomy.extend(glob.glob(path_taxonomy + '**/jpigp/**/label/**_lab.xml', recursive=True))

# ループ処理で各labファイルから日本語ラベルマスタを作成
for each_label in list_path_taxonomy:
    print('現在実行中のファイル： ' + os.path.basename(each_label))
    df_tmp = get_global_label(each_label)
    df_global_label = pd.concat([df_global_label, df_tmp])

# 既存ファイル（taxonomy_global_label.tsv）の末尾に最新マスタを追記
df_global_label.to_csv(path_global_label, sep ='\t', encoding='UTF-8', mode='a', header=False, index=False)


