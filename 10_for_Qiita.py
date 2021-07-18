import os
import re
import glob
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

# パスの指定
path_base = '****' # baseとなるディレクトリの指定。個々のdocidが付されたフォルダが格納された階層を指定することを想定しています。
if path_base[-1] != '/':
    path_base = path_base + '/'

path_taxonomy_labels = '****/taxonomy_global_label.tsv' # Gitに乗せたtsvファイルをローカルに保存して当該パスを指定してください。


def get_keys(arg_docid):
    path_target = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/0000000_**.htm')[0]
    # カラの辞書を作成
    dict_key = {}

    # docIDを取得
    dict_key['docID'] = re.findall('S\w{7}', path_target)[0]

    # 必要なファイル名部分だけに絞る
    filename = os.path.basename(path_target)

    # 府令コードは`jp`以降の3文字
    dict_key['ordinance'] = filename[filename.find('jp') + 2 : filename.find('jp') + 5]
    # 判定基準：数字6桁 & 直後が`-`
    dict_key['formCode'] = re.findall('\d{6}-', filename)[0][0:6]
    # 判定基準：英数字3桁 & 直前が`-` & 直後が`-`
    dict_key['reporting_id'] = re.findall('-\w{3}-', filename)[0][1:4]
    # 判定基準：数字3桁 & 直前が`-` & 直後が`_` の1個目
    dict_key['sequence_n1'] = re.findall('-\d{3}_', filename)[0][1:4]
    # 判定基準：英数字1桁 & 数字5桁 & 直前が`_` & 直後が`-`
    dict_key['edinetCode'] = re.findall('_\w{1}\d{5}-', filename)[0][1:7]
    # 判定基準：数字3桁 & 直前が`-` & 直後が`_` の2個目
    dict_key['sequence_n2'] = re.findall('-\d{3}_', filename)[1][1:4]
    # 判定基準：YYYY-MM-DD の1個目
    dict_key['periodend'] = re.findall('\d{4}-\d{2}-\d{2}', filename)[0]
    # 判定基準：数字2桁 & 直前が`_` & 直後が`_`
    dict_key['report_his'] = re.findall('_\d{2}_', filename)[0][1:3]
    # 判定基準：YYYY-MM-DD の2個目
    dict_key['submitdate'] = re.findall('\d{4}-\d{2}-\d{2}', filename)[1]

    # 横持のDFに変換
    df_key = pd.DataFrame(pd.Series(dict_key)).T

    return df_key


