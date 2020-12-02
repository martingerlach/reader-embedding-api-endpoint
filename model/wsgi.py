# Many thanks to: https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Flask_OAuth_tool
import os
import re
import fasttext
import numpy as np
import math
import requests
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mwapi
import yaml

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False # jsonify does not order the keys
__dir__ = os.path.dirname(__file__)

# load in app user-agent or any other app config
app.config.update(
    yaml.safe_load(open(os.path.join(__dir__, 'flask_config.yaml'))))

# Enable CORS for API endpoints
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# fast-text model for making predictions
FT_MODEL =  fasttext.load_model(os.path.join(__dir__, 'resources/embedding.bin'))
# FT_MODEL =  fasttext.load_model(os.path.join('../resources/embedding.bin'))
VOCAB = FT_MODEL.get_words()

@app.route('/api/v1/reader', methods=['GET'])
def get_recommendations():
    args = parse_args(request)
    qid = args['qid'] ## pass qid-seed
    n = args['n'] ## number of nearest neighbors (default: 10, max: 1000)
    threshold = args['threshold'] ## minimimum threshold for similarity score (default 0)

    if validate_qid_format(qid) and validate_qid_model(qid):
        qid_nn = recommend(qid,nn = n, threshold = threshold)
        result = [ {'qid': r['qid'], 'score':r['score']}  for r in qid_nn]

        return jsonify(result)
    return jsonify({'Error':qid})

def parse_args(request):
    """
    Parse api query parameters
    """
    ## number of neighbors
    n_default = 10 ## default number of neighbors
    n_max = 100 ## maximum number of numbers (even if submitted argument is larger)
    n = request.args.get('n',n_default)
    try:
        n = min(int(n), n_max)
    except:
        n = n_default

    ## seed qid
    qid = request.args.get('qid').upper()
    if not validate_qid_format(qid):
        qid = "Error: poorly formatted 'qid' field. {0} does not match 'Q#...'".format(qid)
    else:
        if not validate_qid_model(qid):
            qid = "Error: {0} is not included in the model".format(qid)

    ## threshold for similarity to include
    threshold = request.args.get('threshold',0.)

    ## whether to show the URL
    showUrl = request.args.get('showurl','')
    if showUrl.lower() == 'true':
        showUrl = True
    else:
        False
    # print(bool(showUrl))
    filter_arg = request.args.get('filter','')
    filterStr = []
    for fstr in filter_arg.split('|'):
        if fstr != '':
            filterStr += [fstr]

    ## pass arguments
    args = {    'qid': qid,
                'n': n,
                'threshold': float(threshold),
            }

    return args

def validate_qid_format(qid):
    return re.match('^Q[0-9]+$', qid)

def validate_qid_model(qid):
    return qid in VOCAB

def recommend(qid, nn = 10, threshold = 0.):
    """
    get nn closest qids in emebdding space.
    """
    recs = FT_MODEL.get_nearest_neighbors(qid,k=nn)
    result = [{'qid':qid,'score':1.}]
    result += [{ 'qid':r[1],'score':r[0]} for r in recs if r[0]>threshold]
    return result

@app.route('/api/v1/list-reader', methods=['GET'])
def get_articlelist():
    ## parse arguments
    # input qid
    ## seed qid
    qid = request.args.get('qid').upper()
    if not validate_qid_format(qid):
        qid = "Error: poorly formatted 'qid' field. {0} does not match 'Q#...'".format(qid)
    else:
        if not validate_qid_model(qid):
            qid = "Error: {0} is not included in the model".format(qid)


    # target language
    lang = request.args.get('lang', 'en').replace('wiki','')
    # number of items to retrieve
    k_default = 100 ## default number of neighbors
    k_max = 100 ## maximum number of numbers (even if submitted argument is larger)
    k = request.args.get('k',k_default)
    try:
        k = min(int(k), k_max)
    except:
        k = k_default

    if validate_qid_format(qid) and validate_qid_model(qid):
        ## get neighbors
        qid_nn = FT_MODEL.get_nearest_neighbors(qid,k=k)
        result = [
            {'qid': r[1],
             'score':r[0],
             }  for r in qid_nn]

        result = add_article_titles(result,lang)
        result_formatted = [
            {'qid': r['qid'],
             'title': r['title'],
             'score':r['score'],
             }  for r in result]

        return jsonify(result_formatted)
    else:
        return jsonify({'Error':qid})
    #     return jsonify(result)
    # return jsonify({'Error':qid})


def add_article_titles(list_items, lang ,n_batch = 20):
    api_url_base = ' https://wikidata.org/w/api.php'
    list_qids = [h['qid'] for h in list_items]
    list_qids_split = np.array_split(list_qids,math.ceil(len(list_qids)/n_batch))

    wiki = lang+'wiki'

    i_qid=0
    list_items_new = list_items.copy()
    for list_qids_batch in list_qids_split:

        params = {
            'action':'wbgetentities',
            'props':'sitelinks|labels|descriptions',
            'languages':'en',
            'format' : 'json',
            'sitefilter':wiki,
            'ids':'|'.join(list_qids_batch),
        }
        response = requests.get( api_url_base,params=params)
        result=json.loads(response.text)
        ## make sure we have results

        for qid_sel in list_qids_batch:
            ## get title in selected wikis
            title = result['entities'].get(qid_sel,{}).get('sitelinks',{}).get(wiki,{}).get('title','-').replace(' ','_')
            list_items_new[i_qid]['title'] = title

            ##get label+description (english)
            label = result['entities'].get(qid_sel,{}).get('labels',{}).get('en',{}).get('value','-')
            list_items_new[i_qid]['label'] = label
            description = result['entities'].get(qid_sel,{}).get('description',{}).get('en',{}).get('value','-')
            list_items_new[i_qid]['description'] = description

            i_qid+=1

    return list_items_new

application = app

if __name__ == '__main__':
    application.run()