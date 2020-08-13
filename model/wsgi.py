# Many thanks to: https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Flask_OAuth_tool
import os

import fasttext
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mwapi
import yaml

app = Flask(__name__)

__dir__ = os.path.dirname(__file__)

# load in app user-agent or any other app config
app.config.update(
    yaml.safe_load(open(os.path.join(__dir__, 'flask_config.yaml'))))

# Enable CORS for API endpoints
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# fast-text model for making predictions
FT_MODEL =  fasttext.load_model(os.path.join(__dir__, 'resources/embedding.bin'))

@app.route('/api/v1/reader', methods=['GET'])
def get_recommendations():
    args = parse_args(request)
    qid = args['qid'] ## pass qid-seed
    n = args['n'] ## number of nearest neighbors (default: 10, max: 1000)
    threshold = args['threshold'] ## minimimum threshold for similarity score (default 0)

    if validate_qid_format(qid) and validate_qid_model(qid):
        qid_nn = recommend(qid,nn = n, threshold = threshold)
        result = [ {'qid': r['qid'], 'score':r['score']}  for r in qid_nn]

        return jsonify(result_formatted)
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

def recommend(qid, nn = 10, list_wikis= ['enwiki'], threshold = 0.):
    """
    get nn closest qids in emebdding space.
    """
    recs = FT_MODEL.get_nearest_neighbors(qid,k=nn)
    result = [{'qid':qid,'score':1.}]
    result += [{ 'qid':r[1],'score':r[0]} for r in recs if r[0]>threshold]
    return result

application = app

if __name__ == '__main__':
    application.run()