# bitbucket-server-contributers-count
Count contributing developers to a Bitbucket Server instance in the last 90 days.

# Usage
pipenv install
pipenv run python3 --hostname [bbserver-hostname] --token [access-token]

or

pipenv run python3 --hostname [bbserver-hostname] --username [bbserver-username] --password [bbserver-password]

(Or use alternate Python 3 environment as required)

Hostname means hostname, not URL... for example use stash.xyzco.com not https://stash.zyxco.com
