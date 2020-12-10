from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import glob
import numpy as np

# パスの指定
path_base = '****' # baseとなるディレクトリの指定。個々のdocidが付されたフォルダが格納された階層を指定することを想定しています。
path_taxonomy_labels = '****/taxonomy_labels_05122254.tsv' # Gitに乗せたtsvファイルをローカルに保存して当該パスを指定してください。


def get_keys(arg_filename):
    # カラの辞書を作成
    dict_key = {}

    # docIDを取得
    dict_key['docID'] = re.findall('S\w{7}', arg_filename)[0]

    # 必要なファイル名部分だけに絞る
    filename = os.path.basename(arg_filename)

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

    return df_dei


# 財務諸表の要素タグからDFを返す関数。
# 5.のサンプルコードからXBRLファイルの読み込みを省略
def get_df(arg_tags):
    # 各fsの各要素を格納した辞書を入れるカラのリスト作成
    list_fs = []
    # 各fsの各要素を辞書に格納
    for each_item in arg_tags:
        dict_fs = {}
        dict_fs['account_item'] = each_item.get('name')
        dict_fs['contextRef'] = each_item.get('contextref')
        dict_fs['format'] = each_item.get('format')
        dict_fs['decimals'] = each_item.get('decimals')
        dict_fs['scale'] = each_item.get('scale')
        dict_fs['unitRef'] = each_item.get('unitRef')
        # マイナス表記の場合の処理＋円単位への変更
        if each_item.get('sign') == '-' and each_item.get('xsi:nil') != 'true':
            amount = int(each_item.text.replace(',', '')) * -1 * 10 ** int(each_item.get('scale'))
        elif each_item.get('xsi:nil') != 'true':
            amount = int(each_item.text.replace(',', '')) * 10 ** int(each_item.get('scale'))
        else:
            amount = ''
        dict_fs['amount'] = amount
        # 辞書をリストへ格納
        list_fs.append(dict_fs)

    # 辞書を格納したリストをDFに
    df_eachfs = pd.DataFrame(list_fs)

    return df_eachfs


