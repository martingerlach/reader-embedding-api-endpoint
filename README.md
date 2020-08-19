# reader-embedding-api-endpoint

This repo sets up an API-endpoint on a Cloud-VPS instance to query the reader-embeddings trained on reading sessions.

It was adapted from the template in https://github.com/wikimedia/research-api-endpoint-template


## Setup

run `model/config/cloudvps_setup.sh`

Test-query: https://reader.wmflabs.org/api/v1/reader?qid=Q81068910


## What it does

The input is a wikidata-item.

The output is a list of wikidata-items which are most similar based on the embedding of reading-sessions.



## Additional Information

### Data collection
The default logging by nginx builds an access log located at `/var/log/nginx/access.log` that logs IP, timestamp, referer, request, and user_agent information.
I have overridden that in this repository to remove IP and user-agent so as not to retain private data unnecessariliy.
This can be [updated easily](https://docs.nginx.com/nginx/admin-guide/monitoring/logging/#setting-up-the-access-log).

### Privacy and encryption
For encryption, there are two important components to this:
* Cloud VPS handles all incoming traffic and enforces HTTPS and maintains the certs to support this. This means that a user who visits the cite will see an appropriately-certified, secure connection without any special configuration. We customize the nginx configuration to enforce HTTPS on client <--> Cloud VPS connection. Eventually this will not be required (see https://phabricator.wikimedia.org/T131288), but in the meantime, a simple redirect
in the nginx configuration (`model.nginx`) will enforce HTTPS.
* The traffic between Cloud VPS and our nginx server, however, is unencrypted and currently cannot be encrypted. This is not a large security concern because it's very difficult to snoop on this traffic, but be aware that it is not end-to-end encrypted.

Additionally, [CORS](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing) is enabled so that any external site (e.g., your UI on toolforge) can make API requests. From a privacy perspective, this does not pose any concerns as no private information is served via this API.

### Debugging
Various commands can be checked to see why your API isn't working:
* `sudo less /var/log/nginx/error.log`: nginx errors
* `sudo systemctl status model`: success at getting uWSGI service up and running to pass nginx requests to flask (generally badd uwsgi.ini file)
* `sudo less /var/log/uwsgi/uwsgi.log`: inspect uWSGI log for startup and handling requests (this is where you're often find Python errors that crashed the service)

### Adapting to a new model etc.
You will probably have to change the following components:
* `model/wsgi.py`: this is the file with your model / Flask so you'll have to update it depending your desired input URL parameters and output JSON result.
* `flask_config.yaml`: any Flask config variables that need to be set.
* `model/config/cloudvps_setup.sh`: you likely will have to change some of the parameters at the top of the file and how you download any larger data/model files. Likewise, `model/config/release.sh` will need to be updated in a similar manner.
* `model/config/model.nginx`: server name will need to be updated to your instance / proxy (set in Horizon)
* `model/config/uwsgi.ini`: potentially update number of processes and virtualenv location
* `model/config/model.service`: potentially update description, though this won't affect the API
* `requirements.txt`: update to include your Python dependencies
* Currently `setup.py` is not used, but it would need to be updated in a more complete package system.

