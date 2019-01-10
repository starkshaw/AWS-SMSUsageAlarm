import json
import boto3
import sys
from datetime import datetime, timedelta
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

today = datetime.today()
SMS_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2']
warning_cutoff = 0.7 # Value between 0 to 1
warning_delivery = 'SMS' # 'SMS' or 'Topic'
warning_audience = '' # A list of phone numbers or a string of an SNS Topic ARN
sns_sender_id = 'AWSWarning'
account_id = boto3.client('sts').get_caller_identity().get('Account')

def lambda_handler(event, context):
    logger.info('Event: {}', event)
    body_message = ''
    usage_details = checkSMSMonthToDateSpentUSDOfThisMonthInEachRegion()
    logger.info('Usage details: {}'.format(json.dumps(usage_details)))
    publish_trace = publishWarningMessage(usage_details)
    body_message = json.dumps(publish_trace)
    response = {
        'usage_details': usage_details,
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': body_message
    }
    return json.dumps(response)

def publishWarningMessage(usage_details):
    usage_details.sort(key=lambda item:item['use_ratio'], reverse=False)
    warning_regions = []
    least_utilized_region = usage_details[0]['region_name']
    sns = boto3.client('sns', region_name=least_utilized_region)
    publish_trace = []
    for i in range(0, len(usage_details)):
        if usage_details[i]['is_warning'] == True:
            warning_regions.append(usage_details[i])
    logger.info('Warning regions with respective use ratio: {}.'.format(warning_regions))
    if len(warning_regions) > 0:
        region_str = ', '.join('{} ({:.2f}%)'.format(i['region_name'], i['use_ratio'] * 100.0) for i in warning_regions)
        msg = 'The monthly SMS usage in your AWS account {} is reaching {:.2f}% of the limit in the following region(s):\n{}\nPlease take appropriate actions.'.format(account_id, warning_cutoff * 100, region_str)
        if type(warning_audience) is list and warning_delivery == 'SMS':
            for i in warning_audience:
                try:
                    sns_response = sns.publish(
                        Message=msg,
                        PhoneNumber=i,
                        MessageAttributes={
                            'AWS.SNS.SMS.SenderID': {
                                'DataType': 'String',
                                'StringValue': sns_sender_id
                            },
                            'AWS.SNS.SMS.SMSType': {
                                'DataType': 'String',
                                'StringValue': 'Transactional'
                            }
                        }
                    )
                    logger.info('Message Published: {}.'.format(sns_response))
                    publish_trace.append(sns_response)
                except sns.exceptions.InvalidParameterException as e:
                    logger.error('Invalid Parameter Exception: {}.'.format(e))
                except Exception as e:
                    logger.error('Error: {}.'.format(e))
        elif type(warning_audience) is str and warning_delivery == 'Topic':
            try:
                regional_sns = boto3.client('sns', region_name=warning_audience.split(':')[3])
                publish_trace.append(
                    regional_sns.publish(
                        Message=msg,
                        TopicArn=warning_audience,
                        Subject='SMS Usage Alarm - {}'.format(today.strftime('%b. %d, %Y')),
                        MessageAttributes={
                            'AWS.SNS.SMS.SenderID': {
                                'DataType': 'String',
                                'StringValue': sns_sender_id
                            },
                            'AWS.SNS.SMS.SMSType': {
                                'DataType': 'String',
                                'StringValue': 'Transactional'
                            }
                        }
                    )
                )
            except IndexError as e:
                logger.error('Cannot extract region metadata from "{}".'.format(warning_audience))
                sys.exit(1)
            except regional_sns.exceptions.InvalidParameterException as e:
                logger.error('Invalid Parameter Exception: {}.'.format(e))
                sys.exit(1)
            except regional_sns.exceptions.NotFoundException as e:
                logger.error('Not Found Exception: {}.'.format(e))
                sys.exit(1)
            except regional_sns.exceptions.ClientError as e:
                logger.error('Client Error: {}.'.format(e))
                sys.exit(1)
            except Exception as e:
                logger.error('Error: {}.'.format(e))
        else:
            logger.error('Error: Warning delivery and warning audience type mismatch.')
    return publish_trace

def checkSMSMonthToDateSpentUSDOfThisMonthInEachRegion():
    list_of_usage = []
    for i in SMS_regions:
        list_of_usage.append(checkSMSMonthToDateSpentUSDOfThisMonth(region_name=i))
    return list_of_usage

def checkSMSMonthToDateSpentUSDOfThisMonth(region_name):
    start_time = datetime(today.year, today.month, 1)
    end_time = datetime(today.year, today.month, today.day)
    response = checkSMSMonthToDateSpentUSD(region_name=region_name, start_time=start_time, end_time=end_time)
    return response

def checkSMSMonthToDateSpentUSD(region_name, start_time, end_time):
    cloudwatch_resource = boto3.resource('cloudwatch', region_name=region_name)
    sns = boto3.client('sns', region_name=region_name)
    account_limit = 1
    try:
        account_limit = sns.get_sms_attributes()['attributes']['MonthlySpendLimit']
    except KeyError as e:
        logger.error('No such key exists: {}.'.format(e))
        logger.error('No spending limit value is set in {}, continue as default value 1.'.format(region_name))
    metric = cloudwatch_resource.Metric('AWS/SNS', 'SMSMonthToDateSpentUSD')
    warning = False
    response = {
        'region_name': region_name,
        'latest_usage_in_USD': 0,
        'account_limit': float(account_limit),
        'use_ratio': 0,
        'is_warning': warning,
        'warning_cutoff': warning_cutoff,
        'start_time': '{}'.format(str(start_time)),
        'end_time': '{}'.format(str(end_time))
    }
    data = metric.get_statistics(
        StartTime = start_time,
        EndTime = end_time,
        Period = 86400,
        Statistics = ['Maximum'],
        Unit = 'Count'
    )
    if not data['Datapoints']:
        logger.info('No datapoints from {} to {}.'.format(str(start_time), str(end_time)))
        return response
    else:
        data['Datapoints'].sort(key=lambda item:item['Timestamp'], reverse=False)
        logger.info('Sorted Metric of AWS/SNS SMSMonthToDateSpentUSD: {}'.format(data))
        latest_datapoint = data['Datapoints'][-1]
        use_ratio = float(latest_datapoint['Maximum']) / float(account_limit)
        use_ratio = round(use_ratio, 3)
        logger.info('Use ratio: {:.2f}%'.format(use_ratio * 100))
        if use_ratio >= warning_cutoff:
            logger.warning('The spending is over {:.2f}% of overall account limit in {}.'.format(warning_cutoff * 100.0, region_name))
            warning = True
        else:
            logger.info('The spending is below {:.2f}% of overall account limit in {}.'.format(warning_cutoff * 100.0, region_name))
            warning = False
        response = {
            'region_name': region_name,
            'latest_usage_in_USD': float(latest_datapoint['Maximum']),
            'account_limit': float(account_limit),
            'use_ratio': use_ratio,
            'is_warning': warning,
            'warning_cutoff': warning_cutoff,
            'start_time': '{}'.format(str(start_time)),
            'end_time': '{}'.format(str(end_time))
        }
        return response

# the following is useful to make this script executable in both AWS Lambda and any other local environments

if __name__ == '__main__':
    lambda_handler('Local Test', None)
