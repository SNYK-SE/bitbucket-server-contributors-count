# bitbucket-server-contributors-count
Count contributing developers to a Bitbucket Server instance in the last 90 days.

# Usage
Install virtual environment with:

`pipenv install`


Then run the script with:

`pipenv run python3 bitbucketserverdevcount.py --hostname [bbserver-hostname] --token [access-token]`

or

`pipenv run python3 bitbucketserverdevcount.py --hostname [bbserver-hostname] --username [bbserver-username] --password [bbserver-password]`


(Or use alternate Python 3 environment as required)


Hostname means hostname, not URL... for example use `stash.xyzco.com` not `https://stash.zyxco.com`
