import json
import urllib.parse
import boto3
import re
import os
import datetime
import dateutil.tz
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

print('Loading function')

s3 = boto3.client('s3')
eastern = dateutil.tz.gettz('US/Eastern')
es_endpoint = "https://search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com"

def detect_labels(photo, bucket):

    rekognition_client = boto3.client('rekognition')
    response = rekognition_client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}}, MaxLabels=10)
    rekog_labels = []
    
    print('Detected labels for ' + photo) 
    print()   
    for label in response['Labels']:
        rekog_labels.append(label['Name'])
        print ("Label: " + label['Name'])
        print ("Confidence: " + str(label['Confidence']))

        print ("Parents:")
        for parent in label['Parents']:
            print ("   " + parent['Name'])
        print ("----------")
        print ()
    print('rekog_labels: ', rekog_labels)
    
    return rekog_labels
    
def generate_object(rekog_labels, user_labels, key, bucket):
    now = str(datetime.datetime.now(tz=eastern)).split('.')[0]
    record = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": now,
        "labels": list(set(rekog_labels + user_labels))
    }
    print(record)
    return record
    
def es_post(record):
    
    host = "search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com"
    region = 'us-east-1'
    service = 'es'
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region)
    search = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    res = search.index(index="photos", doc_type="_doc", body=record)
    # res = search.get(index="photos", doc_type="_doc", id='1')
    return res
    
    
    
def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        rekog_labels = detect_labels(key, bucket)
        if 'x-amz-meta-customlabels' in response['ResponseMetadata']['HTTPHeaders']:
            user_labels_str = response['ResponseMetadata']['HTTPHeaders']['x-amz-meta-customlabels']
            user_labels = re.findall('[a-zA-Z0-9]+', user_labels_str)
        else:
            user_labels = []
        
        print("User_labels ----- ", user_labels)
        print("rekog_labels ----- ", rekog_labels)
        # print(response)
        # print(response['ContentType'])
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
    
    ##### Get user entered labels
    record = generate_object(rekog_labels, user_labels, key, bucket)
    response = es_post(record)
    print("Response from es ----- ", response)
    
    
# def lambda_handler(event, context):
#     host = "search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com"
#     region = 'us-east-1'
#     service = 'es'
#     # access_key, secret_key = os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY")
#     credentials = boto3.Session().get_credentials()
#     # # credentials = credentials.get_frozen_credentials()
#     access_key, secret_key = credentials.access_key, credentials.secret_key
#     # print("access_key", access_key)
#     # print("secret_key", secret_key)
#     awsauth = AWS4Auth(access_key, secret_key, region, service, session_token = credentials.token)
    
#     # credentials = boto3.Session().get_credentials()
#     # auth = AWSV4SignerAuth(credentials, region)
#     # print(credentials.access_key, credentials.secret_key)
    
#     # awsauth = AWS4Auth(access_key, secret_key, region, service, session_token=None)
#     search = OpenSearch(
#         hosts = [{'host': host, 'port': 443}],
#         http_auth = awsauth,
#         use_ssl = True,
#         verify_certs = True,
#         connection_class = RequestsHttpConnection
#     )
#     index_body = {
#         'settings':{
#             "analysis":{
#                 "analyzer":{
#                     "my_analyzer":{
#                         "tokenizer": "standard",
#                         "filter":["standard", "lowercase", "stop", "porter_stem"]
#                         # "type": "snowball"
#                     }
#                 }
#             }
#         }
#     }
#     res = search.indices.create("photos", body=index_body)
#     # res = search.indices.delete(index = "photos")
#     print("create index:", res)