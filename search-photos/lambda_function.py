import json
import boto3
import os
import sys
import uuid
import time
import requests
from requests_aws4auth import AWS4Auth
from requests.auth import HTTPBasicAuth

region = 'us-east-1'
service = "es"
credentials = boto3.Session().get_credentials()
access_key = credentials.access_key
secret_key = credentials.secret_key
awsauth = AWS4Auth(access_key, secret_key, region, service, session_token = credentials.token)
# access_key = os.environ.get('AWS_ACCESS_KEY_ID')
# secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')

# awsauth = AWS4Auth(access_key, secret_key, region, service, session_token=None)
# awsauth = AWS4Auth(access_key, secret_key, REGION, service, session_token=credentials.token)

def lambda_handler(event, context):
	
	# recieve from API Gateway
	print("EVENT --- {}".format(json.dumps(event)))
	
	headers = { "Content-Type": "application/json" }
	lex = boto3.client('lex-runtime')

	query = event["queryStringParameters"]["q"]
	print("query --- {}".format(query))
	
	# input the lex info
	lex_response = lex.post_text(
		botName='PhotoAlbum',
		botAlias='Prod',
		userId='yj2679',
		inputText=query
	)
	
	print("LEX RESPONSE --- {}".format(json.dumps(lex_response)))

	
	if "slots" in lex_response:
		keys = [lex_response["slots"]["tag_a"], lex_response["slots"]["tag_b"], lex_response["slots"]["tag_c"]]
		print(keys)


		img_list = []
		for tag in keys:
			if tag:
				print(tag)
				tag_lower = tag.lower()
				searchData = get_photos_from_es(tag_lower)
				print("es RESPONSE --- {}".format(searchData))
				
				for photo in searchData:
					img_url = 'https://6998-assignment2-b2.s3.amazonaws.com/' + photo
					print(img_url)
					img_list.append(img_url)
	
		if img_list:
			img_list = list(set(img_list))
			print(img_list)
	        
			return {
				'statusCode': 200,
				'headers': {
					'Access-Control-Allow-Headers' : 'Content-Type',
		            'Access-Control-Allow-Origin': '*',
		            'Access-Control-Allow-Methods': 'OPTIONS,GET',
		            'Content-Type': 'application/json'
				},
				'body': json.dumps(img_list)
			}
	else:
		
		return {
				'statusCode': 200,
				'headers': {
					'Access-Control-Allow-Headers' : 'Content-Type',
		            'Access-Control-Allow-Origin': '*',
		            'Access-Control-Allow-Methods': 'OPTIONS,GET',
		            'Content-Type': 'application/json'
				},
				'body': json.dumps("No such photos.")
			}

def send_signed(method, url, service='es', region='us-east-1', body=None):
#     credentials = boto3.Session().get_credentials()
#     auth = HTTPBasicAuth('root', 'TCX6998aws')
    
    

    # es_query = "https://search-restaurants-qxvt5taa6e5u5i6i64le5tyq24.us-east-1.es.amazonaws.com/_search?q={}".format(cuisine)
    URL= "https://search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com/photos/{}"
    es_query = URL.format('_search')
    region = "us-east-1"
    service = "es"
    # access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    # secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    credentials = boto3.Session().get_credentials()
    access_key = credentials.access_key
    secret_key = credentials.secret_key
    print("access_key", access_key)
    print("secret_key", secret_key)
    awsauth = AWS4Auth(access_key, secret_key, region, service, session_token = credentials.token)
	
    

    # awsauth = AWS4Auth(access_key, secret_key, region, service, session_token=None)
    # credentials = boto3.Session().get_credentials()
	
	
    
    esResponse = requests.get(url = es_query, auth=awsauth)

    fn = getattr(requests, method)
    if body and not body.endswith("\n"):
        body += "\n"
    try:
        response = fn(es_query, auth=awsauth, data=body, 
                        headers={"Content-Type":"application/json"})
        if response.status_code != 200:
        	print("failed response from es-----" )
        	print(response.content)
        	raise Exception("{} failed with status code {}".format(method.upper(), response.status_code))
        return response.content
    except Exception:
        raise
        

# def get_photos_from_es(category):
# 	res = []
# 	for q in category:
# 		es_query = "https://search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com/_search?q={}".format(q)
# 		esresponse = requests.get(url = es_query, auth = awsauth)
# 		content = json.loads(esresponse.content.decode("utf"))
# 		res.extend([rstr['_source']['objectKey'] for rstr in content['hits']['hits']])
		
# 	return res


def es_search(criteria):
    URL = 'https://search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com/photos/{}'
    url = URL.format('_search')
    return send_signed('get', url, body=json.dumps(criteria))   

def get_photos_from_es(category):
    """Given a category, return a list of photo ids in that category"""
    def es_search(criteria):
        URL = 'https://search-photo-nzn7hhs64lavsym7bxblpithhm.us-east-1.es.amazonaws.com/photos/{}'
        # url = URL.format('_search')
        return send_signed('get', URL.format('_search'), body=json.dumps(criteria))


    # criteria = {
    #     "query": { "match": {'labels': category} }
    # }
    criteria = {
        "query": { 
        	"match": {
        		"labels":{
        			"query": category,
        			"fuzziness": "AUTO",
        			"analyzer": "standard"
        		} 
        	} 
        }
    }
    content = es_search(criteria)
    content = json.loads(content)
    return [rstr['_source']['objectKey'] for rstr in content['hits']['hits']]


