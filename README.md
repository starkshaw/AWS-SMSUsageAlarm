# AWS-SMSUsageAlarm
This is an alarm to notify you when you are approaching the spent limit of SMS in AWS.

## Introduction

A Lambda function that checks the current SMS usage in [all regions](https://docs.aws.amazon.com/sns/latest/dg/sms_supported-countries.html) that supports SMS. If the usage crossed certain percentage of overall account limit set up in that region (by default it is 1.00 USD), the function will send an SMS to a group of recipients, or to a SNS topic.



## Environments

- Lambda function (`lambda_function.py`), can be triggered by anything. Ideally a CloudWatch event scheduled by some point at a day. **Recommended to deploy this by CloudFormation.**
- Local environment (`sms_usage_alarm.py`). Tested in Python 3.7.



## CloudFormation Deployment

It is recommended to deploy the Lambda version of this alarm via CloudFormation. A CloudFormation stack is provided as `template.json`.

### Prerequisites

If you wish to send the alarm to an SNS topic, you should create an SNS topic in the region of `us-east-1`.

The CloudFormation stack should be launched in the region of `us-east-1`.

When creating a stack, it is required to upload the deployment package of the Lambda function to an S3 bucket that is located in `us-east-1`.

### Settings

There are several settings to be completed before the creation of all resources:

- `S3Bucket`: The name of the S3 bucket where the deployment package is placed.
- `S3Key`: The key of the S3 bucket where the deployment package is placed.
- `WarningCutoff`, `WarningDelivery`, and `WarningAudience` are defined below in [Configurations](#configurations). However, if `WarningAudience` here is a list of phone numbers, it should be separated by a single comma “,”.

Once the deployment is completed, the Lambda function will be invoked at 0:00 UTC each day.



## Configurations

- `warning_cutoff`: A value from 0 to 1. If the percentage of usage crossed the value, the recipients will be notified. For example, if the value is set to `0.7` that means if one region used 70% of its spending limit, you will see this region is included in a warning message.
- `warning_delivery`: A value either be `'SMS'` or `'Topic'`.
- `warning_audience`: If `warning_delivery` is `'SMS'`, `warning_audience` will be a `list` of phone numbers following the E.164 recommendation. If `warning_delivery` is `'Topic'`, `warning_audience` will be a `str` of the ARN of the SNS topic of the recipients.

### Lambda Function

The parameters above should be configured when deploying the CloudFormation stack or from environment variables in the Lambda function. The source code is supposed to be kept unmodified if it is in Lambda environment.

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

- Allow more customization from the event parameter in Lambda.
- Utilizing Amazon Connect and Amazon Lex for automated phone call to system administrator.
