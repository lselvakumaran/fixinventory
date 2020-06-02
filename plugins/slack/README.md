# cloudkeeper-plugin-slack
Slack collector and notification plugin for Cloudkeeper

This plugin consists of two plugins.
A collector plugin that collects Slack users, groups and channels and adds them to the Cloudkeeper graph for analysis and usage by other plugins.
As well as a notification plugin that at the end of a cleanup run will notify Slack users of changes to their resources.

## Usage
```
$ cloudkeeper -v --collector slack --slack-bot-token xoxb-5178416381-911467024217-ro2VfEDEMlsAqUtgPoxEPUwW

OR

$ export SLACK_BOT_TOKEN=xoxb-5178416381-911467024217-ro2VfEDEMlsAqUtgPoxEPUwW
$ cloudkeeper -v --collector slack
```

Provided Slack bot token must have permission to read the list of users, groups and channels as well as user email addresses.

The notification plugin looks for a tag `cloudkeeper:owner` on each resource. If the value of that tag starts with `slack:` or `email:` it will
try and find a corresponding Slack username or email and send that person the event log of their changed resources via Slack.

## List of arguments
```
  --slack-bot-token SLACK_BOT_TOKEN
                        Slack Bot Token (default env $SLACK_BOT_TOKEN)
```