# XBRLのパスから、DFを返す関数本体。
def get_fs(arg_path):
    # fsファイルの読み込み。bs4でパース
    with open(arg_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # nonNumericタグのみ抽出
    tags_nonnumeric = soup.find_all('ix:nonnumeric')

    # nonnumericの各要素を格納するカラの辞書を作成
    dict_tag = {}
    # nonnumericの内容を辞書型に
    for tag in tags_nonnumeric:
        dict_tag[tag.get('name')] = tag

    # 取得対象となりうる財務諸表の`name`一覧定義
    list_target_fs = ['jpcrp_cor:ConsolidatedBalanceSheetTextBlock',
        'jpcrp_cor:ConsolidatedStatementOfIncomeTextBlock',
        'jpcrp_cor:ConsolidatedStatementOfComprehensiveIncomeTextBlock',
        'jpcrp_cor:ConsolidatedStatementOfChangesInEquityTextBlock',
        'jpcrp_cor:ConsolidatedStatementOfCashFlowsTextBlock',
        'jpcrp_cor:BalanceSheetTextBlock',
        'jpcrp_cor:StatementOfIncomeTextBlock',
        #'jpcrp_cor:DetailedScheduleOfManufacturingCostTextBlock',#製造原価報告書を取得する場合はコメントアウトを外してください。
        'jpcrp_cor:StatementOfChangesInEquityTextBlock',
        'jpcrp_cor:StatementOfCashFlowsTextBlock'
    ]

    # 各財務諸表を入れるカラのDFを作成
    list_fs = []
    # 可能性のある財務諸表区分ごとにループ処理でDF作成
    # dict_tagのキーの中には、財務諸表本表に関係のない注記情報に関するキーもあるため、必要な本表に絞ってループ処理
    for each_target_fs in list_target_fs:
        # ターゲットとなるFS区分のタグを取得
        tag_each_fs = dict_tag.get(each_target_fs)
        # 辞書型の値をgetして、値がなければnoneが返る。noneはfalse扱いのため、これを条件に分岐。
        if tag_each_fs:
            # 財務諸表要素は'ix:nonFraction'に入っているため、このタグを取得
            tag_nonfraction = tag_each_fs.find_all('ix:nonfraction')
            # 財務諸表の各要素をDFに。財務諸表区分とタグを引数にして関数に渡す。
            df_each_fs = get_df(tag_nonfraction)
            df_each_fs['fs_class'] = each_target_fs
            list_fs.append(df_each_fs)

    # タグの中にtarget_FSが含まれない場合（例えば注記だけのixbrlを読み込んだ場合）の分岐
    if list_fs:
        # 各財務諸表の結合
        df_fs = pd.concat(list_fs)

        # 並べ替え
        df_fs = df_fs[['fs_class', 'account_item', 'contextRef', 'format', 'decimals', 'scale', 'unitRef', 'amount']]

    else:
        df_fs = pd.DataFrame(index=[])

    return df_fs


def get_label_local(arg_docid):

    path_local_label = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/*_lab.xml')

    # labファイルの読み込み
    with open(path_local_label[0], encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # link:labelタグのみ抽出
    link_label = soup.find_all('link:label')

    # ラベル情報用dictを格納するカラのリストを作成
    list_label = []

    # ラベル情報をループ処理で取得
    for each_label in link_label:
        dict_label = {}
        dict_label['id'] = each_label.get('id')
        dict_label['xlink_label'] = each_label.get('xlink:label')
        dict_label['xlink_role'] = each_label.get('xlink:role')
        dict_label['xlink_type'] = each_label.get('xlink:type')
        dict_label['xml_lang'] = each_label.get('xml:lang')
        dict_label['label'] = each_label.text
        list_label.append(dict_label)

    # ラベル情報取得結果をDFに    
    df_label_local = pd.DataFrame(list_label)

    return df_label_local


def get_labeled_df(arg_fs, arg_label_local):
    df_label_global = pd.read_table(path_taxonomy_labels, sep='\t', encoding='utf-8')

    # グローバルラベルの処理
    # グローバルラベルデータのうち、必要行に絞る
    df_label_global = df_label_global[df_label_global['xlink_role'] == 'http://www.xbrl.org/2003/role/label']
    # 必要列のみに絞る
    df_label_global = df_label_global[['xlink_label', 'label']]
    # 'label_'はじまりを削除で統一
    df_label_global['xlink_label'] = df_label_global['xlink_label'].str.replace('label_', '')
    # 同一ラベルで異なる表示名が存在する場合、独自の表示名を優先
    df_label_global['temp'] = 0

    # ローカルラベルの処理
    # ローカルラベルデータのうち、必要列に絞る
    df_label_local = arg_label_local[['xlink_label', 'label']]
    # ラベルの一番後ろに'_label.*'があり、FSと結合できないため、これを削除
    df_label_local['xlink_label'] = df_label_local['xlink_label'].str.replace('_label.*$', '')
    # ラベルの最初に'jpcrp'で始まるラベルがあり、削除で統一。
    # 削除で統一した結果、各社で定義していた汎用的な科目名（「貸借対照表計上額」など）が重複するようになる。後続処理で重複削除。
    df_label_local['xlink_label'] = df_label_local['xlink_label'].str.replace('jpcrp\d{6}-asr_E\d{5}-\d{3}_', '')
    # ラベルの最初に'label_'で始まるラベルがあり、削除で統一
    # 削除で統一した結果、各社で定義していた汎用的な科目名（「貸借対照表計上額」など）が重複するようになる。後続処理で重複削除。
    df_label_local['xlink_label'] = df_label_local['xlink_label'].str.replace('label_', '')
    # 同一ラベルで異なる表示名が存在する場合、独自の表示名を優先
    df_label_local['temp'] = 1
    
    # label_globalとlabel_localを縦結合
    df_label_merged = pd.concat([df_label_global, df_label_local])
    # 同一ラベルで異なる表示名が存在する場合、独自の表示名を優先
    grp_df_label_merged = df_label_merged.groupby('xlink_label')
    df_label_merged = df_label_merged.loc[grp_df_label_merged['temp'].idxmax(),:]
    df_label_merged = df_label_merged.drop('temp', axis=1)
    
    # localラベルで重複してしまう行があるため、ここで重複行を削除
    df_label_merged = df_label_merged.drop_duplicates()
    
    arg_fs['temp_label'] = arg_fs['account_item'].str.replace('jpcrp\d{6}-asr_E\d{5}-\d{3}:', '')
    arg_fs['temp_label'] = arg_fs['temp_label'].str.replace('jppfs_cor:', '')

    df_labeled_fs = pd.merge(arg_fs, df_label_merged, left_on='temp_label', right_on='xlink_label', how='left').drop_duplicates()

    return df_labeled_fs


def make_tidy(arg_df):
    arg_df['consoli_flg'] = np.where(arg_df['contextRef'].str.contains('NonConsolidated'), 0, 1)

    arg_df['fs'] = np.where(arg_df['fs_class'].str.contains('BalanceSheet'), 'bs', \
        np.where(arg_df['fs_class'].str.contains('StatementOfIncome'), 'pl', \
            np.where(arg_df['fs_class'].str.contains('StatementOfCashFlows'), 'cf', \
                np.where(arg_df['fs_class'].str.contains('StatementOfChangesInEquity'), 'ss', \
                    np.where(arg_df['fs_class'].str.contains('StatementOfComprehensiveIncome'), 'ci', '')))))

    df_tidy = arg_df[['docID', 'ordinance', 'formCode', 'reporting_id', 'sequence_n1', 'edinetCode', 'companyName', 'sequence_n2', 'periodend', 'report_his', 'submitdate', 'consoli_flg', 'fs', 'label', 'contextRef', 'amount']]

    return df_tidy



def get_df_fs(arg_docid):
    # docidから経理の状況が含まれるXBRLファイルのリストを取得
    list_0105 = glob.glob(path_base + arg_docid + '/XBRL/PublicDoc/0105**.htm')
    # 経理の状況が含まれるリストから、各ファイルに対応するDFを作成し、リストに格納
    list_df_fs = [get_fs(each_0105) for each_0105 in list_0105]
    # 各ファイルごとのDFを縦結合する。
    df_fs = pd.concat(list_df_fs)

    # docidから独自ラベルを取得する。
    df_label_local = get_label_local(arg_docid)
    # 日本語ラベル付きDFを取得する。
    df_labeled_fs = get_labeled_df(df_fs, df_label_local)

    # ファイル名からキー情報の取得
    df_filename_keys = get_keys(list_0105[0])
    # 結合用のキー列追加
    df_filename_keys['temp_key'] = 1
    # 結合用のキー列追加
    df_labeled_fs['temp_key'] = 1

    # 会社名の取得
    df_dei = get_dei(arg_docid)
    # 必要なカラムに絞り列名変更
    df_dei = df_dei[['jpdei_cor:EDINETCodeDEI', 'jpdei_cor:FilerNameInJapaneseDEI']].rename(columns={'jpdei_cor:EDINETCodeDEI': 'edinetCode', 'jpdei_cor:FilerNameInJapaneseDEI': 'companyName'})

    # ファイル名から作成したキー情報と結合
    df_output = pd.merge(df_filename_keys, df_labeled_fs, on='temp_key', how='left').drop(columns='temp_key')
    df_output = pd.merge(df_dei, df_output, on='edinetCode', how='left')

    df_output = make_tidy(df_output)

    return df_output








