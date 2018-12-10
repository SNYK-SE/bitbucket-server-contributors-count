import requests
import argparse
import datetime
import time
import base64
import json

# You can set these if you prefer not to use the command-line args
bb_default_hostname = ''
bb_default_token = ''
bb_default_username = ''
bb_default_password = ''

lookback_time_days = 90
lookback_time_ms = lookback_time_days * 24 * 60 * 60 * 1000

now_date = datetime.datetime.now()
epoch_now_s = int(time.time())
epoch_now_ms = epoch_now_s * 1000

cutoff_timestamp_ms = epoch_now_ms - lookback_time_ms


def parse_command_line_args():
    parser = argparse.ArgumentParser(description="Count developers in BitBucket.org active in the last 90 days")
    parser.add_argument('--hostname', type=str, help='BitBucket Server Hostname')

    parser.add_argument('--token', type=str, help='BitBucket Server Personal Access Token')

    parser.add_argument('--username', type=str, help='BitBucket Server Username')
    parser.add_argument('--password', type=str, help='BitBucket Server Password')

    args = parser.parse_args()

    if args.hostname is None:
        args.hostname = bb_default_hostname

    if args.token is None:
        args.token = bb_default_token

    if args.username is None:
        args.username = bb_default_username

    if args.password is None:
        args.password = bb_default_password

    if args.token != '' and args.username != '':
        print('You can either set --token or --username but not both.')
        parser.print_usage()
        parser.print_help()
        quit()

    if args.token == '' and args.username == '':
        print('You must use either --token XOR (--username and --password)')
        parser.print_usage()
        parser.print_help()
        quit()

    if args.hostname == '':
        parser.print_usage()
        parser.print_help()
        quit()

    return args


def get_bitbucket_server_api_return_json(full_api_url):
    headers = get_auth_headers()
    resp = requests.get(full_api_url, headers=headers)
    obj_json_response = resp.json()
    return obj_json_response


def get_page_of_paged_api(api_url, start):
    full_api_url = '%s?start=%s' % (api_url, start)
    # full_api_url = '%s?start=%s&limit=50' % (api_url, start)
    obj_json_response = get_bitbucket_server_api_return_json(full_api_url)
    return obj_json_response


def iteratively_get_all_pages_of_paged_api(api_url, bail_early_delegate=None):
    """Return list of the 'values' objects returned by a paged BitBucket Server API.
        Iterates through all the pages.
        Optional bail_early_delegate allows you to stop and reject items matching some criteria (which we will
        use to not collect and stop paging when we hit a commit older than the target cutoff date."""
    start = 0
    values = []

    continue_loop = True

    while continue_loop:
        obj_json_response = get_page_of_paged_api(api_url, start)

        try:
            new_values = obj_json_response['values']
        except KeyError as k:
            print('WARNING: key \'values\' not found in JSON response.')
            print(json.dumps(obj_json_response, indent=4))
            break

        # Check bail_early_delegate to see if we should stop iterating
        for next_value in new_values:
            if bail_early_delegate is not None and bail_early_delegate(next_value):
                continue_loop = False  # to break out of outer while
                break
            else:
                values.append(next_value)

        if not continue_loop:
            break

        if obj_json_response['isLastPage']:
            break
        else:
            start = obj_json_response['nextPageStart']
            time.sleep(0.1)  # Sleep 100 ms - just so we don't DoS the API
            print(start)

    return values


def test_bail_early_delegate(next_value):
    return True


def bail_if_commit_older_than_target_days_delegate(next_commit):
    """Return True if the given commit is older than the cutoff timestamp"""
    authorTimestamp = next_commit['authorTimestamp']
    d = datetime.datetime.fromtimestamp(authorTimestamp / 1000)

    if authorTimestamp < cutoff_timestamp_ms:
        # this commit is more than 90 days ago
        return True

    return False


def get_token_based_auth_headers():
    headers = {
        'Authorization': 'Bearer %s' % bb_token
    }
    return headers


def get_basic_auth_headers():
    pre_encoded_auth_string = '%s:%s' % (bb_username, bb_password)
    encoded_auth_string = base64.standard_b64encode(pre_encoded_auth_string.encode('utf-8')).decode()

    headers = {
        'Authorization': 'Basic %s' % encoded_auth_string
    }
    return headers


def is_use_token_auth():
    if bb_token is not None and bb_token != '':
        return True
    else:
        return False


def get_auth_headers():
    if is_use_token_auth():
        return get_token_based_auth_headers()
    else:
        return get_basic_auth_headers()


args = parse_command_line_args()
bb_token = args.token
bb_hostname = args.hostname
bb_username = args.username
bb_password = args.password

if is_use_token_auth():
    print('Using Personal Access Token')
else:
    print('Using Basic Auth')


# List projects
all_projects = []
full_api_url = 'https://%s/rest/api/1.0/projects' % bb_hostname
# json_resp = get_bitbucket_server_api_return_json(full_api_url)
# get_all_pages_of_paged_api(full_api_url)
values = iteratively_get_all_pages_of_paged_api(full_api_url)

print("Projects found:")
for next_value in values:
    print(next_value['key'])
    all_projects.append(next_value['key'])
print()

# Get Repos for each Project
unique_authors = []
all_repos_slugs = []
for next_project_key in all_projects:
    print('Project: %s' % next_project_key)

    # /rest/api/1.0/projects/{projectKey}/repos
    repos_api_url = 'https://%s/rest/api/1.0/projects/%s/repos' % (bb_hostname, next_project_key)
    repo_values = iteratively_get_all_pages_of_paged_api(repos_api_url)
    # use 'slug' to lookup commits
    for next_repo in repo_values:
        all_repos_slugs.append(next_repo['slug'])
        next_repo_slug = next_repo['slug']
        print('  Repo: %s' % next_repo_slug)

        # Get Commits for each Repo
        # /rest/api/1.0/projects/{projectKey}/repos/{repositorySlug}/commits
        commits_api_url = 'https://%s/rest/api/1.0/projects/%s/repos/%s/commits' % (bb_hostname, next_project_key, next_repo_slug)
        commit_values = iteratively_get_all_pages_of_paged_api(commits_api_url, bail_if_commit_older_than_target_days_delegate)
        print('    Found %s commits within %s days' % (len(commit_values), lookback_time_days))

        for next_commit in commit_values:
            authorName = next_commit['author']['name']
            authorEmailAddress = next_commit['author']['emailAddress']
            author_composite = '%s <%s>' % (authorName, authorEmailAddress)
            if author_composite not in unique_authors:
                unique_authors.append(author_composite)


# Print Summary of Findings
print('\n')
print('Found %s authors in the last %s days' % (len(unique_authors), lookback_time_days))
print('Authors found:')
for next_author in unique_authors:
    print(next_author)

