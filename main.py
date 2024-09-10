import os
import requests
from github import Github
from flask import Flask, request, redirect
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore
from slack_sdk.web import WebClient
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Existing functions
def get_org_repositories(org_name, github_token):
    g = Github(github_token)
    org = g.get_organization(org_name)
    return org.get_repos()

def get_pr_issue_activity_from_repo(repo):
    pr_issue_activity = []
    issues = repo.get_issues(state='open')
    for issue in issues:
        pr_issue_activity.append({
            'type': 'Issue',
            'title': issue.title,
            'url': issue.html_url
        })
    pulls = repo.get_pulls(state='open')
    for pull in pulls:
        pr_issue_activity.append({
            'type': 'PullRequest',
            'title': pull.title,
            'url': pull.html_url
        })
    return pr_issue_activity

def send_slack_reminder(activities, webhook_url):
    if not activities:
        return
    message = '*Reminder for the Notification*\n'
    message += f'There are {len(activities)} open PRs/issues:\n'
    
    for activity in activities:
        message += f"• {activity['type']}: <{activity['url']}|{activity['title']}>\n"
    
    payload = {
        'text': message,
        'username': 'GitHub Notification Bot',
        'icon_emoji': ':github:'
    }
    
    response = requests.post(webhook_url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send Slack message. Status code: {response.status_code}")
        print(f"Response: {response.text}")
    else:
        print("Message sent successfully.")

# Get environment variables
github_token = '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'
org_name = 'keploy'
slack_webhook_url = 'https://hooks.slack.com/services/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'
slack_client_id ='3074356993157.7697084833814'
slack_client_secret = '69b48790402e873174205fdb5e31956b'
slack_signing_secret = '621d7a267dec79e3bf309f4e352b1032'

# Initialize Slack OAuth components
installation_store = FileInstallationStore(base_dir="./data")
oauth_state_store = FileOAuthStateStore(expiration_seconds=600, base_dir="./data")

authorize_url_generator = AuthorizeUrlGenerator(
    client_id=slack_client_id,
    scopes=["chat:write", "channels:read"]
)

@app.route("/slack/invite", methods=["GET"])
def slack_oauth():
    state = oauth_state_store.issue()
    authorize_url = authorize_url_generator.generate(state)
    return redirect(authorize_url)

@app.route("/slack/oauth_redirect", methods=["GET"])
def slack_oauth_redirect():
    code = request.args.get("code")
    state = request.args.get("state")
    
    if not oauth_state_store.consume(state):
        return "Invalid state parameter", 400

    client = WebClient()
    oauth_response = client.oauth_v2_access(
        client_id=slack_client_id,
        client_secret=slack_client_secret,
        code=code
    )

    installation_store.save(oauth_response)

    return "Installation successful!", 200

def check_github_and_notify():
    repositories = get_org_repositories(org_name, github_token)
    all_activities = []
    for repo in repositories:
        activities = get_pr_issue_activity_from_repo(repo)
        all_activities.extend(activities)
    
    if all_activities:
        send_slack_reminder(all_activities, slack_webhook_url)

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_github_and_notify, trigger="interval", hours=24)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True)