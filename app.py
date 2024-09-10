import os
import requests
from github import Github
                    
def get_org_repositories(org_name, github_token):
    g = Github(github_token)
    org = g.get_organization(org_name)
    return org.get_repos()
                    
def get_pr_issue_activity_from_repo(repo):
    pr_issue_activity = []
    # Fetch recent issues
    issues = repo.get_issues(state='open')
    for issue in issues:
        pr_issue_activity.append({
            'type': 'Issue',
            'title': issue.title,
            'url': issue.html_url
            })
        # Fetch recent pull requests
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
            print('f"Failed to send Slack message. Status code: {response.status_code}"')
            print('"Response: {response.text}"')
        else:
            print('"Message sent successfully."')
          

          # Get environment variables
github_token = os.environ['GITHUB_TOKEN']
org_name = os.environ['ORG_NAME']
slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']
# Get organization repositories
repositories = get_org_repositories(org_name, github_token)
          
# Gather all activities
all_activities = []
for repo in repositories:
    activities = get_pr_issue_activity_from_repo(repo)
    all_activities.extend(activities)

# Send Slack reminders
if all_activities:
    send_slack_reminder(all_activities, slack_webhook_url)