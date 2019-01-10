# AWS-SMSUsageAlarm
This is an alarm to notify you when you are approaching the spent limit of SMS in AWS.

## Introduction

A Lambda function that checks the current SMS usage in [all regions](https://docs.aws.amazon.com/sns/latest/dg/sms_supported-countries.html) that supports SMS. If the usage crossed certain percentage of overall account limit set up in that region (by default it is 1.00 USD), the function will send an SMS to a group of recipients, or to a SNS topic.

## Environment

- Lambda function, can be triggered by anything. Ideally a CloudWatch event scheduled by some point at a day. This function will log the input event but will not use it in logic.
- Local environment. Tested in Python 3.7.

## Configurations

- `warning_cutoff`: A value from 0 to 1. If the percentage of usage crossed the value, the recipients will be notified. For example, if the value is set to `0.7` that means if one region used 70% of its spending limit, you will see this region is included in a warning message.
- `warning_delivery`: A value either be `'SMS'` or `'Topic'`.
- `warning_audience`: If `warning_delivery` is `'SMS'`, `warning_audience` will be a `list` of phone numbers following the E.164 recommendation. If `warning_delivery` is `'Topic'`, `warning_audience` will be a `str` of the ARN of the SNS topic of the recipients.

### Optional

- `SMS_regions`: The default value is a `list` of all AWS regions that support SMS feature. Change to otherwise if it is desired to only monitor certain regions only.
- `sns_sender_id`: The sender ID of SMS. [Not all countries](https://docs.aws.amazon.com/sns/latest/dg/sms_supported-countries.html) support showing sender ID of an SMS message.
- `account_id`: The current AWS account ID retrieved from the saved AWS credential in the environment. **It is NOT recommended to change this to other values.**

These configurations can also be set in the environment variable part or parse as the event parameter in Lambda. However, the code has to be modified to accommodate this purpose.



## Logging in AWS Lambda

Logging is natively supported. If you wish to track the behavior of this function when running in AWS Lambda, you need to assign the function an IAM role that allows the function to write to CloudWatch logs. A typical IAM policy for such permission will be similar to:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```



## To Do

- Create a deployable template of this Lambda function along with other related services, such as a CloudWatch event that invokes the function once per day.
- Allow more customization from the event parameter in Lambda.
- Utilizing Amazon Connect and Amazon Lex for automated phone call to system administrator.