import os
import requests
from github import Github
from datetime import datetime
from collections import defaultdict

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
            'url': issue.html_url,
            'created_at': issue.created_at,
            'repo_name': repo.name
        })
    
    # Fetch recent pull requests
    pulls = repo.get_pulls(state='open')
    for pull in pulls:
        pr_issue_activity.append({
            'type': 'PullRequest',
            'title': pull.title,
            'url': pull.html_url,
            'created_at': pull.created_at,
            'repo_name': repo.name
        })
    
    return pr_issue_activity

def format_date(date):
    return date.strftime("%Y-%m-%d")

def group_activities_by_date(activities):
    grouped_activities = defaultdict(list)
    for activity in activities:
        date_key = format_date(activity['created_at'])
        grouped_activities[date_key].append(activity)
    
    # Sort dates in reverse chronological order
    return dict(sorted(grouped_activities.items(), reverse=True))

def send_slack_reminder(activities, webhook_url):
    if not activities:
        return
    
    grouped_activities = group_activities_by_date(activities)
    
    message = '*GitHub Open PRs and Issues Summary*\n'
    message += f'Total: {len(activities)} open items\n\n'
    
    for date, items in grouped_activities.items():
        message += f'*{date}* ({len(items)} items)\n'
        
        # Group by repository
        repo_items = defaultdict(list)
        for item in items:
            repo_items[item['repo_name']].append(item)
        
        for repo_name, repo_activities in repo_items.items():
            message += f'*Repository: {repo_name}*\n'
            
            # Separate PRs and Issues
            prs = [item for item in repo_activities if item['type'] == 'PullRequest']
            issues = [item for item in repo_activities if item['type'] == 'Issue']
            
            if prs:
                message += '*Pull Requests:*\n'
                for pr in prs:
                    message += f"• <{pr['url']}|{pr['title']}>\n"
            
            if issues:
                message += '*Issues:*\n'
                for issue in issues:
                    message += f"• <{issue['url']}|{issue['title']}>\n"
            
            message += '\n'
    
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

def main():
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

if __name__ == "__main__":
    main()