def get_dei(arg_docid):
    path_header = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/0000000_**.htm')

    # headerファイルの読み込み
    with open(path_header[0], encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # header内の情報を取得
    ix_header = soup.find_all('ix:header')
    # header内のhidden内の情報取得
    ix_hidden = ix_header[0].find_all('ix:hidden')
    # hidden内のnonnumeric, nonfractionタグを取得
    ix_hidden_nonnumeric = ix_hidden[0].find_all('ix:nonnumeric')
    ix_hidden_nonfraction = ix_hidden[0].find_all('ix:nonfraction')

    # DEI情報を格納するカラの辞書オブジェクト作成
    dict_dei = {}

    # nonnumericタグの情報（定性情報）を辞書に格納
    # タグ内のnameを辞書のキーに、表示されるテキストを値に格納
    for dei in ix_hidden_nonnumeric:
        dict_dei[dei.get('name')] = dei.text

    # nonfractionタグの情報（定量情報）を辞書に格納
    # タグ内のnameを辞書のキーに、表示されるテキストを値に格納
    for dei in ix_hidden_nonfraction:
        dict_dei[dei.get('name')] = dei.text

    # 横持ちのデータフレームに変換
    df_dei = pd.DataFrame(pd.Series(dict_dei)).T

    # DEIに含まれる情報のうち、EDINETコードと会社名に絞る
    df_dei = df_dei[['jpdei_cor:EDINETCodeDEI', 'jpdei_cor:FilerNameInJapaneseDEI', 'jpdei_cor:AccountingStandardsDEI', 'jpdei_cor:DocumentTypeDEI']]
    df_dei = df_dei.rename(columns={'jpdei_cor:EDINETCodeDEI': 'edinetCode', 'jpdei_cor:FilerNameInJapaneseDEI': 'companyName', 'jpdei_cor:AccountingStandardsDEI': 'GAAP', 'jpdei_cor:DocumentTypeDEI': 'DocType'})

    return df_dei



# 財務諸表の要素タグからDFを返す関数。
def parse_nonfra(arg_tags):
    # 各fsの各要素を格納した辞書を入れるカラのリスト作成
    list_fs = []
    # 各fsの各要素を辞書に格納
    for each_item in arg_tags:
        dict_fs = {}
        dict_fs['account_item_ns'] = each_item.get('name').split(':')[0]
        dict_fs['account_item'] = each_item.get('name').split(':')[1]
        dict_fs['contextRef'] = each_item.get('contextref')
        dict_fs['format'] = each_item.get('format')
        dict_fs['decimals'] = each_item.get('decimals')
        dict_fs['scale'] = each_item.get('scale')
        dict_fs['unitRef'] = each_item.get('unitref')
        # マイナス表記の場合の処理＋円単位への変更
        if each_item.get('sign') == '-' and each_item.get('xsi:nil') != 'true' and int(each_item.get('decimals')) < 0:
            amount = int(float(each_item.text.replace(',', '')) * -1 * 10 ** int(each_item.get('scale')))
        elif each_item.get('xsi:nil') != 'true' and int(each_item.get('decimals')) < 0:
            amount = int(float(each_item.text.replace(',', '')) * 10 ** int(each_item.get('scale')))
        elif each_item.get('xsi:nil') == 'true':
            amount = ''
        else:
            amount = each_item.text.replace(',', '')
        dict_fs['amount'] = amount
        # 辞書をリストへ格納
        list_fs.append(dict_fs)

    # 辞書を格納したリストをDFに
    df_eachfs = pd.DataFrame(list_fs)

    return df_eachfs


# XBRLのパスから、DFを返す関数本体。
def get_nonfra(arg_docid):

    # 各財務諸表を入れるカラのDFを作成
    list_fs = []
    # 対象ファイルの取得
    list_xbrl_fs = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/**.htm')

    if list_xbrl_fs:
        for arg_path in list_xbrl_fs:
            # ヘッダ情報から得られるnonfraction情報は提出回数のみで、提出回数はファイル名から取得できるためヘッダはパスする。
            if '0000000_header' in arg_path:
                pass
            else:
                # fsファイルの読み込み。bs4でパース
                with open(arg_path, encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'lxml')
            
                # nonNumericタグのみ抽出
                tags_nonnumeric = soup.find_all('ix:nonnumeric')
            
                # 取得されたnonnumericごとにnonfractionを取得し、DFにする。
                for tag in tags_nonnumeric:
                    # nonfractionタグの取得
                    tag_nonfraction = tag.find_all('ix:nonfraction')
                    # 財務諸表の各要素をDFに。
                    df_each_fs = parse_nonfra(tag_nonfraction)
                    # nonnumericタグのタグnameから区分情報を取得
                    df_each_fs['fs_class_ns'] = tag.get('name').split(':')[0]
                    df_each_fs['fs_class'] = tag.get('name').split(':')[1]
                    # リストへ格納
                    if df_each_fs.empty:
                        pass
                    else:
                        list_fs.append(df_each_fs)
    
    # タグの中にtarget_FSが含まれない場合（例えば注記だけのixbrlを読み込んだ場合）の分岐
    if list_fs:
        # 各財務諸表の結合
        df_fs = pd.concat(list_fs)

        # 並べ替え
        df_fs = df_fs[['fs_class_ns', 'fs_class', 'account_item_ns', 'account_item', 'contextRef', 'format', 'decimals', 'scale', 'unitRef', 'amount']]

        # Namespace指定用のymd取得
        df_fs['xmlns_jpcrp_ymd'] = get_ns_ymd(arg_docid)

    else:
        # DFがないときはカラのDFを格納
        df_fs = pd.DataFrame()

    return df_fs

def get_ns_ymd(arg_docid):

    target_path = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/**.xbrl')[0]

    # headerファイルの読み込み
    with open(target_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    tag_html = soup.find_all('xbrli:xbrl')[0]

    # Namespace情報を格納するカラの辞書オブジェクト作成
    dict_xmlns = {}

    # xmlns:jpcrp_cor情報を取得
    # xmlns:jppfs_cor情報を取得
    jpcrp_cor = tag_html.get('xmlns:jpcrp_cor')
    dict_xmlns['xmlns_jpcrp_cor'] = jpcrp_cor
    ns_ymd = re.findall('\d{4}-\d{2}-\d{2}', jpcrp_cor)[0]

    return ns_ymd


def get_label_local(arg_docid):
    # 引数のdocidからパスを生成
    path_local_label = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/*_lab.xml')

    # 標準ラベルのみ使用し、独自ラベルを持たない場合があるため、if分岐
    if path_local_label:
        # labファイルの読み込み
        # labファイルの読み込み
        with open(path_local_label[0], encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
    
        # link:locタグのみ抽出
        link_loc = soup.find_all('link:loc')
    
        # ラベル情報用dictを格納するカラのリストを作成
        list_locator = []
    
        # ラベル情報をループ処理で取得
        for each_loc in link_loc:
            dict_locator = {}
            #dict_locator['xlink_type'] = each_loc.get('xlink:type')
            dict_locator['xlink_href'] = each_loc.get('xlink:href')
            dict_locator['shema'] = each_loc.get('xlink:href').split(sep='#')[0]
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
            #dict_arc['xlink_type'] = each_arc.get('xlink:type')
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
            #dict_resource['xlink_type'] = each_label.get('xlink:type')
            dict_resource['xml_lang'] = each_label.get('xml:lang')
            dict_resource['label_text'] = each_label.text
            list_resource.append(dict_resource)
    
        # ラベル情報取得結果をDFに    
        df_resource = pd.DataFrame(list_resource)
    
        # locとarcの結合
        df_merged = pd.merge(df_locator, df_arc, on='loc_label', how='inner')
        df_merged = pd.merge(df_merged, df_resource, on='xlink_label', how='inner')
    
        # 結合用のキー列追加
        df_merged['xmlns_jpcrp_ymd'] = get_ns_ymd(arg_docid)

    else:
        df_merged = pd.DataFrame()

    return df_merged


# ラベルの結合
def get_labeled_df(arg_fs, arg_label_local):

    df_label_global = pd.read_table(path_taxonomy_labels, sep='\t', encoding='utf-8')

    output_columns = ['fs_class_ns', 'fs_class', 'fs_label', 'account_item_ns', 'account_item', 'account_label', 'contextRef', 'unitRef', 'amount']

    df_fs = arg_fs
    df_label_local = arg_label_local

    # ローカルラベルがない場合も存在するため、分岐
    if df_label_local.empty:
        df_label_tmp = pd.concat([df_label_global])
    else:
        # 本来はグローバルラベルに定義がある「jpcrp_cor_ShareholdingRatio」をローカルラベルに含めている会社し、レコード重複の原因となるため、この行を削除
        df_label_local = df_label_local[~df_label_local['label_for_join'].str.contains('jpcrp_cor_ShareholdingRatio')]
        df_label_tmp = pd.concat([df_label_local, df_label_global])
        df_label_tmp = df_label_tmp[df_label_tmp['xlink_role'].str.contains('/2003/role/label')]

    # 必要カラムのみに絞る
    df_label_tmp = df_label_tmp[['xmlns_jpcrp_ymd', 'label_for_join', 'xlink_role', 'label_text']].drop_duplicates()
    # タクソノミが存在しないはずの2018-03-31を指定する会社が存在したため、結合のためだけに2019-02-28に置き換える
    df_label_tmp['xmlns_jpcrp_ymd'] = df_label_tmp['xmlns_jpcrp_ymd'].str.replace('2018-03-31', '2019-02-28')

    df_fs['fs_label_for_join'] = df_fs['fs_class_ns'] + '_' + df_fs['fs_class']
    df_fs['account_label_for_join'] = df_fs['account_item_ns'] + '_' + df_fs['account_item']
    # タクソノミが存在しないはずの2018-03-31を指定する会社が存在したため、結合のためだけに2019-02-28に置き換える
    df_fs['xmlns_jpcrp_ymd'] = df_fs['xmlns_jpcrp_ymd'].str.replace('2018-03-31', '2019-02-28')

    df_tmp_fslabel = pd.merge(df_fs, df_label_tmp, left_on=['fs_label_for_join', 'xmlns_jpcrp_ymd'], right_on=['label_for_join', 'xmlns_jpcrp_ymd'], how='left').drop(columns=['label_for_join']).rename(columns={'label_text': 'fs_label'})
    df_tmp = pd.merge(df_tmp_fslabel, df_label_tmp, left_on=['account_label_for_join', 'xmlns_jpcrp_ymd'], right_on=['label_for_join', 'xmlns_jpcrp_ymd'], how='left').drop(columns=['label_for_join']).rename(columns={'label_text': 'account_label'})

    df_output = df_tmp[output_columns]

    return df_output

def make_tidy(arg_df):
    # 連結財務諸表フラグの作成
    arg_df['consoli_flg'] = np.where(arg_df['contextRef'].str.contains('NonConsolidated'), 0, 1)
    # 財務諸表区分コードの作成
    arg_df['fs'] = np.where(arg_df['fs_class'].str.contains('BalanceSheet'), 'bs', \
                    np.where(arg_df['fs_class'].str.contains('StatementOfIncome'), 'pl', \
                    np.where(arg_df['fs_class'].str.contains('StatementOfCashFlows'), 'cf', \
                    np.where(arg_df['fs_class'].str.contains('StatementOfChangesInEquity'), 'ss', \
                    np.where(arg_df['fs_class'].str.contains('StatementOfComprehensiveIncome'), 'ci', '')))))
    # 並び替え
    df_tidy = arg_df[[
        'docID', 
        'ordinance', 
        'formCode', 
        'reporting_id', 
        'sequence_n1', 
        'DocType', 
        'edinetCode', 
        'companyName', 
        'sequence_n2', 
        'periodend', 
        'report_his', 
        'submitdate', 
        'GAAP',
        'fs_label',
        'account_label', 
        'contextRef', 
        'amount'
        ]]

    return df_tidy


def get_df_fs(arg_docid):
    # DEI情報の取得
    df_dei = get_dei(arg_docid)

    # DFの取得開始
    # ファイル名からキー情報の取得
    df_filename_keys = get_keys(arg_docid)
    # 結合用のキー列追加
    df_filename_keys['temp_key'] = 1

    # 財務数値をDFにする
    df_fs = get_nonfra(arg_docid)

    # docidから独自ラベルを取得する。
    df_label_local = get_label_local(arg_docid)
    # 日本語ラベル付きDFを取得する。
    df_labeled_fs = get_labeled_df(df_fs, df_label_local)
    # 結合用のキー列追加
    df_labeled_fs['temp_key'] = 1

    # ファイル名から作成したキー情報と結合
    df_output = pd.merge(df_filename_keys, df_labeled_fs, on='temp_key', how='left').drop(columns='temp_key')
    df_output = pd.merge(df_dei, df_output, on='edinetCode', how='left')

    df_output = make_tidy(df_output)

    return df_output
